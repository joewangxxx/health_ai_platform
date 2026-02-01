from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from backend.database import get_session
from backend.auth import get_current_user
from backend.models import User, IoTHealthData
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class IoTDataCreate(BaseModel):
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
        new_records = []
        abnormal_detected = False
        hr_sum = 0
        hr_count = 0
        
        for item in data_list:
            # Create DB Record
            record = IoTHealthData(
                user_id=current_user.id,
                device_type=item.device_type,
                data_type="heart_rate" if item.unit == "bpm" else "unknown",
                value=item.value,
                unit=item.unit,
                recorded_at=datetime.fromisoformat(item.recorded_at.replace("Z", "+00:00"))
            )
            new_records.append(record)
            
            # Simple Rule Engine Trigger
            if item.device_type == "BLE_HRM" and item.unit == "bpm":
                hr_sum += item.value
                hr_count += 1
                if item.value > 120 or item.value < 40:
                    abnormal_detected = True

        # Batch Insert
        db.add_all(new_records)
        db.commit()
        
        # ⚡ Trigger Fusion Engine (Real-time Bayesian Update)
        fusion_result = None
        if hr_count > 0:
            try:
                # Lazy import to avoid circular dependency
                # Note: 'backend.main' imports this router, so we must import 'backend.main' inside function
                from backend.main import fusion_engine
                
                avg_hr = hr_sum / hr_count
                # Ensure profile is loaded
                if not current_user.profile:
                     # Refresh or something if needed, but SQLModel relationship should handle valid session
                     pass
                     
                if fusion_engine:
                    fusion_result = await fusion_engine.update_realtime_risk(
                        user_profile=current_user.profile, 
                        latest_hr=avg_hr
                    )
            except Exception as e:
                print(f"Fusion Trigger Failed: {e}")
                # Don't fail the upload just because fusion failed
        
        return {
            "status": "success", 
            "count": len(new_records),
            "alert": "Abnormal Heart Rate Detected!" if abnormal_detected else None,
            "fusion_update": fusion_result
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
