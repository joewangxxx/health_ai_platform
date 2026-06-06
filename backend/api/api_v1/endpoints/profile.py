from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from backend.auth import get_current_user
from backend.models import User
from backend.services.profile_csv_import import ProfileCsvImportError, parse_platform_profile_csv


router = APIRouter()


def _looks_like_csv(file: UploadFile) -> bool:
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    return filename.endswith(".csv") or content_type in {"text/csv", "application/csv", "application/vnd.ms-excel"}


@router.post("/import-csv")
async def import_profile_csv(
    request: Request,
    file: UploadFile = File(...),
    demo_patient_id: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    if not _looks_like_csv(file):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    selector = demo_patient_id or request.query_params.get("demo_patient_id")
    try:
        content = await file.read()
        return parse_platform_profile_csv(content, demo_patient_id=selector, filename=file.filename)
    except ProfileCsvImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
