from __future__ import annotations

import argparse
import json
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Optional
import asyncio
from unittest.mock import AsyncMock, patch

from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from backend.models import User, UserProfile
from backend.services.chat_service import ChatService

MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST_PATH = MODULE_DIR / "agent_behavior_manifest.json"
DEFAULT_BASELINE_PATH = MODULE_DIR / "baselines" / "agent_behavior_baseline.json"
DEFAULT_OUTPUT_DIR = MODULE_DIR / "artifacts"
BASELINE_STATE_UNCHECKED = "unchecked"
BASELINE_STATE_MATCHED = "matched"
BASELINE_STATE_MISMATCHED = "mismatched"

REQUIRED_SCENARIO_CLASSES = {
    "urgent_triage",
    "report_interpretation",
    "trend_explanation",
    "medication_qa",
    "insufficient_evidence_refusal",
    "tool_failure_degradation",
}


def load_agent_behavior_manifest(manifest_path: Path | str | None = None) -> Dict[str, Any]:
    path = Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST_PATH
    manifest = json.loads(path.read_text(encoding="utf-8"))
    _validate_manifest(manifest, path)
    return manifest


def run_agent_behavior_eval(
    *,
    manifest_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    baseline_path: Path | str | None = None,
) -> Dict[str, Any]:
    manifest = load_agent_behavior_manifest(manifest_path)
    output_path = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path.mkdir(parents=True, exist_ok=True)

    scenario_results: list[Dict[str, Any]] = []
    failure_samples: list[Dict[str, Any]] = []

    for scenario in manifest["scenarios"]:
        result = _run_scenario(scenario)
        scenario_results.append(result)
        if not result["passed"]:
            failure_samples.append(_build_failure_sample(result))

    summary = {
        "manifest_version": manifest["manifest_version"],
        "scenario_count": len(scenario_results),
        "passed_count": sum(1 for item in scenario_results if item["passed"]),
        "failed_count": sum(1 for item in scenario_results if not item["passed"]),
    }
    baseline_snapshot = {
        "manifest_version": manifest["manifest_version"],
        "scenarios": [_scenario_snapshot(item) for item in scenario_results],
    }

    baseline_match = None
    baseline_differences: list[Dict[str, Any]] = []
    baseline_state = BASELINE_STATE_UNCHECKED
    baseline_file = Path(baseline_path) if baseline_path is not None else None
    if baseline_file is not None and baseline_file.exists():
        baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
        baseline_match = baseline == baseline_snapshot
        baseline_state = BASELINE_STATE_MATCHED if baseline_match else BASELINE_STATE_MISMATCHED
        if not baseline_match:
            baseline_differences = _diff_baseline(baseline, baseline_snapshot)

    report = {
        "manifest_path": str(Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST_PATH),
        "baseline_path": str(baseline_file) if baseline_file is not None else None,
        "summary": summary,
        "results": scenario_results,
        "failure_samples": failure_samples,
        "baseline_snapshot": baseline_snapshot,
        "baseline_match": baseline_match,
        "baseline_state": baseline_state,
        "baseline_differences": baseline_differences,
    }

    (output_path / "agent_behavior_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_path / "agent_behavior_failure_samples.json").write_text(
        json.dumps({"samples": failure_samples, "summary": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return report


def write_agent_behavior_baseline(
    report: Dict[str, Any],
    baseline_path: Path | str | None = None,
) -> Path:
    path = Path(baseline_path) if baseline_path is not None else DEFAULT_BASELINE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report["baseline_snapshot"], ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _run_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    engine = _build_engine()
    with Session(engine) as session:
        user = _seed_user(session, scenario.get("user") or {})
        with ExitStack() as stack:
            _patch_runtime(stack, scenario)
            service = ChatService()
            service.client = _build_fake_client(scenario)
            response = asyncio.run(
                service.chat(
                    user=user,
                    query=scenario["query"],
                    session=session,
                    conversation_id=None,
                    force_refresh=True,
                )
            )
        return _build_result_record(scenario, response, scenario["expected"])


def _patch_runtime(stack: ExitStack, scenario: Dict[str, Any]) -> None:
    tool_outputs = scenario.get("tool_outputs") or {}
    rag_spec = scenario.get("rag") or {}

    def fake_execute_registered_tool(tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        output = tool_outputs.get(tool_name)
        if output is None:
            return {"status": "blocked", "reason": "tool_unavailable", "tool": tool_name}
        return deepcopy(output)

    async def fake_cache_get(*args: Any, **kwargs: Any) -> None:
        return None

    async def fake_cache_set(*args: Any, **kwargs: Any) -> None:
        return None

    def fake_search_context_with_quality(query: str, k: int = 3) -> Dict[str, Any]:
        if not isinstance(rag_spec, dict):
            return {"context": "", "rag_quality_summary": None}
        return {
            "context": rag_spec.get("context") or "",
            "rag_quality_summary": deepcopy(rag_spec.get("quality_summary")),
        }

    def fake_search_context(query: str, k: int = 3) -> str:
        if not isinstance(rag_spec, dict):
            return ""
        return rag_spec.get("context") or ""

    stack.enter_context(patch("backend.services.chat_service.execute_registered_tool", side_effect=fake_execute_registered_tool))
    stack.enter_context(patch("backend.services.chat_service.CacheManager.get", new=AsyncMock(return_value=None)))
    stack.enter_context(patch("backend.services.chat_service.CacheManager.set", new=AsyncMock(return_value=None)))
    stack.enter_context(
        patch("backend.services.chat_service.rag_service.search_context_with_quality", side_effect=fake_search_context_with_quality, create=True)
    )
    stack.enter_context(patch("backend.services.chat_service.rag_service.search_context", side_effect=fake_search_context, create=True))


class _FakeCompletions:
    def __init__(self, final_reply: str):
        self.final_reply = final_reply
        self.calls = 0

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls += 1
        if self.calls == 1:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="", tool_calls=None),
                    )
                ]
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.final_reply, tool_calls=None),
                )
            ]
        )


