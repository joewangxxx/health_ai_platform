from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from backend.services.ocr_service import medical_ocr_service
from backend.core.config import settings
from backend.database import get_session
from backend.auth import get_current_user
from backend.models import User, MedicalDocument
from sqlmodel import Session
import logging
import uuid
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

router = APIRouter()
logger = logging.getLogger(__name__)

# China Timezone
CHINA_TZ = ZoneInfo("Asia/Shanghai")

@router.post("/upload")
async def extract_medical_data(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    智能体检单识别接口 (Task 56: 增加持久化存储)
    
    Flow:
    1. Upload Image (jpg/png/pdf)
    2. Save file to uploads/medical_reports/
    3. Create MedicalDocument DB record
    4. OCR extracts raw text
    5. LLM parses text into structured JSON
    6. Update ocr_summary in DB
    7. Return data + file_url + document_id
    """
    # 1. Validate File Type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, PDF supported.")
    
    try:
        # 2. Read File
        file_bytes = await file.read()
        
        # 3. Generate Unique Filename and Save (Use China TZ)
        now_china = datetime.now(CHINA_TZ)
        unique_id = uuid.uuid4().hex[:8]
        timestamp = now_china.strftime("%Y%m%d_%H%M%S")
        
        # Get file extension
        ext = os.path.splitext(file.filename)[1] or ".bin"
        safe_filename = f"{timestamp}_{unique_id}{ext}"
        
        # Ensure directory exists
        save_dir = os.path.join(settings.UPLOAD_DIR, "medical_reports")
        os.makedirs(save_dir, exist_ok=True)
        
        file_path = os.path.join(save_dir, safe_filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        
        # 4. Generate Access URL
        file_url = f"/static/medical_reports/{safe_filename}"
        
        # 5. Create DB Record (Initial) with China TZ
        doc = MedicalDocument(
            user_id=current_user.id,
            file_name=file.filename,
            file_path=file_path,
            file_url=file_url,
            upload_date=now_china,
            ocr_summary=None
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        
        logger.info(f"Saved Document ID={doc.id} to {file_path}")
        
        # 6. Call OCR Service
        result = await medical_ocr_service.parse_medical_report(file_bytes)
        
        # 7. Update DB with OCR Summary
        if result.get("status") == "success" and result.get("data"):
            doc.ocr_summary = json.dumps(result["data"], ensure_ascii=False)
            session.add(doc)
            session.commit()
            
            # Task 114: Invalidate user's cached AI responses when new health data arrives
            from backend.core.cache import CacheManager
            await CacheManager.invalidate_user_cache(current_user.id)
            logger.info(f"🗑️ Cache invalidated after OCR upload for user {current_user.id}")
        
        # 8. Build Response
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            **result,
            "document_id": doc.id,
            "file_url": file_url
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"OCR Upload Endpoint Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

