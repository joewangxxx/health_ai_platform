from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional
import json
import inspect
import logging
import uvicorn
import uuid
import sys
import os
import traceback

# 主入口：集中挂载 FastAPI 生命周期、认证、分析与各业务子路由。
# 设计目标：在部分可选模型不可用时，服务仍可降级运行并返回可消费结果。
if hasattr(sys.stdout, "reconfigure"):
    # 统一 stdout 编码，避免 Windows 终端输出中文时出现乱码。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    # 统一 stderr 编码，确保异常栈信息可读。
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.core.config import DEFAULT_BACKEND_CORS_ORIGINS, settings
from backend.config import DEFAULT_DEVICE_STATE

logger = logging.getLogger(__name__)


class _OptionalRuntimeComponentStub:
    # 可选组件导入失败时使用的兜底桩对象，保证后续调用不因 None 崩溃。
    def __init__(self, *args, **kwargs):
        self._loaded = False

    async def load_models(self):
        # 与真实引擎保持同名异步接口，方便生命周期阶段统一初始化。
        self._loaded = True


async def _maybe_await(value):
    # 兼容同步函数和异步函数的返回值，调用端无需区分。
    if inspect.isawaitable(value):
        return await value
    return value

# --- 导入认证与数据库模块 ---
from backend.database import init_db, get_session
from backend.models import User, UserCreate, Token, UserProfile, UserRead
from backend.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    authenticate_user,
    get_current_active_superuser
)
from sqlmodel import Session, select
from sqlalchemy import func

# 可选服务组件：导入失败时会回退到桩对象，不阻断应用启动。

# ================= 🚀 HealthAI Platform =================

# ================= 2. 服务初始化 =================
try:
    from backend.services.risk_engine import DiseaseRiskEngine
except Exception:
    DiseaseRiskEngine = _OptionalRuntimeComponentStub

try:
    from backend.services.gene_service import GeneRiskEngine
except Exception:
    GeneRiskEngine = _OptionalRuntimeComponentStub

try:
    from backend.services.fusion_service import FusionRiskEngine
except Exception:
    FusionRiskEngine = lambda *args, **kwargs: _OptionalRuntimeComponentStub()

try:
    from backend.services.admin_service import AdminDataService, task_logs, system_task_state  # 管理端服务
except Exception:
    AdminDataService = _OptionalRuntimeComponentStub
    task_logs = []
    system_task_state = {}

try:
    from backend.services.food_service import FoodPredictor
except Exception:
    FoodPredictor = _OptionalRuntimeComponentStub

try:
    from backend.services.inference_service import Predictor
except Exception:
    Predictor = _OptionalRuntimeComponentStub

try:
    from backend.services.pharm_service import PharmService
except Exception:
    PharmService = _OptionalRuntimeComponentStub

# ================= 全局引擎实例初始化 =================
risk_engine = None
gene_engine = None
pharm_engine = None
fusion_engine = None
food_predictor = None
food_vision_engine = None  # 别名，指向 food_predictor
general_predictor = None
admin_service = None


