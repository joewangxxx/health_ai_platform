import json
from pathlib import Path

from backend.eval.agent_behavior_eval import load_agent_behavior_manifest, main, run_agent_behavior_eval


REQUIRED_SCENARIO_CLASSES = {
    "urgent_triage",
    "report_interpretation",
    "trend_explanation",
    "medication_qa",
    "insufficient_evidence_refusal",
    "tool_failure_degradation",
}


def test_agent_behavior_manifest_covers_six_required_scenarios():
    manifest = load_agent_behavior_manifest()
    scenario_classes = {scenario["scenario_class"] for scenario in manifest["scenarios"]}

    assert manifest["manifest_version"] == 1
    assert scenario_classes == REQUIRED_SCENARIO_CLASSES


def test_agent_behavior_eval_matches_baseline_and_is_deterministic(tmp_path):
    report_first = run_agent_behavior_eval(output_dir=tmp_path)
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(report_first["baseline_snapshot"], ensure_ascii=False, indent=2), encoding="utf-8")

    second_output_dir = tmp_path / "second"
    report_second = run_agent_behavior_eval(output_dir=second_output_dir, baseline_path=baseline_path)

    assert report_first["summary"]["scenario_count"] == 6
    assert report_first["summary"]["failed_count"] == 0
    assert report_first["failure_samples"] == []
    assert report_second["baseline_match"] is True
    assert report_first["results"] == report_second["results"]

    latest_results = json.loads((second_output_dir / "agent_behavior_results.json").read_text(encoding="utf-8"))
    failure_samples = json.loads((second_output_dir / "agent_behavior_failure_samples.json").read_text(encoding="utf-8"))

    assert latest_results["summary"]["failed_count"] == 0
    assert failure_samples["samples"] == []


def test_agent_behavior_eval_records_failure_samples_for_regressions(tmp_path):
    manifest = load_agent_behavior_manifest()
    broken_manifest_path = tmp_path / "broken_manifest.json"

    broken_manifest = json.loads(json.dumps(manifest))
    broken_manifest["scenarios"][0]["expected"]["lane"] = "trend_review"
    broken_manifest_path.write_text(json.dumps(broken_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    baseline_path = tmp_path / "baseline.json"
    good_report = run_agent_behavior_eval(output_dir=tmp_path / "good")
    baseline_path.write_text(json.dumps(good_report["baseline_snapshot"], ensure_ascii=False, indent=2), encoding="utf-8")

    broken_report = run_agent_behavior_eval(
        manifest_path=broken_manifest_path,
        output_dir=tmp_path / "broken",
        baseline_path=baseline_path,
    )

    assert broken_report["summary"]["failed_count"] == 1
    assert broken_report["baseline_match"] is False
    assert broken_report["failure_samples"]
    assert broken_report["failure_samples"][0]["scenario_class"] == manifest["scenarios"][0]["scenario_class"]
    assert "lane" in broken_report["failure_samples"][0]["failed_checks"][0]["check"]
    broken_failure_samples = json.loads((tmp_path / "broken" / "agent_behavior_failure_samples.json").read_text(encoding="utf-8"))
    assert broken_failure_samples["samples"][0]["scenario_class"] == manifest["scenarios"][0]["scenario_class"]


def test_agent_behavior_eval_main_separates_stale_baselines_from_runtime_failures(tmp_path):
    fresh_report = run_agent_behavior_eval(output_dir=tmp_path / "fresh")
    stale_baseline_path = tmp_path / "stale_baseline.json"

    stale_snapshot = json.loads(json.dumps(fresh_report["baseline_snapshot"]))
    stale_snapshot["scenarios"][0]["title"] = "outdated title"
    stale_baseline_path.write_text(json.dumps(stale_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    drift_report = run_agent_behavior_eval(
        output_dir=tmp_path / "drift",
        baseline_path=stale_baseline_path,
    )

    assert drift_report["summary"]["failed_count"] == 0
    assert drift_report["baseline_match"] is False
    assert drift_report["baseline_state"] == "mismatched"
    assert drift_report["failure_samples"] == []
    assert drift_report["baseline_differences"]

    exit_code = main(
        [
            "--baseline",
            str(stale_baseline_path),
            "--output-dir",
            str(tmp_path / "cli-check"),
        ]
    )
    assert exit_code == 2

    refresh_exit_code = main(
        [
            "--baseline",
            str(stale_baseline_path),
            "--output-dir",
            str(tmp_path / "cli-refresh"),
            "--write-baseline",
        ]
    )
    assert refresh_exit_code == 0

    refreshed_snapshot = json.loads(stale_baseline_path.read_text(encoding="utf-8"))
    assert refreshed_snapshot == fresh_report["baseline_snapshot"]
