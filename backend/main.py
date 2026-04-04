from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict
from typing import Optional
import json
import inspect
import logging
import uvicorn
import uuid
import sys
import os
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.core.config import settings
from backend.config import DEFAULT_DEVICE_STATE

logger = logging.getLogger(__name__)


class _OptionalRuntimeComponentStub:
    def __init__(self, *args, **kwargs):
        self._loaded = False

    async def load_models(self):
        self._loaded = True


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value

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

# ================= 馃殌 HealthAI Platform =================

# ================= ?? 2. ?????? =================
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
    from backend.services.admin_service import AdminDataService, task_logs, system_task_state  # Admin Service
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

# ================= 馃摝 鍏ㄥ眬寮曟搸瀹炰緥鍒濆鍖?=================
risk_engine = None
gene_engine = None
pharm_engine = None
fusion_engine = None
food_predictor = None
food_vision_engine = None  # 鍒悕锛屾寚鍚?food_predictor
general_predictor = None
admin_service = None


# ================= 鈿?3. 搴旂敤鐢熷懡鍛ㄦ湡 =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database.")
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
            # Create Profile
            profile = UserProfile(user_id=admin_user.id)
            session.add(profile)
            session.commit()
            logger.info("Admin account ensured: admin / admin")
        else:
            logger.info("Admin account already exists: admin")
    
    # Task 79: Auto-patch database schema (Hotfix for extra_data column)
    import sqlite3
    db_path = settings.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
    logger.info("Checking database schema at: %s", db_path)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Try to add extra_data column - will fail silently if already exists
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
    
    # Task 85: Auto-patch allow_research column
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
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
    
    # Task 108: Initialize Redis Cache
    # Task 108: Initialize Redis Cache
    logger.info("Initializing Redis cache.")
    from backend.core.cache import CacheManager
    await CacheManager.init(settings.REDIS_URL)

    logger.info("Initializing optional runtime engines.")
    global risk_engine, gene_engine, pharm_engine, fusion_engine, food_predictor, food_vision_engine, general_predictor, admin_service
    try:
        # Instantiate optional runtime engines.
        risk_engine = DiseaseRiskEngine()
        gene_engine = GeneRiskEngine()
        pharm_engine = PharmService()
        food_predictor = FoodPredictor()
        general_predictor = Predictor()

        # Load optional models during lifespan startup so app import stays light.
        await risk_engine.load_models()
        await gene_engine.load_models()
        await pharm_engine.load_models()
        await food_predictor.load_models()
        await general_predictor.load_models()

        food_vision_engine = food_predictor
        admin_service = AdminDataService(risk_engine=risk_engine, gene_engine=gene_engine, pharm_engine=pharm_engine)
        logger.info("Optional runtime engines initialized successfully.")
    except Exception as e:
        logger.warning("Optional runtime engine initialization failed: %s", e)
        logger.exception("Optional runtime engine initialization traceback")

    try:
        fusion_engine = FusionRiskEngine(risk_engine=risk_engine, gene_engine=gene_engine)
    except Exception as exc:
        logger.warning("Optional fusion engine initialization skipped: %s", exc)
        fusion_engine = None

    yield

    # Shutdown
    logger.info("Shutting down application.")
    # Task 108: Close Redis connection
    await CacheManager.close()

app = FastAPI(title="HealthAI Platform API", version="3.0", lifespan=lifespan)

# CORS - 鏀惧紑鎵€鏈夋潵婧愪互閬垮厤Network Error
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 鍏佽鎵€鏈夋潵婧?
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


@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ================= 鈿?5. 鏍稿績涓氬姟鎺ュ彛 (Services) =================