# ================= 3. 应用生命周期 =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段
    # 启动总流程：数据库初始化、兼容性补丁、缓存初始化、可选引擎加载。
    logger.info("Initializing database.")
    init_db()
    
    # 自动创建管理员账号
    from sqlmodel import Session, select
    from backend.database import engine
    from backend.models import User, UserProfile
    from backend.auth import get_password_hash
    
    with Session(engine) as session:
        # 默认管理员兜底：仅在库中不存在时创建，避免重复插入。
        statement = select(User).where(User.username == "admin")
        user = session.exec(statement).first()
        if not user:
            logger.info("Admin account not found; creating default admin account.")
            admin_user = User(
                username="admin", 
                email="admin@healthai.com", 
                hashed_password=get_password_hash("admin"),
                is_superuser=True
            )
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            # 创建用户资料
            profile = UserProfile(user_id=admin_user.id)
            session.add(profile)
            session.commit()
            logger.info("Admin account ensured: admin / admin")
        else:
            logger.info("Admin account already exists: admin")
    
    # 任务 79：自动补齐数据库 schema（extra_data 列热修复）
    import sqlite3
    db_path = settings.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
    logger.info("Checking database schema at: %s", db_path)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 尝试添加 extra_data 列；若已存在则静默跳过
        # 历史版本兼容：补齐 userprofile.extra_data 列（幂等执行）。
        cursor.execute("ALTER TABLE userprofile ADD COLUMN extra_data JSON;")
        conn.commit()
        logger.info("Database schema patched: extra_data column added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("Database schema OK: extra_data column already exists.")
        else:
            logger.warning("Database schema check warning: %s", e)
    except Exception as e:
        logger.warning("Database schema patch skipped: %s", e)
    
    # 任务 85：自动补齐 allow_research 列
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 历史版本兼容：补齐科研授权开关字段。
        cursor.execute("ALTER TABLE userprofile ADD COLUMN allow_research BOOLEAN DEFAULT 0;")
        conn.commit()
        logger.info("Database schema patched: allow_research column added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("Database schema OK: allow_research column already exists.")
    except Exception as e:
        logger.warning("allow_research patch skipped: %s", e)
    finally:
        try:
            conn.close()
        except:
            pass

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # OCR 处理状态用于前端区分 success/partial_success/stored_unprocessed。
        cursor.execute("ALTER TABLE medicaldocument ADD COLUMN ocr_processing_status JSON;")
        conn.commit()
        logger.info("Database schema patched: ocr_processing_status column added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("Database schema OK: ocr_processing_status column already exists.")
        else:
            logger.warning("OCR status schema check warning: %s", e)
    except Exception as e:
        logger.warning("ocr_processing_status patch skipped: %s", e)
    finally:
        try:
            conn.close()
        except:
            pass
    
    # 任务 108：初始化 Redis 缓存
    # 任务 108：初始化 Redis 缓存
    logger.info("Initializing Redis cache.")
    from backend.core.cache import CacheManager
    # 缓存层允许后续按组件策略降级；此处先尝试初始化。
    await CacheManager.init(settings.REDIS_URL)

    logger.info("Initializing optional runtime engines.")
    global risk_engine, gene_engine, pharm_engine, fusion_engine, food_predictor, food_vision_engine, general_predictor, admin_service
    try:
        # 实例化可选运行时引擎。
        # 可选引擎集中实例化，单点失败不应阻断 API 可用性。
        risk_engine = DiseaseRiskEngine()
        gene_engine = GeneRiskEngine()
        pharm_engine = PharmService()
        food_predictor = FoodPredictor()
        general_predictor = Predictor()

        # 在生命周期启动时加载可选模型，避免导入应用时负担过重。
        await risk_engine.load_models()
        await gene_engine.load_models()
        await pharm_engine.load_models()
        await food_predictor.load_models()
        await general_predictor.load_models()

        # 当前视觉分析复用 food_predictor，保留独立变量便于后续拆分。
        food_vision_engine = food_predictor
        admin_service = AdminDataService(risk_engine=risk_engine, gene_engine=gene_engine, pharm_engine=pharm_engine)
        logger.info("Optional runtime engines initialized successfully.")
    except Exception as e:
        logger.warning("Optional runtime engine initialization failed: %s", e)
        logger.exception("Optional runtime engine initialization traceback")

    try:
        # 融合引擎依赖风险与基因引擎；失败时由综合分析接口走降级路径。
        fusion_engine = FusionRiskEngine(risk_engine=risk_engine, gene_engine=gene_engine)
    except Exception as exc:
        logger.warning("Optional fusion engine initialization skipped: %s", exc)
        fusion_engine = None

    yield

    # 关闭阶段
    # 关闭阶段：回收外部连接资源，避免热重载造成连接泄漏。
    logger.info("Shutting down application.")
    # 任务 108：关闭 Redis 连接
    await CacheManager.close()

app = FastAPI(title="HealthAI Platform API", version="3.0", lifespan=lifespan)

cors_allow_origins = [
    origin
    for origin in (settings.BACKEND_CORS_ORIGINS or DEFAULT_BACKEND_CORS_ORIGINS)
    if origin != "*"
]
if not cors_allow_origins:
    cors_allow_origins = DEFAULT_BACKEND_CORS_ORIGINS.copy()

# CORS: authenticated browser routes use backend-owned allowlisted origins.

# CORS：当前策略允许全部来源，优先保证本地与跨域联调可用。

# CORS - 放开所有来源以避免网络错误
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件挂载（任务 56：医疗文档存储）
from fastapi.staticfiles import StaticFiles
import os as _os
_os.makedirs(settings.UPLOAD_DIR, exist_ok=True)  # 自动创建上传目录
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

@app.get("/admin/users", response_model=list[UserRead])
async def read_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # 管理员专用接口：普通用户直接拒绝访问。
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    users = session.exec(select(User)).all()
    return users


@app.get("/health")
def health_check():
    # 容器/网关健康探针入口。
    return {"status": "healthy"}

# ================= 5. 核心业务接口（服务） =================

@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate, session: Session = Depends(get_session)):
    # 1. 检查用户名
    # 注册流程：用户名唯一性校验 -> 邮箱唯一性校验 -> 密码长度校验。
    statement = select(User).where(User.username == user.username)
    if session.exec(statement).first():
        raise HTTPException(status_code=400, detail="用户名已存在 (Username already taken)")
    
    # 2. Check Email (if provided)
    if user.email:
        statement_email = select(User).where(User.email == user.email)
        if session.exec(statement_email).first():
             raise HTTPException(status_code=400, detail="邮箱已注册 (Email already registered)")

    # 3. Check Password Strength
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位 (Password too short)")
    
    hashed_pwd = get_password_hash(user.password)
    # 注册成功后立即创建空画像，避免后续 profile 读写出现空分支。
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_pwd)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    # 创建空用户画像
    profile = UserProfile(user_id=db_user.id)
    session.add(profile)
    session.commit()
    
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    # OAuth2 密码模式登录：认证通过后签发 Bearer Token。
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/user/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    # 返回当前登录态基础信息，不包含敏感字段。
    return {
        "username": current_user.username,
        "email": current_user.email,
        "profile": current_user.profile,
        "is_superuser": current_user.is_superuser  # RBAC 权限字段
    }

@app.get("/user/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get the current user profile."""
    # profile 使用历史兼容结构；这里统一做 JSON 字段反序列化后再返回。
    if not current_user.profile:
        return {"status": "empty", "profile": None, "message": "User profile not found"}
    
    profile_dict = current_user.profile.model_dump(exclude_unset=False, warnings=False)
    
    # 解析 JSON 字段
    import json
    if profile_dict.get("genomic_data"):
        try:
            profile_dict["genomic_data"] = json.loads(profile_dict["genomic_data"])
        except:
            pass
    if profile_dict.get("risk_history"):
        try:
            profile_dict["risk_history"] = json.loads(profile_dict["risk_history"])
        except:
            pass
    if isinstance(profile_dict.get("extra_data"), str):
        try:
            profile_dict["extra_data"] = json.loads(profile_dict["extra_data"])
        except:
            pass
            
    return {"status": "success", "profile": profile_dict}

@app.post("/user/profile")
async def update_user_profile(
    profile_data: dict, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    """Update user profile with clinical and genetic data."""
    import json
    # 增量更新用户画像，并在有有效指标时写入一条历史快照记录。
    
    db_profile = current_user.profile
    if not db_profile:
        # 首次写入场景：没有画像则先创建关联记录。
        db_profile = UserProfile(user_id=current_user.id)
        session.add(db_profile)
    
    # 特殊处理: user_snps -> genomic_data (JSON 序列化)
    # 前端 user_snps 字段映射到后端 genomic_data 持久化列。
    if "user_snps" in profile_data and profile_data["user_snps"]:
        db_profile.genomic_data = json.dumps(profile_data["user_snps"])
        del profile_data["user_snps"]
    
    # 特殊处理: risk_report -> risk_history (JSON 序列化)
    if "risk_report" in profile_data and profile_data["risk_report"]:
        from backend.services.payload_normalization import normalize_risk_snapshot_payload

        normalized_risk_report = normalize_risk_snapshot_payload(
            profile_data["risk_report"],
            source="analyze_comprehensive",
        )
        if normalized_risk_report:
            # 优先保存标准化后的 risk_snapshot.v1 结构。
            db_profile.risk_history = json.dumps(normalized_risk_report, ensure_ascii=False)
        else:
            # 标准化失败时回退到原始风险报告，确保数据不丢失。
            db_profile.risk_history = json.dumps(profile_data["risk_report"], ensure_ascii=False)
        del profile_data["risk_report"]
    
    # 任务 84：在 SQLite 更新前确保所有 JSON 字段已序列化
    # 这些字段必须是字符串而非字典，SQLite 才能正确存储
    json_fields = ["genomic_data", "risk_history"]
    for field in json_fields:
        if field in profile_data and isinstance(profile_data[field], dict):
            profile_data[field] = json.dumps(profile_data[field], ensure_ascii=False)
    
    # 🔥 紧急修复：排除受保护字段，避免 IntegrityError
    # 禁止更新 id 或 user_id（前端清空时可能传入 None）
    protected_fields = {"id", "user_id", "user"}
    for pf in protected_fields:
        # 剔除受保护字段，避免误写主键/外键触发完整性异常。
        profile_data.pop(pf, None)
    
    # 更新其他字段（允许 None 值以支持清空操作）
    for key, value in profile_data.items():
        if hasattr(db_profile, key):
            # 保持 JSON 列字段为原生对象，仅序列化“字符串承载”的 JSON 载荷。
            if key not in {"extra_data"} and isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            setattr(db_profile, key, value)
            
    session.add(db_profile)
    # 仅在存在有效指标时落历史记录，避免产生空壳时间点。
    
    # [任务 27] 创建历史记录
    # 返回历史记录摘要列表，供前端列表页快速展示。
    from backend.models import HealthRecord
    
    # 提取用于历史记录的指标
    # 仅保留数值型且相关的指标
    metric_keys = [
        "Weight", "BMI", "WaistCircum", "SBP", "DBP", 
        "Glucose_Fasting", "HbA1c", "Cholesterol_Total", 
        "Triglycerides", "Cholesterol_HDL", "Cholesterol_LDL",
        "WBC", "Platelet", "GGT", "ALP", "Creatinine", "eGFR"
    ]
    
    current_metrics = {}
    for k in metric_keys:
        val = getattr(db_profile, k, None)
        if val is not None:
            current_metrics[k] = val
            
    if current_metrics:
        # 任务 83：确保 risk_snapshot 始终为 JSON 字符串（而非 dict）
        risk_snapshot_str = db_profile.risk_history
        if risk_snapshot_str and not isinstance(risk_snapshot_str, str):
            risk_snapshot_str = json.dumps(risk_snapshot_str, ensure_ascii=False)
        
        new_record = HealthRecord(
            user_id=current_user.id,
            source="manual_update",
            metrics=json.dumps(current_metrics, ensure_ascii=False),
            risk_snapshot=risk_snapshot_str
        )
        session.add(new_record)
        logger.info("Created history record for user %s", current_user.id)

    # 所有更新在同一事务提交，确保画像与历史记录一致。
    session.commit()
    session.refresh(db_profile)
    
    # 任务 114：用户资料变更时失效其 AI 响应缓存
    from backend.core.cache import CacheManager
    # 画像更新后立即失效用户缓存，避免 AI 上下文读取陈旧数据。
    await _maybe_await(CacheManager.invalidate_user_cache(current_user.id))
    
    return {"status": "success", "message": "健康档案更新成功", "profile": db_profile}

@app.get("/history/list")
async def get_history_list(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取健康历史记录列表"""
    # 构建趋势序列：每条记录形成一个时间点，缺失值保持 None。
    from backend.models import HealthRecord
    from sqlmodel import col
    
    statement = select(HealthRecord).where(HealthRecord.user_id == current_user.id).order_by(col(HealthRecord.record_date).desc())
    records = session.exec(statement).all()
    
    # 构建返回结果，安全处理 metrics 字段
    result = []
    for r in records:
        # 计算指标摘要
        summary = "No data"
        if r.metrics:
            try:
                metrics_dict = json.loads(r.metrics)
                summary = f"Contains {len(metrics_dict)} metrics"
            except (json.JSONDecodeError, TypeError):
                summary = "指标数据解析失败"
        
        result.append({
            "id": r.id,
            "date": r.record_date.strftime("%Y-%m-%d %H:%M"),
            "source": r.source,
            "summary": summary
        })
    
    return result

@app.get("/history/trends")
async def get_history_trends(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取关键指标趋势数据（用于绘图）"""
    from backend.models import HealthRecord
    from sqlmodel import col
    
    statement = select(HealthRecord).where(HealthRecord.user_id == current_user.id).order_by(HealthRecord.record_date)
    records = session.exec(statement).all()
    
    dates = []
    series = {
        "BMI": [],
        "Glucose_Fasting": [],
        "SBP": [],
        "HbA1c": [],
        "Cholesterol_Total": []
    }
    
    for r in records:
        try:
            metrics = json.loads(r.metrics)
            # 仅在至少有一个关键指标时才追加？
            # 或者只追加日期并填空值？这里选择仅追加现有可用指标。
            dates.append(r.record_date.strftime("%Y-%m-%d"))
            
            for key in series.keys():
                series[key].append(metrics.get(key, None))
                
        except:
            continue
            
    return {
        "dates": dates,
        "metrics": series
    }

# ================= 5. 管理员数据中心（新增） =================

@app.post("/admin/data/upload")
async def admin_upload_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    pipeline_type: str = Form(...), # 临床/基因关联/药学/视觉流水线类型
    extra_meta: str = Form(None), # 额外元信息（例如 disease_name）
    admin: User = Depends(get_current_active_superuser)
):
    """Admin data upload endpoint."""


    # 每次上传生成短 task_id，作为后台流水线执行追踪标识。
    # 临床专用上传接口：同步归档文件，随后可独立触发训练流程。
    task_id = str(uuid.uuid4())[:8]
    
    # 保存临时文件
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{task_id}_{file.filename}")
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
        
    # 分发执行流水线
    # 根据 pipeline_type 分发到不同后台处理任务。
    if pipeline_type == "clinical":
        background_tasks.add_task(admin_service.process_clinical, file_path, task_id)
    elif pipeline_type == "gwas":
        if not extra_meta:
             return {"status": "error", "message": "Missing disease_name (extra_meta) for GWAS"}
        background_tasks.add_task(admin_service.process_gwas, file_path, extra_meta, task_id)
    elif pipeline_type == "pharm":
         background_tasks.add_task(admin_service.process_pharm, file_path, task_id)
    elif pipeline_type == "vision":
         background_tasks.add_task(admin_service.process_vision, file_path, task_id)
    else:
        return {"status": "error", "message": "Unknown pipeline type"}
        
    return {
        "status": "queued",
        "task_id": task_id,
        "message": f"Pipeline {pipeline_type} started in background"
    }

@app.get("/admin/data/logs")
async def get_admin_logs(admin: User = Depends(get_current_active_superuser)):
    """Get admin task logs."""
    return {"logs": task_logs}

# ================= 🏥 临床数据专用接口 =================

@app.post("/admin/data/clinical/upload")
async def admin_upload_clinical(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_active_superuser)
):
    """Upload clinical data archive for the admin background pipeline."""



    task_id = str(uuid.uuid4())[:8]
    
    # 保存临时文件
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{task_id}_{file.filename}")
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 调用归档方法 (同步执行，因为只是保存文件)
    admin_service.process_clinical(file_path, task_id)
    
    return {
        "status": "success",
        "task_id": task_id,
        "message": f"{file.filename} 上传成功，已完成 NHANES 数据处理"
    }

@app.post("/admin/data/clinical/train")
async def admin_trigger_clinical_train(
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_current_active_superuser)
):
    """
    触发临床数据训练流水线
    执行 ETL + 数据清洗 + 模型训练
    """
    task_id = str(uuid.uuid4())[:8]
    
    # 后台执行训练流水线
    # 训练链路可能耗时较长，采用后台任务避免阻塞请求线程。
    background_tasks.add_task(admin_service.trigger_clinical_pipeline, task_id)
    
    return {
        "status": "queued",
        "task_id": task_id,
        "message": "临床模型训练任务已加入后台队列。"
    }

@app.get("/admin/stats")
async def get_admin_stats(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_active_superuser)
):
    """Admin Dashboard Stats"""
    # 管理端概览数据：总用户数 + 当前任务运行状态。
    count = session.exec(select(func.count(User.id))).one()
    return {
        "total_users": count,
        "status": "Online",
        "active_tasks": system_task_state.get("active_count", 0)
    }

