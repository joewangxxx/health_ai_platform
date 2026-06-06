from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlmodel import Session

from backend.auth import get_current_user
from backend.database import get_session
from backend.models import User, UserProfile
from backend.services.behavior_day_import import BehaviorDayImportError, parse_behavior_day_upload


router = APIRouter()


def _persist_latest_behavior_day(result: dict, current_user: User, session: Session) -> None:
    behavior_day = result.get("behavior_day")
    if not isinstance(behavior_day, dict):
        return

    profile = current_user.profile
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)
        session.flush()

    extra_data = dict(profile.extra_data or {})
    extra_data["latest_behavior_day"] = behavior_day
    if isinstance(behavior_day.get("lifestyle_context"), dict):
        extra_data["latest_lifestyle_context"] = behavior_day["lifestyle_context"]

    profile.extra_data = extra_data
    session.add(profile)
    session.commit()


@router.post("/import-behavior-day")
async def import_behavior_day(
    file: UploadFile = File(...),
    patient_id: str | None = Form(default=None),
    local_date: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        content = await file.read()
        result = parse_behavior_day_upload(
            content,
            filename=file.filename,
            content_type=file.content_type,
            patient_id=patient_id,
            local_date=local_date,
        )
        _persist_latest_behavior_day(result, current_user, session)
        result["persisted"] = True
        return result
    except BehaviorDayImportError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.to_response_body())
