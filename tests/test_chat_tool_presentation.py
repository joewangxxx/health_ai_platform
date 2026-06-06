from backend.services.chat_tool_presentation import (
    build_tool_done_message,
    build_tool_status_message,
    summarize_tool_output_for_prompt,
)


def test_chat_tool_presentation_keeps_readable_chinese_status_messages():
    assert build_tool_status_message("medication_summary_lookup") == "正在读取健康用药摘要。"
    assert build_tool_status_message("recent_metric_anomaly_lookup") == "正在整理近期指标异常。"
    assert build_tool_status_message("report_comparison_lookup") == "正在比对两份报告摘要。"
    assert build_tool_status_message("unknown_tool") == "正在执行工具：unknown_tool"


def test_chat_tool_presentation_keeps_readable_chinese_done_messages():
    assert build_tool_done_message("medication_summary_lookup") == "用药摘要读取完成"
    assert build_tool_done_message("recent_metric_anomaly_lookup") == "指标异常整理完成"
    assert build_tool_done_message("report_comparison_lookup") == "报告比对完成"
    assert build_tool_done_message("unknown_tool") == "unknown_tool completed"


def test_chat_tool_presentation_summarizes_bounded_tool_outputs():
    assert (
        summarize_tool_output_for_prompt(
            "report_comparison_lookup",
            {"summary": {"count": 2}, "shared_metric_count": 6},
        )
        == "report differences=2, comparable_fields=6"
    )
    assert (
        summarize_tool_output_for_prompt(
            "report_summary_lookup",
            {"file_name": "体检报告.pdf", "report_summary": {"metrics": [{"name": "BMI"}, {"name": "UA"}]}},
        )
        == "体检报告.pdf, metrics=2"
    )
    assert summarize_tool_output_for_prompt("unknown_tool", {}) == "bounded evidence reviewed"
