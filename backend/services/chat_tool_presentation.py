from typing import Any, Dict


def build_tool_status_message(tool_name: str) -> str:
    """生成工具开始执行时的中文状态文案。"""
    # 这些文案只服务于 SSE 进度展示，不参与工具执行和 API 契约判定。
    tool_messages = {
        "medication_summary_lookup": "正在读取健康用药摘要。",
        "recent_metric_anomaly_lookup": "正在整理近期指标异常。",
        "report_comparison_lookup": "正在比对两份报告摘要。",
        "get_user_profile_summary": "正在读取您的健康档案摘要。",
        "get_latest_risk_report": "正在查看最新风险评估结果。",
        "get_history_trends": "正在整理近期健康趋势变化。",
        "get_uploaded_documents_summary": "正在查阅已上传报告的 OCR 摘要。",
        "report_summary_lookup": "正在读取最新报告摘要。",
        "recent_abnormal_metrics_lookup": "正在整理近期异常指标。",
        "latest_analysis_snapshot_lookup": "正在读取最新分析快照。",
        "search_medical_guidelines": "正在比对医学知识与指南证据。",
    }
    return tool_messages.get(tool_name, f"正在执行工具：{tool_name}")


def build_tool_done_message(tool_name: str) -> str:
    """生成工具执行完成时的中文状态文案。"""
    # 与 build_tool_status_message 分开维护，避免完成态误用进行中文案。
    tool_messages = {
        "medication_summary_lookup": "用药摘要读取完成",
        "recent_metric_anomaly_lookup": "指标异常整理完成",
        "report_comparison_lookup": "报告比对完成",
        "get_user_profile_summary": "健康档案读取完成",
        "get_latest_risk_report": "风险报告读取完成",
        "get_history_trends": "历史趋势分析完成",
        "get_uploaded_documents_summary": "报告摘要读取完成",
        "report_summary_lookup": "报告摘要读取完成",
        "recent_abnormal_metrics_lookup": "异常指标整理完成",
        "latest_analysis_snapshot_lookup": "分析快照读取完成",
        "search_medical_guidelines": "医学指南检索完成",
    }
    return tool_messages.get(tool_name, f"{tool_name} completed")


def summarize_tool_output_for_prompt(tool_name: str, result: Dict[str, Any]) -> str:
    """把工具结果压缩成稳定、短小、可进入提示词的证据摘要。"""
    # 该摘要只保留计数和命中信号，避免把长文本或敏感明细塞回模型上下文。
    if tool_name == "medication_summary_lookup":
        summary = result.get("medication_summary") or {}
        count = summary.get("count")
        return f"medication items={count}" if count is not None else "medication summary reviewed"
    if tool_name in {"recent_metric_anomaly_lookup", "recent_abnormal_metrics_lookup"}:
        summary = result.get("summary") or {}
        count = summary.get("count")
        return f"abnormal metrics={count}" if count is not None else "abnormal metrics reviewed"
    if tool_name == "report_comparison_lookup":
        summary = result.get("summary") or {}
        count = summary.get("count")
        shared = result.get("shared_metric_count")
        if count is not None and shared is not None:
            return f"report differences={count}, comparable_fields={shared}"
        return "report comparison reviewed"
    if tool_name == "report_summary_lookup":
        summary = result.get("report_summary") or {}
        metric_count = len(summary.get("metrics") or [])
        file_name = result.get("file_name") or "report"
        return f"{file_name}, metrics={metric_count}"
    if tool_name == "get_history_trends":
        return f"trend records={result.get('count') or 0}"
    if tool_name == "get_uploaded_documents_summary":
        return f"uploaded documents={result.get('count') or 0}"
    if tool_name == "get_user_profile_summary":
        present_fields = [
            key
            for key in ("age", "gender", "bmi", "sbp", "dbp", "glucose_fasting")
            if result.get(key) is not None
        ]
        return f"profile fields={len(present_fields)}"
    if tool_name == "get_latest_risk_report":
        findings = (result.get("risk_report") or {}).get("top_findings") or []
        return f"snapshot findings={len(findings)}"
    if tool_name == "latest_analysis_snapshot_lookup":
        findings = result.get("top_findings") or []
        return f"snapshot findings={len(findings)}"
    if tool_name == "search_medical_guidelines":
        return f"guideline matches={1 if result.get('matches_found') else 0}"
    return "bounded evidence reviewed"
