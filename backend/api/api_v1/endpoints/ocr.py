import asyncio
import inspect
import json
import logging
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from backend.auth import get_current_user
from backend.core.config import settings
from backend.database import get_session
from backend.models import MedicalDocument, User
from backend.services.ocr_service import medical_ocr_service
from backend.services.payload_normalization import (
    has_structured_ocr_summary_data,
    normalize_ocr_processing_status_payload,
    normalize_ocr_summary_payload,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
CHINA_TZ = ZoneInfo("Asia/Shanghai")


async def _parse_medical_report_with_timeout(file_bytes: bytes, timeout_seconds: float | None = None):
    timeout = timeout_seconds or settings.OCR_PROCESSING_TIMEOUT_SECONDS

    try:
        result = medical_ocr_service.parse_medical_report(file_bytes)
        if inspect.isawaitable(result):
            return await asyncio.wait_for(result, timeout=timeout)
        return result
    except (asyncio.TimeoutError, TimeoutError):
        logger.warning("OCR processing timed out after %s seconds; document remains saved.", timeout)
        return medical_ocr_service.build_stored_unprocessed_result(
            "ocr_processing_timeout",
            "Document saved, but OCR processing timed out.",
        )


@router.post("/upload")
async def extract_medical_data(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    OCR upload endpoint that persists a canonical summary envelope.
    """
    # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, PDF supported.")

    try:
        file_bytes = await file.read()

        now_china = datetime.now(CHINA_TZ)
        unique_id = uuid.uuid4().hex[:8]
        timestamp = now_china.strftime("%Y%m%d_%H%M%S")

        ext = os.path.splitext(file.filename)[1] or ".bin"
        safe_filename = f"{timestamp}_{unique_id}{ext}"

        save_dir = os.path.join(settings.UPLOAD_DIR, "medical_reports")
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, safe_filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        file_url = f"/static/medical_reports/{safe_filename}"

        doc = MedicalDocument(
            user_id=current_user.id,
            file_name=file.filename,
            file_path=file_path,
            file_url=file_url,
            upload_date=now_china,
            ocr_summary=None,
            ocr_processing_status=None,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        logger.info("Saved Document ID=%s to %s", doc.id, file_path)

        # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
        result = await _parse_medical_report_with_timeout(file_bytes)

        effective_status = result.get("status")
        if effective_status == "error":
            # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
            # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
            effective_status = "stored_unprocessed"

        raw_processing_status = result.get("ocr_processing_status")
        if isinstance(raw_processing_status, dict) and raw_processing_status.get("status") != effective_status:
            raw_processing_status = {
                **raw_processing_status,
                "status": effective_status,
            }

        normalized_status = normalize_ocr_processing_status_payload(
            raw_processing_status,
            default_status=effective_status,
            structured_data_present=has_structured_ocr_summary_data(result.get("data")),
            raw_text_present=bool(result.get("raw_text")),
            saved_at=doc.upload_date.isoformat() if doc.upload_date else None,
            processed_at=datetime.now(CHINA_TZ).isoformat(),
        )

        if normalized_status is not None:
            doc.ocr_processing_status = normalized_status

        normalized_summary = None
        if result.get("data") is not None and has_structured_ocr_summary_data(result["data"]):
            normalized_summary = normalize_ocr_summary_payload(result["data"])
            doc.ocr_summary = json.dumps(normalized_summary, ensure_ascii=False)

        session.add(doc)
        session.commit()

        if normalized_summary is not None:
            # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
            from backend.core.cache import CacheManager

            invalidate_result = CacheManager.invalidate_user_cache(current_user.id)
            if inspect.isawaitable(invalidate_result):
                await invalidate_result
            logger.info("Cache invalidated after OCR upload for user %s", current_user.id)

        response_data = normalized_summary if normalized_summary is not None else result.get("data")

        return {
            **result,
            "status": effective_status,
            "data": response_data,
            "document_id": doc.id,
            "file_url": file_url,
            "ocr_processing_status": normalized_status,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        logger.error("OCR Upload Endpoint Error: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