@app.get("/admin/task/status")
async def get_task_status(admin: User = Depends(get_current_active_superuser)):
    """Get global task execution status for real-time log display"""
    # 提供全局任务状态与日志，供前端实时刷新执行面板。
    return {
        "is_running": system_task_state.get("is_running", False),
        "active_count": system_task_state.get("active_count", 0),
        "logs": system_task_state.get("logs", []),
        "current_task": system_task_state.get("current_task", None)
    }

# ================= 4. API 路由注册 =================
from backend.api import nutrition

# 营养分析子路由：饮食相关评估能力入口。
app.include_router(nutrition.router, prefix="/nutrition", tags=["Nutrition"])

# 聊天路由（增强 RAG）
from backend.api.api_v1.endpoints import chat
# 对话子路由：RAG 与智能问答主入口。
app.include_router(chat.router, prefix="/chat", tags=["Chat"])

# 分析与模拟（任务 28）
from backend.api.api_v1.endpoints import analysis
# 规则分析子路由：独立的分析与模拟接口集合。
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])

@app.get("/")
def read_root():
    return {"message": "HealthAI Platform API is Running", "status": "active"}

class CheckupData(BaseModel):
    # 用户体检输入模型：允许额外字段，便于前后端渐进扩展。
    # --- 基础 ---
    Age: float
    Gender: int
    BMI: float
    Height: Optional[float] = None # V10 新增
    Weight: Optional[float] = None # V10 新增
    WaistCircum: Optional[float] = None

    # --- 血压 ---
    SBP: Optional[float] = None
    DBP: Optional[float] = None

    # --- 核心生化 ---
    Glucose_Fasting: Optional[float] = None
    HbA1c: Optional[float] = None
    Cholesterol_Total: Optional[float] = None
    Triglycerides: Optional[float] = None
    Cholesterol_HDL: Optional[float] = None
    
    # --- V10 新增：深度生化指标 ---
    WBC: Optional[float] = None        # 白细胞计数
    GGT: Optional[float] = None        # 转氨酶
    ALP: Optional[float] = None        # 碱性磷酸酶
    Platelet: Optional[float] = None   # 血小板
    Creatinine: Optional[float] = None # 肌酐

    # --- 其他 ---
    Sleep_Hours: Optional[float] = None
    user_snps: Optional[dict] = None
    Sleep_Hours: Optional[float] = None
    model_config = ConfigDict(extra="allow")

