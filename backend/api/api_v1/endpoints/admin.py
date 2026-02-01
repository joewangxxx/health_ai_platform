"""
Admin API Endpoints (Task 85: Research Data Export)
"""
import hashlib
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import User, UserProfile
from backend.auth import get_current_active_superuser
from backend.core.config import settings

router = APIRouter()

# Secret salt for anonymization (should ideally be in .env)
RESEARCH_SALT = getattr(settings, 'RESEARCH_SALT', 'health_ai_research_2024')


def anonymize_user_id(user_id: int) -> str:
    """Generate anonymous ID using SHA256 hash with salt."""
    raw = f"{user_id}{RESEARCH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@router.get("/research/export")
async def export_research_data(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_active_superuser)
):
    """
    Task 85: Export anonymized research data.
    
    - Only includes users who opted in (allow_research=True)
    - Strips all PII (name, email, phone, user_id)
    - Generates anonymized ID for each record
    - Returns only physiological metrics and risk assessments
    """
    # Query only consenting users
    statement = select(UserProfile).where(UserProfile.allow_research == True)
    profiles = session.exec(statement).all()
    
    if not profiles:
        return {
            "status": "success",
            "count": 0,
            "message": "No users have opted in for research data sharing.",
            "data": []
        }
    
    # Anonymize and extract research-relevant fields
    research_data = []
    
    # Define which fields to export (NO PII)
    export_fields = [
        # Demographics (non-identifying)
        "Age", "Gender",
        # Body metrics
        "Height", "Weight", "BMI", "WaistCircum", "SBP", "DBP",
        # Biochemistry
        "Glucose_Fasting", "HbA1c", "Cholesterol_Total", "Triglycerides",
        "Cholesterol_HDL", "Cholesterol_LDL", "eGFR", "ALT",
        # Blood panel
        "WBC", "Platelet", "GGT", "ALP", "Creatinine",
        # Lifestyle
        "Sleep_Hours",
        # Extra unstructured findings
        "extra_data",
        # Risk assessment (already anonymized since it's computed)
        "risk_history"
    ]
    
    for profile in profiles:
        record = {
            "anon_id": anonymize_user_id(profile.user_id),
        }
        
        # Extract allowed fields
        for field in export_fields:
            value = getattr(profile, field, None)
            if value is not None:
                record[field] = value
        
        research_data.append(record)
    
    return {
        "status": "success",
        "count": len(research_data),
        "message": f"Exported {len(research_data)} anonymized records for research.",
        "data": research_data
    }


@router.get("/research/stats")
async def get_research_stats(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_active_superuser)
):
    """Get statistics on research data availability."""
    # Count total profiles
    total_profiles = session.exec(select(UserProfile)).all()
    
    # Count consenting users
    consenting = session.exec(
        select(UserProfile).where(UserProfile.allow_research == True)
    ).all()
    
    return {
        "total_profiles": len(total_profiles),
        "research_consenting": len(consenting),
        "consent_rate": round(len(consenting) / max(len(total_profiles), 1) * 100, 1)
    }