@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate, session: Session = Depends(get_session)):
    # 1. Check Username
    statement = select(User).where(User.username == user.username)
    if session.exec(statement).first():
        raise HTTPException(status_code=400, detail="鐢ㄦ埛鍚嶅凡瀛樺湪 (Username already taken)")
    
    # 2. Check Email (if provided)
    if user.email:
        statement_email = select(User).where(User.email == user.email)
        if session.exec(statement_email).first():
             raise HTTPException(status_code=400, detail="璇ラ偖绠卞凡琚敞鍐?(Email already registered)")

    # 3. Check Password Strength
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="瀵嗙爜闀垮害鑷冲皯闇€瑕?6 浣?(Password too short)")
    
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
    """Get the current user profile."""
    if not current_user.profile:
        return {"status": "empty", "profile": None, "message": "User profile not found"}
    
    profile_dict = current_user.profile.model_dump(exclude_unset=False, warnings=False)
    
    # 瑙ｆ瀽 JSON 瀛楁
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
    
    db_profile = current_user.profile
    if not db_profile:
        db_profile = UserProfile(user_id=current_user.id)
        session.add(db_profile)
    
    # 鐗规畩澶勭悊: user_snps -> genomic_data (JSON 搴忓垪鍖?
    if "user_snps" in profile_data and profile_data["user_snps"]:
        db_profile.genomic_data = json.dumps(profile_data["user_snps"])
        del profile_data["user_snps"]
    
    # 鐗规畩澶勭悊: risk_report -> risk_history (JSON 搴忓垪鍖?
    if "risk_report" in profile_data and profile_data["risk_report"]:
        from backend.services.payload_normalization import normalize_risk_snapshot_payload

        normalized_risk_report = normalize_risk_snapshot_payload(
            profile_data["risk_report"],
            source="analyze_comprehensive",
        )
        if normalized_risk_report:
            db_profile.risk_history = json.dumps(normalized_risk_report, ensure_ascii=False)
        else:
            db_profile.risk_history = json.dumps(profile_data["risk_report"], ensure_ascii=False)
        del profile_data["risk_report"]
    
    # Task 84: Ensure all JSON fields are serialized before SQLite update
    # These fields MUST be strings, not dicts, for SQLite to store them
    json_fields = ["genomic_data", "risk_history"]
    for field in json_fields:
        if field in profile_data and isinstance(profile_data[field], dict):
            profile_data[field] = json.dumps(profile_data[field], ensure_ascii=False)
    
    # 馃敟 URGENT FIX: Exclude protected fields to prevent IntegrityError
    # Never allow id or user_id to be updated (they can be None from frontend clearing)
    protected_fields = {"id", "user_id", "user"}
    for pf in protected_fields:
        profile_data.pop(pf, None)
    
    # 鏇存柊鍏朵粬瀛楁 (鍏佽 None 鍊间互鏀寔娓呯┖鎿嶄綔)
    for key, value in profile_data.items():
        if hasattr(db_profile, key):
            # Keep JSON-column fields as native objects; serialize string-backed JSON payloads only.
            if key not in {"extra_data"} and isinstance(value, dict):
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
        logger.info("Created history record for user %s", current_user.id)

    session.commit()
    session.refresh(db_profile)
    
    # Task 114: Invalidate user's cached AI responses when profile data changes
    from backend.core.cache import CacheManager
    await _maybe_await(CacheManager.invalidate_user_cache(current_user.id))
    
    return {"status": "success", "message": "妗ｆ宸叉洿鏂板苟淇濆瓨鍘嗗彶璁板綍", "profile": db_profile}

@app.get("/history/list")
async def get_history_list(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """鑾峰彇鍋ュ悍鍘嗗彶璁板綍鍒楄〃"""
    from backend.models import HealthRecord
    from sqlmodel import col
    
    statement = select(HealthRecord).where(HealthRecord.user_id == current_user.id).order_by(col(HealthRecord.record_date).desc())
    records = session.exec(statement).all()
    
    # 鏋勫缓杩斿洖缁撴灉锛屽畨鍏ㄥ鐞?metrics 瀛楁
    result = []
    for r in records:
        # 璁＄畻鎸囨爣鎽樿
        summary = "No data"
        if r.metrics:
            try:
                metrics_dict = json.loads(r.metrics)
                summary = f"Contains {len(metrics_dict)} metrics"
            except (json.JSONDecodeError, TypeError):
                summary = "鏁版嵁瑙ｆ瀽閿欒"
        
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
    """鑾峰彇鍏抽敭鎸囨爣瓒嬪娍鏁版嵁 (鐢ㄤ簬缁樺浘)"""
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

# ================= 馃洝锔?5. Admin Data Center (New) =================

@app.post("/admin/data/upload")
async def admin_upload_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    pipeline_type: str = Form(...), # clinical, gwas, pharm, vision
    extra_meta: str = Form(None), # e.g. disease_name
    admin: User = Depends(get_current_active_superuser)
):
    """Admin data upload endpoint."""


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
    """Get admin task logs."""
    return {"logs": task_logs}