class LifestyleContextData(BaseModel):
    schema_version: str
    data_mode: str
    scenario_id: str
    summary: dict
    modifier_inputs: dict
    source_provenance: dict
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_contract(self):
        from backend.services.demo_behavior_scenarios import BehaviorScenarioRepository

        BehaviorScenarioRepository.validate_lifestyle_context(self.model_dump())
        return self


class ComprehensiveRequest(BaseModel):
    # 综合分析请求：clinical 与 user_snps 支持分别传入/缺省。
    clinical: Optional[CheckupData] = None
    user_snps: Optional[dict] = {}
    lifestyle_context: Optional[LifestyleContextData] = None


def _build_degraded_composite_risk_report(clinical_profile: dict) -> dict | None:
    """Fallback composite risk report when the fusion engine is unavailable."""
    # 第一层降级：若风险引擎可用，优先复用其结果并补齐统一字段。
    if not risk_engine or not hasattr(risk_engine, "assess_health"):
        base_report = None
    else:
        try:
            base_report = risk_engine.assess_health(clinical_profile)
        except Exception:
            logger.exception("Risk engine degraded fallback failed; attempting rule-based fallback.")
            base_report = None

    if isinstance(base_report, dict) and not base_report.get("error"):
        degraded_report = {}
        for disease, info in base_report.items():
            if not isinstance(info, dict):
                continue

            base_prob = info.get("final_risk", info.get("probability", info.get("risk", 0)))
            try:
                normalized_prob = round(float(base_prob), 1)
            except (TypeError, ValueError):
                normalized_prob = 0.0

            breakdown = info.get("breakdown") if isinstance(info.get("breakdown"), dict) else {}
            degraded_report[disease] = {
                **info,
                "final_risk": normalized_prob,
                "level": info.get("level", info.get("risk_level", "Low")),
                "breakdown": {
                    "base_clinical": breakdown.get("base_clinical", f"{normalized_prob}%"),
                    "gene_modifier": breakdown.get("gene_modifier", "x1.0"),
                    "lifestyle_modifier": breakdown.get("lifestyle_modifier", "x1.0"),
                },
            }

        if degraded_report:
            return degraded_report

    # 第二层降级：若上游引擎不可用，进入规则估算路径。
    def _safe_number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _risk_level(probability: float) -> str:
        if probability >= 75:
            return "Very High"
        if probability >= 50:
            return "High"
        if probability >= 25:
            return "Medium"
        return "Low"

    def _normalized_report(probability: float, drivers: list[str]) -> dict:
        clipped = max(5.0, min(round(probability, 1), 95.0))
        return {
            "final_risk": clipped,
            "level": _risk_level(clipped),
            "breakdown": {
                "base_clinical": f"{clipped}%",
                "gene_modifier": "x1.0",
                "lifestyle_modifier": "x1.0",
            },
            "drivers": drivers,
        }

    # 无年龄时使用保守默认值，保证规则路径可计算。
    age = _safe_number(clinical_profile.get("Age")) or 45.0
    bmi = _safe_number(clinical_profile.get("BMI"))
    sbp = _safe_number(clinical_profile.get("SBP"))
    dbp = _safe_number(clinical_profile.get("DBP"))
    glucose = _safe_number(clinical_profile.get("Glucose_Fasting"))
    hba1c = _safe_number(clinical_profile.get("HbA1c"))
    creatinine = _safe_number(clinical_profile.get("Creatinine"))
    egfr = _safe_number(clinical_profile.get("eGFR"))
    triglycerides = _safe_number(clinical_profile.get("Triglycerides"))
    hdl = _safe_number(clinical_profile.get("Cholesterol_HDL"))

    # 下面三组规则分别给出高血压、糖尿病、慢性肾病的解释性风险估计。
    hypertension_drivers = []
    hypertension_risk = 8.0 + min(age / 6.0, 14.0)
    if bmi is not None and bmi >= 24:
        hypertension_risk += 10.0
        hypertension_drivers.append("BMI")
    if sbp is not None:
        hypertension_risk += max(0.0, min((sbp - 120) * 0.9, 24.0))
        if sbp >= 130:
            hypertension_drivers.append("SBP")
    if dbp is not None:
        hypertension_risk += max(0.0, min((dbp - 80) * 0.7, 16.0))
        if dbp >= 85:
            hypertension_drivers.append("DBP")

    diabetes_drivers = []
    diabetes_risk = 6.0 + min(age / 8.0, 12.0)
    if bmi is not None and bmi >= 24:
        diabetes_risk += 10.0
        diabetes_drivers.append("BMI")
    if glucose is not None:
        diabetes_risk += max(0.0, min((glucose - 5.2) * 18.0, 34.0))
        if glucose >= 5.6:
            diabetes_drivers.append("Glucose_Fasting")
    if hba1c is not None:
        diabetes_risk += max(0.0, min((hba1c - 5.4) * 20.0, 30.0))
        if hba1c >= 5.7:
            diabetes_drivers.append("HbA1c")
    if triglycerides is not None and triglycerides >= 1.7:
        diabetes_risk += 8.0
        diabetes_drivers.append("Triglycerides")
    if hdl is not None and hdl < 1.0:
        diabetes_risk += 6.0
        diabetes_drivers.append("Cholesterol_HDL")

    ckd_drivers = []
    ckd_risk = 5.0 + min(age / 10.0, 10.0)
    if creatinine is not None:
        ckd_risk += max(0.0, min((creatinine - 80.0) * 0.35, 20.0))
        if creatinine >= 90:
            ckd_drivers.append("Creatinine")
    if egfr is not None:
        ckd_risk += max(0.0, min((90.0 - egfr) * 0.9, 28.0))
        if egfr < 90:
            ckd_drivers.append("eGFR")
    if sbp is not None and sbp >= 130:
        ckd_risk += 6.0
        ckd_drivers.append("SBP")
    if glucose is not None and glucose >= 5.6:
        ckd_risk += 4.0
        ckd_drivers.append("Glucose_Fasting")

    return {
        "Hypertension": _normalized_report(hypertension_risk, sorted(set(hypertension_drivers))),
        "Diabetes": _normalized_report(diabetes_risk, sorted(set(diabetes_drivers))),
        "CKD": _normalized_report(ckd_risk, sorted(set(ckd_drivers))),
    }


