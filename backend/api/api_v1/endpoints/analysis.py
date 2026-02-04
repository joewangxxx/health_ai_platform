"""
Health Analysis API Endpoints
=============================

提供健康分析相关的 API 端点，包括：
- 未来风险模拟 (simulate_future)
- 干预措施模拟 (simulate_intervention)
- 异常指标检测 (detect_anomalies)
- PDF 健康报告导出 (export_pdf)

Author: Health AI Platform Team
"""
from datetime import datetime
from typing import Dict, Any
import io

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from backend.database import get_session
from backend.models import User
from backend.auth import get_current_user
from backend.services.projection_service import projection_service
from backend.services.analysis_service import anomaly_service
from backend.services.pdf_service import pdf_service, PDFGenerationError
from backend.services.risk_engine import disease_risk_engine
from backend.services.lifestyle_service import hydration_advisor

router = APIRouter()

@router.post("/simulate/future")
async def simulate_future(
    years: int = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Project health risk N years into the future (Natural Progression)
    """
    if not current_user.profile:
        raise HTTPException(400, "User profile not found. Please complete clinical data first.")
        
    result = projection_service.simulate_future_risk(current_user.profile, years=years)
    return {"status": "success", "data": result}

@router.post("/simulate/intervention")
async def simulate_intervention(
    target: Dict[str, Any] = Body(...), # e.g. {"weight_loss_percent": 0.05}
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Simulate health risk after intervention
    """
    if not current_user.profile:
        raise HTTPException(400, "User profile not found")
        
    result = projection_service.simulate_intervention(current_user.profile, intervention=target)
    return {"status": "success", "data": result}


# ================= Task 88: Anomaly Detection =================


@router.post("/detect_anomalies")
async def detect_anomalies(
    clinical_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Task 88: Detect anomalies in clinical data.
    
    Input: Dict with indicator names as keys.
           Values can be simple numbers or objects with {value, unit, ref_range, hospital_flag}
    
    Output: {
        "status": "success",
        "anomalies": [...],
        "summary": {...}
    }
    """
    anomalies = anomaly_service.detect_anomalies(clinical_data)
    summary = anomaly_service.generate_summary(anomalies)
    
    return {
        "status": "success",
        "anomalies": anomalies,
        "summary": summary
    }


@router.get("/detect_anomalies/profile")
async def detect_anomalies_from_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Detect anomalies using the user's stored profile data.
    """
    if not current_user.profile:
        raise HTTPException(400, "User profile not found")
    
    # Convert profile to dict
    profile_data = current_user.profile.model_dump(exclude_unset=True)
    
    anomalies = anomaly_service.detect_anomalies(profile_data)
    summary = anomaly_service.generate_summary(anomalies)
    
    return {
        "status": "success",
        "anomalies": anomalies,
        "summary": summary
    }


# ================= Task 101: PDF Export =================


@router.post("/export/pdf")
async def export_health_report_pdf(
    include_hydration: bool = True,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Task 101: 导出健康报告 PDF
    
    生成包含以下内容的专业健康报告:
    - 封面 (用户信息、报告日期)
    - 健康综述 (AI 分析)
    - 风险评估表
    - CKM 分期 (如适用)
    - 个性化建议 (饮食、水合计划)
    """
    if not current_user.profile:
        raise HTTPException(400, "User profile not found. Please complete clinical data first.")
    
    try:
        # 1. 收集用户数据
        profile_data = current_user.profile.model_dump(exclude_unset=True)
        profile_data["name"] = current_user.username
        
        # 2. 获取风险评估
        risk_data = disease_risk_engine.assess_health(profile_data)
        
        # 3. 获取 CKM 分期
        ckm_data = disease_risk_engine.assess_ckm_stage(profile_data)
        
        # 4. 生成 AI 分析摘要
        ai_analysis = _generate_ai_summary(profile_data, risk_data, ckm_data)
        
        # 5. 获取水合计划 (可选)
        hydration_plan = None
        if include_hydration:
            hydration_plan = hydration_advisor.calculate_water_plan(profile_data)
        
        # 6. 生成饮食建议
        diet_advice = _generate_diet_advice(risk_data, ckm_data)
        
        # 7. 生成 PDF
        pdf_bytes = pdf_service.create_health_report(
            user_profile=profile_data,
            risk_data=risk_data,
            ai_analysis_text=ai_analysis,
            ckm_data=ckm_data,
            diet_advice=diet_advice,
            hydration_plan=hydration_plan,
        )
        
        # 8. 返回 PDF 流
        filename = f"健康报告_{current_user.username}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
            }
        )
    
    except PDFGenerationError as e:
        raise HTTPException(500, f"PDF 生成失败: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"报告生成过程中发生错误: {str(e)}")


def _generate_ai_summary(profile: dict, risk_data: dict, ckm_data: dict) -> str:
    """生成 AI 健康摘要文本"""
    lines = []
    
    # 基本信息
    age = profile.get("Age", "-")
    bmi = profile.get("BMI", "-")
    lines.append(f"📋 本次评估基于您的健康数据进行分析。年龄 {age} 岁，BMI {bmi}。")
    lines.append("")
    
    # 高风险项目
    high_risks = [
        (k, v) for k, v in risk_data.items()
        if isinstance(v, dict) and v.get("probability", 0) >= 40
    ]
    
    if high_risks:
        lines.append("⚠️ 需要关注的风险项目:")
        for disease, data in sorted(high_risks, key=lambda x: -x[1].get("probability", 0)):
            disease_cn = data.get("disease_cn", disease)
            prob = data.get("probability", 0)
            lines.append(f"  • {disease_cn}: 风险概率 {prob}%")
        lines.append("")
    else:
        lines.append("✅ 目前各项疾病风险均在正常范围内。")
        lines.append("")
    
    # CKM 状态
    stage = ckm_data.get("stage", 0)
    stage_name = ckm_data.get("stage_name", "")
    if stage >= 2:
        lines.append(f"🫀 心肾代谢状态: {stage_name}")
        criteria = ckm_data.get("criteria_met", [])
        if criteria:
            lines.append(f"   判定依据: {', '.join(criteria[:3])}")
        lines.append("")
    
    # 总结建议
    lines.append("💡 建议:")
    if stage >= 2:
        lines.append("  • 定期监测血糖、血压、肾功能指标")
        lines.append("  • 控制体重，保持健康饮食")
    if high_risks:
        lines.append("  • 建议就医咨询，进一步检查")
    else:
        lines.append("  • 保持当前健康的生活方式")
        lines.append("  • 定期体检，预防为主")
    
    return "\n".join(lines)


def _generate_diet_advice(risk_data: dict, ckm_data: dict) -> list:
    """根据风险生成饮食建议"""
    advice = []
    
    # 高风险疾病对应的饮食建议
    risk_diet_map = {
        "T2D": "🍚 控制碳水化合物摄入，选择低GI食物",
        "Hypertension": "🧂 限盐饮食，每日钠摄入 < 5g",
        "CVD": "🫒 采用地中海饮食，增加 Omega-3 摄入",
        "FattyLiver": "🚫 戒酒，减少高脂肪食物",
        "Gout": "🥩 限制高嘌呤食物（内脏、海鲜）",
        "CKD": "🥛 控制蛋白质摄入，限制磷钾",
    }
    
    for disease, diet in risk_diet_map.items():
        if disease in risk_data:
            data = risk_data[disease]
            if isinstance(data, dict) and data.get("probability", 0) >= 30:
                advice.append(diet)
    
    # CKM 分期建议
    stage = ckm_data.get("stage", 0)
    if stage >= 2:
        advice.append("🥗 建议采用 DASH 饮食模式")
    
    if not advice:
        advice.append("🥗 保持均衡饮食，多摄入蔬果")
    
    return advice
