from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
import uvicorn
import uuid
import sys
import os
import traceback

from backend.core.config import settings
from backend.config import DEFAULT_DEVICE_STATE

# --- Import Auth & DB Modules ---
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

# ================= 🚀 HealthAI Platform =================

# ================= 📦 2. 模块智能导入 =================
print("\n========== 🚀 HealthAI Platform 启动中 ==========")

try:
    # V3.0 核心服务
    from backend.services.risk_engine import DiseaseRiskEngine
    from backend.services.gene_service import GeneRiskEngine
    from backend.services.fusion_service import FusionRiskEngine
    from backend.services.admin_service import AdminDataService, task_logs, system_task_state # Admin Service
    
    # V2.0 服务
    from backend.services.food_service import FoodPredictor
    from backend.services.inference_service import Predictor
    from backend.services.pharm_service import PharmService
    
    print("✅ 所有服务模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print(f"当前 Python 路径: {sys.path}")

# ================= 📦 全局引擎实例初始化 =================
risk_engine = None
gene_engine = None
pharm_engine = None
fusion_engine = None
food_predictor = None
food_vision_engine = None  # 别名，指向 food_predictor
general_predictor = None
admin_service = None


# ================= ⚡ 3. 应用生命周期 =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🔄 初始化数据库...")
    init_db()
    
    # Auto-create Admin
    from sqlmodel import Session, select
    from backend.database import engine
    from backend.models import User, UserProfile
    from backend.auth import get_password_hash
    
    with Session(engine) as session:
        statement = select(User).where(User.username == "admin")
        user = session.exec(statement).first()
        if not user:
            print("⚠️ 未找到管理员账号，正在自动创建...")
            admin_user = User(
                username="admin", 
                email="admin@healthai.com", 
                hashed_password=get_password_hash("admin"),
                is_superuser=True
            )
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            # Create Profile
            profile = UserProfile(user_id=admin_user.id)
            session.add(profile)
            session.commit()
            print("✅ [System] 管理员账号已确保存在: admin / admin")
        else:
            print("✅ [System] 管理员账号已存在: admin")
    
    # Task 79: Auto-patch database schema (Hotfix for extra_data column)
    import sqlite3
    db_path = settings.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
    print(f"🔧 Checking database schema at: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Try to add extra_data column - will fail silently if already exists
        cursor.execute("ALTER TABLE userprofile ADD COLUMN extra_data JSON;")
        conn.commit()
        print("✅ Database schema patched: extra_data column added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ Database schema OK: extra_data column already exists.")
        else:
            print(f"⚠️ Database schema check warning: {e}")
    except Exception as e:
        print(f"⚠️ Database schema patch skipped: {e}")
    
    # Task 85: Auto-patch allow_research column
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE userprofile ADD COLUMN allow_research BOOLEAN DEFAULT 0;")
        conn.commit()
        print("✅ Database schema patched: allow_research column added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ Database schema OK: allow_research column already exists.")
    except Exception as e:
        print(f"⚠️ allow_research patch skipped: {e}")
    finally:
        try:
            conn.close()
        except:
            pass
    
    # Task 108: Initialize Redis Cache
    print("🔄 初始化 Redis 缓存...")
    from backend.core.cache import CacheManager
    await CacheManager.init(settings.REDIS_URL)
    
    print("🔄 初始化核心引擎...")
    global risk_engine, gene_engine, pharm_engine, fusion_engine, food_predictor, food_vision_engine, general_predictor, admin_service
    try:
        risk_engine = DiseaseRiskEngine()
        gene_engine = GeneRiskEngine()
        pharm_engine = PharmService()
        fusion_engine = FusionRiskEngine(risk_engine=risk_engine, gene_engine=gene_engine)
        
        # Initialize Admin Service with engine references for Hot Reload
        admin_service = AdminDataService(risk_engine=risk_engine, gene_engine=gene_engine, pharm_engine=pharm_engine)
        
        # V2.0 Legacy
        food_predictor = FoodPredictor()
        food_vision_engine = food_predictor  # 🔥 别名，确保路由函数能访问
        general_predictor = Predictor()
        print("✅ 引擎初始化完成")
    except Exception as e:
        print(f"❌ 引擎初始化失败: {e}")
        traceback.print_exc()
    
    yield
    
    # Shutdown
    print("🛑 服务关闭...")
    # Task 108: Close Redis connection
    await CacheManager.close()

app = FastAPI(title="HealthAI Platform API", version="3.0", lifespan=lifespan)

# CORS - 放开所有来源以避免Network Error
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files Mount (Task 56: Medical Document Storage)
from fastapi.staticfiles import StaticFiles
import os as _os
_os.makedirs(settings.UPLOAD_DIR, exist_ok=True)  # Auto-create upload dir
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

@app.get("/admin/users", response_model=list[UserRead])
async def read_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    users = session.exec(select(User)).all()
    return users

# ================= ⚡ 5. 核心业务接口 (Services) =================

@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate, session: Session = Depends(get_session)):
    # 1. Check Username
    statement = select(User).where(User.username == user.username)
    if session.exec(statement).first():
        raise HTTPException(status_code=400, detail="用户名已存在 (Username already taken)")
    
    # 2. Check Email (if provided)
    if user.email:
        statement_email = select(User).where(User.email == user.email)
        if session.exec(statement_email).first():
             raise HTTPException(status_code=400, detail="该邮箱已被注册 (Email already registered)")

    # 3. Check Password Strength
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少需要 6 位 (Password too short)")
    
    hashed_pwd = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_pwd)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    # Create Empty Profile
    profile = UserProfile(user_id=db_user.id)
    session.add(profile)
    session.commit()
    
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
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
    return {
        "username": current_user.username,
        "email": current_user.email,
        "profile": current_user.profile,
        "is_superuser": current_user.is_superuser  # RBAC field
    }