def _iot_data_from_lifestyle_context(lifestyle_context: LifestyleContextData | None) -> dict:
    iot_data = dict(DEFAULT_DEVICE_STATE)
    if not lifestyle_context:
        return iot_data

    context = lifestyle_context.model_dump()
    summary = context.get("summary") if isinstance(context.get("summary"), dict) else {}
    for source_key, target_key in (
        ("steps", "steps"),
        ("sleep_hours", "sleep_hours"),
        ("active_minutes", "active_minutes"),
        ("sedentary_minutes", "sedentary_minutes"),
        ("estimated_calories", "estimated_calories"),
        ("estimated_sodium_mg", "estimated_sodium_mg"),
    ):
        value = summary.get(source_key)
        if value is not None:
            iot_data[target_key] = value

    iot_data["lifestyle_context"] = context
    iot_data["lifestyle_source"] = context.get("data_mode") or "uploaded"
    return iot_data


def _calculate_composite_risk_report(clinical_profile: dict, user_snps: dict, iot_data: dict) -> tuple[dict | None, str]:
    # 优先尝试融合引擎；失败时自动回退到可解释降级规则。
    if fusion_engine is not None:
        try:
            fusion_report = fusion_engine.calculate_composite_risk(
                clinical_profile=clinical_profile,
                user_snps=user_snps,
                iot_data=iot_data,
            )
            if isinstance(fusion_report, dict) and fusion_report.get("error"):
                logger.warning("Fusion engine returned error report; attempting degraded fallback.")
            else:
                return fusion_report, "fusion"
        except Exception:
            logger.exception("Fusion engine comprehensive analysis failed; attempting degraded fallback.")

    degraded_report = _build_degraded_composite_risk_report(clinical_profile)
    if degraded_report is not None:
        logger.warning("Fusion engine unavailable; using degraded comprehensive analysis fallback.")
        return degraded_report, "degraded_fallback"
    return None, "unavailable"


