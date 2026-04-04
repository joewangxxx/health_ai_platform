from backend.services.context_builder import (
    DEFAULT_CONTEXT_BUDGETS,
    build_context_payload,
    trim_history_to_token_budget,
)


def test_build_context_payload_trims_large_sections():
    payload = build_context_payload(
        profile_summary="P" * 4000,
        rag_context="R" * 12000,
        tool_evidence_text="T" * 6000,
        query="我最近血糖偏高，应该注意什么？",
    )

    assert "[truncated]" in payload["profile_summary"]
    assert "[truncated]" in payload["rag_context"]
    assert "[truncated]" in payload["tool_evidence_text"]
    assert payload["budget_summary"]["profile"]["used"] <= DEFAULT_CONTEXT_BUDGETS["profile"]
    assert payload["budget_summary"]["rag"]["used"] <= DEFAULT_CONTEXT_BUDGETS["rag"]
    assert payload["budget_summary"]["tools"]["used"] <= DEFAULT_CONTEXT_BUDGETS["tools"]


def test_trim_history_to_token_budget_keeps_recent_messages():
    history = [
        {"role": "user", "content": "A" * 600},
        {"role": "assistant", "content": "B" * 600},
        {"role": "user", "content": "C" * 600},
        {"role": "assistant", "content": "D" * 600},
    ]

    trimmed = trim_history_to_token_budget(history, token_budget=320)

    assert [message["content"][0] for message in trimmed] == ["C", "D"]