def _build_fake_client(scenario: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions(scenario.get("final_reply") or "Agent evaluation complete.")))


def _build_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _seed_user(session: Session, user_spec: Dict[str, Any]) -> User:
    user = User(
        username=user_spec.get("username", "agent_eval_user"),
        email=user_spec.get("email", "agent_eval_user@example.com"),
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    profile_spec = user_spec.get("profile")
    if isinstance(profile_spec, dict):
        profile = UserProfile(user_id=user.id, **profile_spec)
        session.add(profile)
        session.commit()
        session.refresh(profile)
        user.profile = profile

    return user


def _scenario_snapshot(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "scenario_class": result["scenario_class"],
        "title": result["title"],
        "passed": result["passed"],
        "observed": result["observed"],
        "reply_excerpt": result["reply_excerpt"],
    }


def _build_failure_sample(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "scenario_class": result["scenario_class"],
        "title": result["title"],
        "failed_checks": result["failed_checks"],
        "observed": result["observed"],
        "reply_excerpt": result["reply_excerpt"],
    }


def _diff_baseline(expected: Dict[str, Any], observed: Dict[str, Any]) -> list[Dict[str, Any]]:
    expected_scenarios = {item["scenario_class"]: item for item in expected.get("scenarios", []) if isinstance(item, dict)}
    observed_scenarios = {item["scenario_class"]: item for item in observed.get("scenarios", []) if isinstance(item, dict)}
    diffs: list[Dict[str, Any]] = []

    for scenario_class in sorted(set(expected_scenarios) | set(observed_scenarios)):
        if expected_scenarios.get(scenario_class) != observed_scenarios.get(scenario_class):
            diffs.append(
                {
                    "scenario_class": scenario_class,
                    "expected": expected_scenarios.get(scenario_class),
                    "observed": observed_scenarios.get(scenario_class),
                }
            )
    return diffs


def _validate_manifest(manifest: Dict[str, Any], path: Path) -> None:
    if manifest.get("manifest_version") != 1:
        raise ValueError(f"Invalid manifest version in {path}")
    scenarios = manifest.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError(f"Manifest {path} must include scenarios")
    scenario_classes = {item.get("scenario_class") for item in scenarios if isinstance(item, dict)}
    if scenario_classes != REQUIRED_SCENARIO_CLASSES:
        raise ValueError(
            "Manifest must cover the required scenario classes: "
            f"{sorted(REQUIRED_SCENARIO_CLASSES)}"
        )
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError(f"Invalid scenario entry in {path}")
        for key in ("scenario_class", "title", "query", "expected"):
            if key not in scenario:
                raise ValueError(f"Scenario is missing '{key}' in {path}")


def _check_value(*, path: str, expected: Any, observed: Any, failures: list[Dict[str, Any]]) -> None:
    if expected != observed:
        failures.append(
            {
                "check": path,
                "expected": expected,
                "observed": observed,
            }
        )


def _check_contains(*, path: str, expected_values: Iterable[Any], observed_values: Iterable[Any], failures: list[Dict[str, Any]]) -> None:
    observed_set = set(observed_values)
    missing = [value for value in expected_values if value not in observed_set]
    if missing:
        failures.append(
            {
                "check": path,
                "expected_contains": list(expected_values),
                "missing": missing,
                "observed": list(observed_values),
            }
        )


def _extract_text_excerpt(reply: str, limit: int = 160) -> str:
    normalized = " ".join(str(reply or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _build_result_record(
    scenario: Dict[str, Any],
    response: Dict[str, Any],
    expected: Dict[str, Any],
) -> Dict[str, Any]:
    decision_summary = response["decision_summary"]
    response_verdict = response["response_verdict"] or {}
    observed = {
        "lane": decision_summary.get("lane"),
        "verdict": decision_summary.get("verdict"),
        "policy_answer_mode": decision_summary.get("policy", {}).get("answer_mode"),
        "policy_degrade_reason": decision_summary.get("policy", {}).get("degrade_reason"),
        "policy_tool_availability": decision_summary.get("policy", {}).get("tool_availability"),
        "response_mode": response_verdict.get("response_mode"),
        "response_degraded_reason": response_verdict.get("degraded_reason"),
        "evidence_sufficiency": response_verdict.get("evidence_sufficiency"),
        "human_escalation_required": response_verdict.get("human_escalation_required"),
        "tool_used": list(decision_summary.get("tool_used") or []),
        "evidence_tags": list(response.get("evidence_tags") or []),
    }

    failures: list[Dict[str, Any]] = []
    _check_value(path="lane", expected=expected.get("lane"), observed=observed["lane"], failures=failures)
    _check_value(path="verdict", expected=expected.get("verdict"), observed=observed["verdict"], failures=failures)
    _check_value(
        path="policy_answer_mode",
        expected=expected.get("policy_answer_mode"),
        observed=observed["policy_answer_mode"],
        failures=failures,
    )
    _check_value(
        path="policy_degrade_reason",
        expected=expected.get("policy_degrade_reason"),
        observed=observed["policy_degrade_reason"],
        failures=failures,
    )
    _check_value(
        path="response_mode",
        expected=expected.get("response_mode"),
        observed=observed["response_mode"],
        failures=failures,
    )
    _check_value(
        path="response_degraded_reason",
        expected=expected.get("response_degraded_reason"),
        observed=observed["response_degraded_reason"],
        failures=failures,
    )
    _check_value(
        path="evidence_sufficiency",
        expected=expected.get("evidence_sufficiency"),
        observed=observed["evidence_sufficiency"],
        failures=failures,
    )
    _check_value(
        path="human_escalation_required",
        expected=expected.get("human_escalation_required"),
        observed=observed["human_escalation_required"],
        failures=failures,
    )
    _check_contains(
        path="tool_used",
        expected_values=expected.get("tool_used_contains") or [],
        observed_values=observed["tool_used"],
        failures=failures,
    )
    _check_contains(
        path="evidence_tags",
        expected_values=expected.get("evidence_tags_contains") or [],
        observed_values=observed["evidence_tags"],
        failures=failures,
    )

    reply_excerpt = _extract_text_excerpt(response.get("reply") or "")
    if expected.get("reply_excerpt_contains"):
        _check_contains(
            path="reply_excerpt",
            expected_values=expected["reply_excerpt_contains"],
            observed_values=[reply_excerpt],
            failures=failures,
        )

    return {
        "scenario_class": scenario["scenario_class"],
        "title": scenario["title"],
        "passed": not failures,
        "failed_checks": failures,
        "observed": observed,
        "reply_excerpt": reply_excerpt,
        "raw_response": response,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the agent behavior evaluation harness.")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)

    report = run_agent_behavior_eval(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        baseline_path=args.baseline,
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

    if args.write_baseline:
        write_agent_behavior_baseline(report, args.baseline)
        return 0

    if report["summary"]["failed_count"] > 0:
        return 1

    if report.get("baseline_state") == BASELINE_STATE_MISMATCHED:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