def _build_analysis_context(
    clinical_profile: dict,
    request_clinical: dict | None,
    user_snps: dict | None,
    analysis_source: str,
) -> dict:
    # recognized 表示最终参与评估的字段，entered 表示本次请求显式提交的字段。
    # 两者拆开记录，便于前端解释“模型看到的数据”和“用户本次输入”。
    # 生成 analysis_context.v1：用于前端展示“本次分析是 final 还是 provisional”。
    recognized_fields = sorted(
        key for key, value in clinical_profile.items()
        if value is not None
    )
    entered_fields = sorted(
        key for key, value in (request_clinical or {}).items()
        if value is not None
    )

    # 融合模式下如果缺少基因上下文，统一标记为 provisional，
    # 并把 BMI 作为阻断字段返回给上游引导补全。
    if analysis_source == "fusion" and not user_snps:
        return {
            "schema_version": "analysis_context.v1",
            "analysis_mode": "provisional",
            "provisional_reasons": [
                {
                    "code": "missing_required_context",
                    "fields": ["BMI"],
                }
            ],
            "blocking_fields": ["BMI"],
            "field_state_summary": {
                "recognized": recognized_fields,
                "derived": [],
                "missing": ["BMI"],
                "user_confirmed": [],
                "user_entered": entered_fields,
            },
        }

    # derived_fields 记录“可由现有输入推导”的字段，供解释层说明不确定性来源。
    derived_fields = []
    if clinical_profile.get("BMI") is None and clinical_profile.get("Height") is not None and clinical_profile.get("Weight") is not None:
        derived_fields.append("BMI")
    if (
        clinical_profile.get("eGFR") is None
        and clinical_profile.get("Creatinine") is not None
        and clinical_profile.get("Age") is not None
        and clinical_profile.get("Gender") is not None
    ):
        derived_fields.append("eGFR")

    # missing_fields 聚焦关键化验项，供引导补录组件消费。
    missing_fields = []
    for field_name in (
        "Glucose_Fasting",
        "HbA1c",
        "Cholesterol_Total",
        "Triglycerides",
        "Cholesterol_HDL",
        "Creatinine",
        "ALT",
        "ALP",
    ):
        if clinical_profile.get(field_name) is None:
            missing_fields.append(field_name)

    # provisional_reasons 作为统一降级说明，前端可直接消费并渲染解释文案。
    provisional_reasons = []
    if derived_fields:
        provisional_reasons.append({
            "code": "derived_field_present",
            "fields": sorted(derived_fields),
        })
    if missing_fields:
        provisional_reasons.append({
            "code": "missing_labs",
            "fields": sorted(missing_fields),
        })

    return {
        "schema_version": "analysis_context.v1",
        "analysis_mode": "provisional" if provisional_reasons else "final",
        "provisional_reasons": provisional_reasons,
        "blocking_fields": [],
        "field_state_summary": {
            "recognized": recognized_fields,
            "derived": sorted(derived_fields),
            "missing": sorted(missing_fields),
            "user_confirmed": [],
            "user_entered": entered_fields,
        },
    }
    