@app.get("/user/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """获取当前用户的完整档案"""
    if not current_user.profile:
        return {"status": "empty", "profile": None, "message": "用户档案不存在"}
    
    profile_dict = current_user.profile.model_dump(exclude_unset=False)
    
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
            
    return {"status": "success", "profile": profile_dict}

@app.post("/user/profile")
async def update_user_profile(
    profile_data: dict, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    """更新用户档案 (临床 + 基因数据)"""
    import json
    
    db_profile = current_user.profile
    if not db_profile:
        db_profile = UserProfile(user_id=current_user.id)
        session.add(db_profile)
    
    # 特殊处理: user_snps -> genomic_data (JSON 序列化)
    if "user_snps" in profile_data and profile_data["user_snps"]:
        db_profile.genomic_data = json.dumps(profile_data["user_snps"])
        del profile_data["user_snps"]
    
    # 特殊处理: risk_report -> risk_history (JSON 序列化)
    if "risk_report" in profile_data and profile_data["risk_report"]:
        db_profile.risk_history = json.dumps(profile_data["risk_report"])
        del profile_data["risk_report"]
    
    # Task 84: Ensure all JSON fields are serialized before SQLite update
    # These fields MUST be strings, not dicts, for SQLite to store them
    json_fields = ["genomic_data", "risk_history", "extra_data"]
    for field in json_fields:
        if field in profile_data and isinstance(profile_data[field], dict):
            profile_data[field] = json.dumps(profile_data[field], ensure_ascii=False)
    
    # 🔥 URGENT FIX: Exclude protected fields to prevent IntegrityError
    # Never allow id or user_id to be updated (they can be None from frontend clearing)
    protected_fields = {"id", "user_id", "user"}
    for pf in protected_fields:
        profile_data.pop(pf, None)
    
    # 更新其他字段 (允许 None 值以支持清空操作)
    for key, value in profile_data.items():
        if hasattr(db_profile, key):
            # Extra safety: serialize any remaining dict values
            if isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            setattr(db_profile, key, value)
            
    session.add(db_profile)
    
    # [Task 27] Create History Record
    from backend.models import HealthRecord
    
    # Extract metrics for history
    # Filter only numeric/relevant metrics
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
        # Task 83: Ensure risk_snapshot is always a JSON string (not dict)
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
        print(f"✅ Created History Record for User {current_user.id}")

    session.commit()
    session.refresh(db_profile)
    
    # Task 114: Invalidate user's cached AI responses when profile data changes
    from backend.core.cache import CacheManager
    await CacheManager.invalidate_user_cache(current_user.id)
    
    return {"status": "success", "message": "档案已更新并保存历史记录", "profile": db_profile}

@app.get("/history/list")
async def get_history_list(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取健康历史记录列表"""
    from backend.models import HealthRecord
    from sqlmodel import col
    
    statement = select(HealthRecord).where(HealthRecord.user_id == current_user.id).order_by(col(HealthRecord.record_date).desc())
    records = session.exec(statement).all()
    
    return [
        {
            "id": r.id,
            "date": r.record_date.strftime("%Y-%m-%d %H:%M"),
            "source": r.source,
            "summary": f"包含 {len(json.loads(r.metrics))} 项指标"
        } 
        for r in records
    ]

@app.get("/history/trends")
async def get_history_trends(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取关键指标趋势数据 (用于绘图)"""
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
            # Only add if we have at least one metric of interest? 
            # Or just add date and fill none? Let's simply append what we have.
            dates.append(r.record_date.strftime("%Y-%m-%d"))
            
            for key in series.keys():
                series[key].append(metrics.get(key, None))
                
        except:
            continue
            
    return {
        "dates": dates,
        "metrics": series
    }

# ================= 🛡️ 5. Admin Data Center (New) =================

@app.post("/admin/data/upload")
async def admin_upload_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    pipeline_type: str = Form(...), # clinical, gwas, pharm, vision
    extra_meta: str = Form(None), # e.g. disease_name
    admin: User = Depends(get_current_active_superuser)
):
    """
    管理员数据上传接口 (Background Pipeline Trigger)
    """
    task_id = str(uuid.uuid4())[:8]
    
    # Save Temp File
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{task_id}_{file.filename}")
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
        
    # Dispatch Pipeline
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
    """获取所有后台任务日志"""
    return {"logs": task_logs}

# ================= 🏥 临床数据专用接口 =================

@app.post("/admin/data/clinical/upload")
async def admin_upload_clinical(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_active_superuser)
):
    """
    临床数据上传归档 (仅保存文件，不触发训练)
    支持批量上传多个 XPT/CSV 文件
    """
    task_id = str(uuid.uuid4())[:8]
    
    # Save Temp File
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
        "message": f"{file.filename} 已归档至 NHANES 目录"
    }

@app.post("/admin/data/clinical/train")
async def admin_trigger_clinical_train(
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_current_active_superuser)
):
    """
    手动触发临床模型重训练流水线
    运行 ETL + 训练 + 引擎重载
    """
    task_id = str(uuid.uuid4())[:8]
    
    # 后台执行训练流水线
    background_tasks.add_task(admin_service.trigger_clinical_pipeline, task_id)
    
    return {
        "status": "queued",
        "task_id": task_id,
        "message": "临床模型重构流水线已在后台启动..."
    }

@app.get("/admin/stats")
async def get_admin_stats(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_active_superuser)
):
    """Admin Dashboard Stats"""
    count = session.exec(select(func.count(User.id))).one()
    return {
        "total_users": count,
        "status": "Online",
        "active_tasks": system_task_state.get("active_count", 0)
    }

@app.get("/admin/task/status")
async def get_task_status(admin: User = Depends(get_current_active_superuser)):
    """Get global task execution status for real-time log display"""
    return {
        "is_running": system_task_state.get("is_running", False),
        "active_count": system_task_state.get("active_count", 0),
        "logs": system_task_state.get("logs", []),
        "current_task": system_task_state.get("current_task", None)
    }

# ================= 🛣️ 4. API 路由注册 =================
from backend.api import nutrition

app.include_router(nutrition.router, prefix="/nutrition", tags=["Nutrition"])

# Chat Router (RAG Enhanced)
from backend.api.api_v1.endpoints import chat
app.include_router(chat.router, prefix="/chat", tags=["Chat"])

# Analysis & Simulation (Task 28)
from backend.api.api_v1.endpoints import analysis
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])

@app.get("/")
def read_root():
    return {"message": "HealthAI Platform API is Running", "status": "active"}

class CheckupData(BaseModel):
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
    WBC: Optional[float] = None        # 白细胞
    GGT: Optional[float] = None        # 转肽酶
    ALP: Optional[float] = None        # 碱性磷酸酶
    Platelet: Optional[float] = None   # 血小板
    Creatinine: Optional[float] = None # 肌酐

    # --- 其他 ---
    Sleep_Hours: Optional[float] = None
    user_snps: Optional[dict] = None
    Sleep_Hours: Optional[float] = None
    
    class Config:
        extra = "allow"

class ComprehensiveRequest(BaseModel):
    clinical: Optional[CheckupData] = None
    user_snps: Optional[dict] = {}
    
@app.post("/analyze/comprehensive")
async def analyze_comprehensive(
    request: ComprehensiveRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    V3.0 贝叶斯融合分析接口
    - 优先使用 request 中的 clinical 数据
    - 如果 request 某字段缺失且用户已登录，尝试从 DB Profile 补全
    """
    final_clinical = {}
    
    # Load from DB
    if current_user and current_user.profile:
        db_profile = current_user.profile.model_dump(exclude_unset=True)
        final_clinical.update({k: v for k, v in db_profile.items() if v is not None})
        
    # Merge Request
    if request.clinical:
        req_clinical = request.clinical.model_dump(exclude_unset=True)
        final_clinical.update({k: v for k, v in req_clinical.items() if v is not None})
        
    # Fallback
    if not final_clinical.get('Age'):
        final_clinical['Age'] = 45 
        
    try:
        result = fusion_engine.calculate_composite_risk(
            clinical_profile=final_clinical,
            user_snps=request.user_snps,
            iot_data=DEFAULT_DEVICE_STATE
        )
        return {"status": "success", "risk_report": result}
        
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
        "safety_score": 85, # Mock, ideally engine calculates this
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
    return DEFAULT_DEVICE_STATE

@app.post("/analyze/food_image")
async def analyze_food(file: UploadFile = File(...)):
    print(f">>> 收到图片上传请求: {file.filename}")  # Debug log
    
    try:
        if not food_vision_engine:
            print(">>> 警告：视觉引擎未加载")
            return {
                "status": "error",
                "nutrition": {"calories": 0, "carbs": 0, "protein": 0, "fat": 0},
                "message": "视觉引擎未加载"
            }
        
        # 读取图片字节
        image_bytes = await file.read()
        print(f">>> 图片大小: {len(image_bytes)} bytes")
        
        # 调用预测
        result = food_vision_engine.predict(image_bytes)
        print(f">>> 预测结果: {result}")
        
        # 构建返回给前端的 JSON
        return {
            "status": "success" if result.get('status') == 'success' else "error",
            "filename": file.filename,
            "nutrition": result,
            "detected_carbs": result.get('carbs', 0),
            "message": "识别成功" if result.get('status') == 'success' else "识别失败"
        }
    except Exception as e:
        print(f">>> 图片处理异常: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "nutrition": {"calories": 0, "carbs": 0, "protein": 0, "fat": 0},
            "message": f"服务端处理异常: {str(e)}"
        }

@app.post("/analyze/genetics_file")
async def analyze_genetics_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
        parsed_data = gene_engine.parse_23andme_txt(text_content)
        return {
            "status": "success", 
            "parsed_count": len(parsed_data["snps_dict"]), 
            "snps_dict": parsed_data["snps_dict"],
            "preview_list": parsed_data["preview_list"][:20]  # Limit preview to 20 items
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/drugs/list")
async def get_drug_list():
    try:
        drugs = pharm_engine.get_supported_drugs()
        return {"status": "success", "drugs": drugs}
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch drugs: {str(e)}", "drugs": []}

# ================= 🛣️ 6. OCR 模块 (Task 21) =================
from backend.api.api_v1.endpoints import ocr
app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR"])

# ================= 📚 7. RAG 知识库模块 (Task 22) =================
from backend.api.api_v1.endpoints import knowledge
app.include_router(knowledge.router, prefix="/admin/knowledge", tags=["Knowledge Base"])

# ================= ⌚ 8. IoT 传感器模块 (Task 30) =================
from backend.api.api_v1.endpoints import iot
app.include_router(iot.router, prefix="/api/v1/iot", tags=["IoT"])

# ================= 📁 9. 用户文档模块 (Task 57) =================
from backend.api.api_v1.endpoints import user as user_api
app.include_router(user_api.router, prefix="/api/v1/user", tags=["User Documents"])

# ================= 🔬 10. 科研数据模块 (Task 85) =================
from backend.api.api_v1.endpoints import admin as admin_api
app.include_router(admin_api.router, prefix="/api/v1/admin", tags=["Admin Research"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)