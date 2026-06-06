from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from backend.database import get_session
from backend.auth import get_current_user
from backend.models import User, IoTHealthData
from pydantic import BaseModel
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class IoTDataCreate(BaseModel):
    """中文说明：IoTDataCreate 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""

    device_type: str
    value: float
    unit: str
    recorded_at: str # ISO string

@router.post("/sync/batch")
async def sync_iot_batch(
    data_list: List[IoTDataCreate],
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Batch upload IoT sensor data (e.g. from Web Bluetooth).
    Trigger alert if HR is abnormal.
    """
    try:
        # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
        new_records = []
        abnormal_detected = False
        hr_sum = 0
        hr_count = 0

        for item in data_list:
            # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
            record = IoTHealthData(
                user_id=current_user.id,
                device_type=item.device_type,
                data_type="heart_rate" if item.unit == "bpm" else "unknown",
                value=item.value,
                unit=item.unit,
                recorded_at=datetime.fromisoformat(item.recorded_at.replace("Z", "+00:00"))
            )
            new_records.append(record)

            # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
            if item.device_type == "BLE_HRM" and item.unit == "bpm":
                hr_sum += item.value
                hr_count += 1
                if item.value > 120 or item.value < 40:
                    abnormal_detected = True

        # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
        db.add_all(new_records)
        db.commit()

        # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
        fusion_result = None
        if hr_count > 0:
            try:
                # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
                # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
                from backend.main import fusion_engine

                avg_hr = hr_sum / hr_count
                # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
                if not current_user.profile:
                     # Refresh or something if needed, but SQLModel relationship should handle valid session
                     pass
                     
                if fusion_engine:
                    fusion_result = await fusion_engine.update_realtime_risk(
                        user_profile=current_user.profile,
                        latest_hr=avg_hr,
                    )
            except Exception as e:
                logger.warning("Fusion trigger failed: %s", e)
                # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。

        return {
            "status": "success", 
            "count": len(new_records),
            "alert": "Abnormal Heart Rate Detected!" if abnormal_detected else None,
            "fusion_update": fusion_result
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