@app.post("/analyze/comprehensive")
async def analyze_comprehensive(
    request: ComprehensiveRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Run composite risk analysis with optional DB profile merge."""

    # 数据合并优先级：数据库画像 < 本次请求（后者覆盖前者）。



    final_clinical = {}
    
    # 从数据库加载
    if current_user and current_user.profile:
        db_profile = current_user.profile.model_dump(exclude_unset=True)
        final_clinical.update({k: v for k, v in db_profile.items() if v is not None})
        
    # 合并请求数据
    req_clinical = {}
    if request.clinical:
        req_clinical = request.clinical.model_dump(exclude_unset=True)
        final_clinical.update({k: v for k, v in req_clinical.items() if v is not None})
        
    # 回退路径
    if not final_clinical.get('Age'):
        # 年龄缺失时提供保守默认值，避免模型/规则路径直接失败。
        final_clinical['Age'] = 45 
        
    try:
        # analysis_source 用于下游构建 analysis_context 的模式判定。
        iot_data = _iot_data_from_lifestyle_context(request.lifestyle_context)
        result, analysis_source = _calculate_composite_risk_report(
            clinical_profile=final_clinical,
            user_snps=request.user_snps,
            iot_data=iot_data,
        )
        if result is None:
            return {
                "status": "error",
                "message": "Comprehensive analysis unavailable; risk engines are not initialized.",
            }
        return {
            "status": "success",
            "risk_report": result,
            "analysis_context": _build_analysis_context(
                clinical_profile=final_clinical,
                request_clinical=req_clinical,
                user_snps=request.user_snps,
                analysis_source=analysis_source,
            ),
        }
        
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

class MedicationRequest(BaseModel):
    target_drug: str
    clinical: CheckupData
    genetics: Optional[dict] = {}
    iot: Optional[dict] = None

@app.post("/analyze/medication")
async def analyze_medication(req: MedicationRequest):
    # 药物分析：融合临床、基因与 IoT 上下文生成剂量/相互作用建议。
    iot = req.iot if req.iot else DEFAULT_DEVICE_STATE
    clinical_dict = req.clinical.model_dump()
    
    res = pharm_engine.calculate_dosage_recommendation(
        drug_name=req.target_drug,
        user_snps=req.genetics,
        clinical_profile=clinical_dict,
        iot_data=iot
    )
    
    return {
        "status": "success", 
        "safety_score": 85, # 当前为占位分数，后续可由引擎真实计算
        "recommendation": res.get('base_suggestion', 'No interactions found'),
        "analysis": {
            "genomic": res.get('base_suggestion', 'No gene issues'),
            "clinical": "; ".join(res.get('clinical_warning', ['Normal'])),
            "iot": "; ".join(res.get('iot_alert', ['Normal'])),
        },
        "detail": res
    }

@app.get("/api/device/current")
def get_device_status():
    # 返回设备侧默认状态（可被上游模拟或真实采集数据覆盖）。
    return DEFAULT_DEVICE_STATE

@app.post("/analyze/food_image")
async def analyze_food(file: UploadFile = File(...)):
    # 食物图像分析：引擎不可用时返回固定降级结构，保持前端契约稳定。
    logger.debug("Received food image upload: %s", file.filename)
    
    try:
        if not food_vision_engine:
            logger.warning("Food vision engine unavailable; returning degraded response.")
            return {
                "status": "error",
                "nutrition": {"calories": 0, "carbs": 0, "protein": 0, "fat": 0},
                "message": "Food vision engine unavailable"
            }
        
        # 读取图片字节
        image_bytes = await file.read()
        logger.debug("Food image payload size: %s bytes", len(image_bytes))
        
        # 调用预测
        result = food_vision_engine.predict(image_bytes)
        logger.info("Food image analysis completed: status=%s", result.get("status"))
        
        # 构建返回给前端的 JSON
        return {
            "status": "success" if result.get('status') == 'success' else "error",
            "filename": file.filename,
            "nutrition": result,
            "detected_carbs": result.get('carbs', 0),
            "message": "识别成功" if result.get('status') == 'success' else "识别失败"
        }
    except Exception as e:
        logger.exception("Food image analysis failed")
        return {
            "status": "error",
            "nutrition": {"calories": 0, "carbs": 0, "protein": 0, "fat": 0},
            "message": f"食物图像分析失败: {str(e)}"
        }

@app.post("/analyze/genetics_file")
async def analyze_genetics_file(file: UploadFile = File(...)):
    # 基因文本解析：按 23andMe 结构读取并返回预览样本。
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
        parsed_data = gene_engine.parse_23andme_txt(text_content)
        return {
            "status": "success", 
            "parsed_count": len(parsed_data["snps_dict"]), 
            "snps_dict": parsed_data["snps_dict"],
            "preview_list": parsed_data["preview_list"][:20]  # 预览列表最多返回 20 条
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/drugs/list")
async def get_drug_list():
    # 返回药物引擎当前支持的药物清单。
    try:
        drugs = pharm_engine.get_supported_drugs()
        return {"status": "success", "drugs": drugs}
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch drugs: {str(e)}", "drugs": []}

# ================= 6. OCR 模块（任务 21） =================
from backend.api.api_v1.endpoints import ocr
# OCR 子路由：文档上传、OCR 处理、状态回传。
app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR"])

# ================= 7. RAG 知识库模块（任务 22） =================
from backend.api.api_v1.endpoints import knowledge
# 知识库子路由：管理端 RAG 资料入库与检索管理。
app.include_router(knowledge.router, prefix="/admin/knowledge", tags=["Knowledge Base"])

# ================= 8. IoT 传感器模块（任务 30） =================
from backend.api.api_v1.endpoints import iot
# IoT 子路由：设备数据接入与状态查询。
app.include_router(iot.router, prefix="/api/v1/iot", tags=["IoT"])

# ================= 📁 9. 用户文档模块（任务 57） =================
from backend.api.api_v1.endpoints import user as user_api
# 用户文档子路由：文档列表、下载与关联元数据能力。
app.include_router(user_api.router, prefix="/api/v1/user", tags=["User Documents"])

from backend.api.api_v1.endpoints import profile as profile_api
app.include_router(profile_api.router, prefix="/api/v1/profile", tags=["Profile"])

from backend.api.api_v1.endpoints import demo as demo_api
app.include_router(demo_api.router, prefix="/api/v1/demo", tags=["Demo"])

# ================= 🔬 10. 科研数据模块（任务 85） =================
from backend.api.api_v1.endpoints import admin as admin_api
# 科研管理子路由：管理员科研数据与任务管理入口。
app.include_router(admin_api.router, prefix="/api/v1/admin", tags=["Admin Research"])

from backend.api.api_v1.endpoints import lifestyle as lifestyle_api
app.include_router(lifestyle_api.router, prefix="/api/v1/lifestyle", tags=["Lifestyle"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