# ================= 馃彞 涓村簥鏁版嵁涓撶敤鎺ュ彛 =================

@app.post("/admin/data/clinical/upload")
async def admin_upload_clinical(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_active_superuser)
):
    """Upload clinical data archive for the admin background pipeline."""



    task_id = str(uuid.uuid4())[:8]
    
    # Save Temp File
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{task_id}_{file.filename}")
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 璋冪敤褰掓。鏂规硶 (鍚屾鎵ц锛屽洜涓哄彧鏄繚瀛樻枃浠?
    admin_service.process_clinical(file_path, task_id)
    
    return {
        "status": "success",
        "task_id": task_id,
        "message": f"{file.filename} 宸插綊妗ｈ嚦 NHANES 鐩綍"
    }

@app.post("/admin/data/clinical/train")
async def admin_trigger_clinical_train(
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_current_active_superuser)
):
    """
    鎵嬪姩瑙﹀彂涓村簥妯″瀷閲嶈缁冩祦姘寸嚎
    杩愯 ETL + 璁粌 + 寮曟搸閲嶈浇
    """
    task_id = str(uuid.uuid4())[:8]
    
    # 鍚庡彴鎵ц璁粌娴佹按绾?
    background_tasks.add_task(admin_service.trigger_clinical_pipeline, task_id)
    
    return {
        "status": "queued",
        "task_id": task_id,
        "message": "涓村簥妯″瀷閲嶆瀯娴佹按绾垮凡鍦ㄥ悗鍙板惎鍔?.."
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

# ================= 馃洠锔?4. API 璺敱娉ㄥ唽 =================
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
    # --- 鍩虹 ---
    Age: float
    Gender: int
    BMI: float
    Height: Optional[float] = None # V10 鏂板
    Weight: Optional[float] = None # V10 鏂板
    WaistCircum: Optional[float] = None

    # --- 琛€鍘?---
    SBP: Optional[float] = None
    DBP: Optional[float] = None

    # --- 鏍稿績鐢熷寲 ---
    Glucose_Fasting: Optional[float] = None
    HbA1c: Optional[float] = None
    Cholesterol_Total: Optional[float] = None
    Triglycerides: Optional[float] = None
    Cholesterol_HDL: Optional[float] = None
    
    # --- V10 鏂板锛氭繁搴︾敓鍖栨寚鏍?---
    WBC: Optional[float] = None        # 鐧界粏鑳?
    GGT: Optional[float] = None        # 杞偨閰?
    ALP: Optional[float] = None        # 纰辨€х７閰搁叾
    Platelet: Optional[float] = None   # 琛€灏忔澘
    Creatinine: Optional[float] = None # 鑲岄厫

    # --- 鍏朵粬 ---
    Sleep_Hours: Optional[float] = None
    user_snps: Optional[dict] = None
    Sleep_Hours: Optional[float] = None
    model_config = ConfigDict(extra="allow")

class ComprehensiveRequest(BaseModel):
    clinical: Optional[CheckupData] = None
    user_snps: Optional[dict] = {}


def _build_degraded_composite_risk_report(clinical_profile: dict) -> dict | None:
    """Fallback composite risk report when the fusion engine is unavailable."""
    if not risk_engine or not hasattr(risk_engine, "assess_health"):
        return None

    base_report = risk_engine.assess_health(clinical_profile)
    if not isinstance(base_report, dict) or base_report.get("error"):
        return None

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

    return degraded_report or None


def _calculate_composite_risk_report(clinical_profile: dict, user_snps: dict, iot_data: dict) -> tuple[dict | None, str]:
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
    recognized_fields = sorted(
        key for key, value in clinical_profile.items()
        if value is not None
    )
    entered_fields = sorted(
        key for key, value in (request_clinical or {}).items()
        if value is not None
    )

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

    return {
        "schema_version": "analysis_context.v1",
        "analysis_mode": "final",
        "provisional_reasons": [],
        "blocking_fields": [],
        "field_state_summary": {
            "recognized": recognized_fields,
            "derived": [],
            "missing": [],
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




    final_clinical = {}
    
    # Load from DB
    if current_user and current_user.profile:
        db_profile = current_user.profile.model_dump(exclude_unset=True)
        final_clinical.update({k: v for k, v in db_profile.items() if v is not None})
        
    # Merge Request
    req_clinical = {}
    if request.clinical:
        req_clinical = request.clinical.model_dump(exclude_unset=True)
        final_clinical.update({k: v for k, v in req_clinical.items() if v is not None})
        
    # Fallback
    if not final_clinical.get('Age'):
        final_clinical['Age'] = 45 
        
    try:
        result, analysis_source = _calculate_composite_risk_report(
            clinical_profile=final_clinical,
            user_snps=request.user_snps,
            iot_data=DEFAULT_DEVICE_STATE,
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
    logger.debug("Received food image upload: %s", file.filename)
    
    try:
        if not food_vision_engine:
            logger.warning("Food vision engine unavailable; returning degraded response.")
            return {
                "status": "error",
                "nutrition": {"calories": 0, "carbs": 0, "protein": 0, "fat": 0},
                "message": "Food vision engine unavailable"
            }
        
        # 璇诲彇鍥剧墖瀛楄妭
        image_bytes = await file.read()
        logger.debug("Food image payload size: %s bytes", len(image_bytes))
        
        # 璋冪敤棰勬祴
        result = food_vision_engine.predict(image_bytes)
        logger.info("Food image analysis completed: status=%s", result.get("status"))
        
        # 鏋勫缓杩斿洖缁欏墠绔殑 JSON
        return {
            "status": "success" if result.get('status') == 'success' else "error",
            "filename": file.filename,
            "nutrition": result,
            "detected_carbs": result.get('carbs', 0),
            "message": "璇嗗埆鎴愬姛" if result.get('status') == 'success' else "璇嗗埆澶辫触"
        }
    except Exception as e:
        logger.exception("Food image analysis failed")
        return {
            "status": "error",
            "nutrition": {"calories": 0, "carbs": 0, "protein": 0, "fat": 0},
            "message": f"链嶅姟绔鐞嗗紓甯? {str(e)}"
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

# ================= 馃洠锔?6. OCR 妯″潡 (Task 21) =================
from backend.api.api_v1.endpoints import ocr
app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR"])

# ================= 馃摎 7. RAG 鐭ヨ瘑搴撴ā鍧?(Task 22) =================
from backend.api.api_v1.endpoints import knowledge
app.include_router(knowledge.router, prefix="/admin/knowledge", tags=["Knowledge Base"])

# ================= 鈱?8. IoT 浼犳劅鍣ㄦā鍧?(Task 30) =================
from backend.api.api_v1.endpoints import iot
app.include_router(iot.router, prefix="/api/v1/iot", tags=["IoT"])

# ================= 馃搧 9. 鐢ㄦ埛鏂囨。妯″潡 (Task 57) =================
from backend.api.api_v1.endpoints import user as user_api
app.include_router(user_api.router, prefix="/api/v1/user", tags=["User Documents"])

# ================= 馃敩 10. 绉戠爺鏁版嵁妯″潡 (Task 85) =================
from backend.api.api_v1.endpoints import admin as admin_api
app.include_router(admin_api.router, prefix="/api/v1/admin", tags=["Admin Research"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
