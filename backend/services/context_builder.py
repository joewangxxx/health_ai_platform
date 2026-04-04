import math
from typing import Dict, List


DEFAULT_CONTEXT_BUDGETS: Dict[str, int] = {
    "profile": 500,
    "rag": 1500,
    "tools": 800,
    "history": 320,
    "query": 300,
}

TRUNCATION_MARKER = "\n[truncated]"


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def trim_text_to_token_budget(text: str, token_budget: int) -> str:
    if not text:
        return ""
    if token_budget <= 0:
        return ""

    used_tokens = estimate_tokens(text)
    if used_tokens <= token_budget:
        return text

    marker_budget = estimate_tokens(TRUNCATION_MARKER)
    allowed_budget = max(1, token_budget - marker_budget)
    max_chars = max(1, allowed_budget * 4)
    return f"{text[:max_chars]}{TRUNCATION_MARKER}"


def trim_history_to_token_budget(history: List[Dict[str, str]], token_budget: int) -> List[Dict[str, str]]:
    if token_budget <= 0:
        return []

    kept: List[Dict[str, str]] = []
    used = 0
    for message in reversed(history):
        content = message.get("content", "")
        role = message.get("role", "")
        message_tokens = estimate_tokens(content) + estimate_tokens(role)
        if kept and used + message_tokens > token_budget:
            break
        if not kept and message_tokens > token_budget:
            trimmed_content = trim_text_to_token_budget(content, max(1, token_budget - estimate_tokens(role)))
            kept.append({"role": role, "content": trimmed_content})
            break
        kept.append({"role": role, "content": content})
        used += message_tokens

    kept.reverse()
    return kept


def build_context_payload(
    *,
    profile_summary: str,
    rag_context: str,
    tool_evidence_text: str,
    query: str,
    budgets: Dict[str, int] | None = None,
) -> Dict[str, object]:
    active_budgets = {**DEFAULT_CONTEXT_BUDGETS, **(budgets or {})}

    trimmed_profile = trim_text_to_token_budget(profile_summary, active_budgets["profile"])
    trimmed_rag = trim_text_to_token_budget(rag_context, active_budgets["rag"])
    trimmed_tools = trim_text_to_token_budget(tool_evidence_text, active_budgets["tools"])
    trimmed_query = trim_text_to_token_budget(query, active_budgets["query"])

    return {
        "profile_summary": trimmed_profile,
        "rag_context": trimmed_rag,
        "tool_evidence_text": trimmed_tools,
        "query": trimmed_query,
        "budget_summary": {
            "profile": {"budget": active_budgets["profile"], "used": estimate_tokens(trimmed_profile)},
            "rag": {"budget": active_budgets["rag"], "used": estimate_tokens(trimmed_rag)},
            "tools": {"budget": active_budgets["tools"], "used": estimate_tokens(trimmed_tools)},
            "query": {"budget": active_budgets["query"], "used": estimate_tokens(trimmed_query)},
            "history": {"budget": active_budgets["history"]},
        },
    }
