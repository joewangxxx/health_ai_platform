from backend.services.agent_safety import enforce_tool_policy, evaluate_post_tool_sufficiency


def test_write_tool_is_blocked_for_normal_user():
    result = enforce_tool_policy(
        user_is_admin=False,
        tool_meta={"read_only": False, "scope": "admin_only"},
        acting_user_id=1,
        target_user_id=1,
    )

    assert result["allowed"] is False
    assert result["reason"] == "permission_denied"


def test_self_only_tool_blocks_cross_user_access():
    result = enforce_tool_policy(
        user_is_admin=False,
        tool_meta={"read_only": True, "scope": "self_only"},
        acting_user_id=1,
        target_user_id=2,
    )

    assert result["allowed"] is False
    assert result["reason"] == "scope_denied"


def test_admin_can_use_admin_only_tool():
    result = enforce_tool_policy(
        user_is_admin=True,
        tool_meta={"read_only": False, "scope": "admin_only"},
        acting_user_id=1,
        target_user_id=2,
    )

    assert result["allowed"] is True


def test_post_tool_sufficiency_blocks_empty_medication_result():
    result = evaluate_post_tool_sufficiency(
        lane="medication_related",
        allowed_tool_names=["medication_summary_lookup"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "medication_summary_lookup",
                "result": {
                    "has_medication_summary": False,
                    "medication_summary": None,
                },
            }
        ],
    )

    assert result["should_continue"] is False
    assert result["stop_reason"] == "tool_unavailable"
    assert result["evidence_state"] == "insufficient"


def test_post_tool_sufficiency_blocks_weak_trend_result():
    result = evaluate_post_tool_sufficiency(
        lane="trend_review",
        allowed_tool_names=["get_history_trends"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "get_history_trends",
                "result": {
                    "count": 1,
                    "items": [
                        {
                            "record_date": "2026-04-01T12:00:00",
                            "source": "manual_update",
                            "metrics": {"Glucose_Fasting": 6.8},
                        }
                    ],
                },
            }
        ],
    )

    assert result["should_continue"] is False
    assert result["stop_reason"] == "evidence_insufficient"
    assert result["evidence_state"] == "limited"


def test_post_tool_sufficiency_blocks_conflicting_evidence():
    result = evaluate_post_tool_sufficiency(
        lane="general_health",
        allowed_tool_names=["get_user_profile_summary", "search_medical_guidelines"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "get_user_profile_summary",
                "result": {
                    "has_profile": True,
                    "glucose_fasting": 6.9,
                    "abnormal_flags": ["fasting glucose high"],
                },
            }
        ],
        profile_evidence={"glucose_fasting": 6.9, "abnormal_flags": ["fasting glucose high"]},
        retrieval_evidence="Normal glucose guidance for healthy adults.",
    )

    assert result["should_continue"] is False
    assert result["stop_reason"] == "conflicting_evidence"
    assert result["evidence_state"] == "insufficient"
