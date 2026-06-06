"""Evaluate OCR-text structured extraction on synthetic health-report samples.

The repository OCR provider depends on external Baidu credentials. This phase
therefore evaluates the deterministic post-OCR text extraction path:
MedicalOCRService._extract_by_regex -> normalize_ocr_summary_payload.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.config import PROJECT_ROOT
from backend.services.ocr_service import MedicalOCRService
from backend.services.payload_normalization import normalize_ocr_summary_payload


DEFAULT_SAMPLE_DIR = Path(PROJECT_ROOT) / "docs" / "evaluation" / "ocr-samples"
DEFAULT_OUTPUT_DIR = Path(PROJECT_ROOT) / "docs" / "evaluation"
FIELD_TOLERANCE = 0.011

SUPPORTED_RAW_FIELDS = [
    "BMI",
    "WBC",
    "HGB",
    "PLT",
    "ALT",
    "AST",
    "GGT",
    "Glu",
    "TC",
    "TG",
    "UA",
    "SBP",
    "DBP",
    "HbA1c",
    "Creatinine",
    "eGFR",
    "HDL",
    "LDL",
]
UNSUPPORTED_FALLBACK_FIELDS = []
ALL_EVAL_FIELDS = SUPPORTED_RAW_FIELDS + UNSUPPORTED_FALLBACK_FIELDS

CANONICAL_ALIAS = {
    "PLT": "Platelet",
    "Glu": "Glucose_Fasting",
    "TC": "Cholesterol_Total",
    "TG": "Triglycerides",
    "HDL": "Cholesterol_HDL",
    "LDL": "Cholesterol_LDL",
}


@dataclass(frozen=True)
class SyntheticReport:
    sample_id: str
    text: str
    raw_truth: dict[str, float]


def rounded(value: float, digits: int = 2) -> float:
    return round(value, digits)


def make_report(index: int, rng: random.Random) -> SyntheticReport:
    sample_id = f"sample_{index:03d}"
    age = rng.randint(24, 78)
    gender = rng.choice(["男", "女"])
    height = rng.randint(154, 184)
    weight = rounded(rng.uniform(49, 91), 1)
    bmi = rounded(weight / ((height / 100) ** 2), 1)
    sbp = rng.randint(105, 158)
    dbp = rng.randint(66, 98)

    truth = {
        "BMI": bmi,
        "WBC": rounded(rng.uniform(3.6, 9.4), 2),
        "HGB": float(rng.randint(112, 169)),
        "PLT": float(rng.randint(125, 360)),
        "ALT": float(rng.randint(11, 86)),
        "AST": float(rng.randint(12, 65)),
        "GGT": float(rng.randint(12, 96)),
        "Glu": rounded(rng.uniform(4.1, 8.9), 2),
        "TC": rounded(rng.uniform(3.3, 6.9), 2),
        "TG": rounded(rng.uniform(0.7, 3.6), 2),
        "UA": float(rng.randint(210, 520)),
        "SBP": float(sbp),
        "DBP": float(dbp),
        "HbA1c": rounded(rng.uniform(4.8, 7.6), 1),
        "Creatinine": float(rng.randint(48, 118)),
        "eGFR": float(rng.randint(62, 126)),
        "HDL": rounded(rng.uniform(0.85, 1.95), 2),
        "LDL": rounded(rng.uniform(1.6, 4.3), 2),
    }

    optional_drop: set[str] = set()
    if index % 5 == 0:
        optional_drop.update(["GGT", "UA"])
    if index % 7 == 0:
        optional_drop.update(["HGB", "PLT"])
    if index % 9 == 0:
        optional_drop.update(["AST", "TG"])
    if index % 11 == 0:
        optional_drop.update(["HDL", "LDL"])

    report_lines = [
        "HealthAI Platform Synthetic Physical Examination Report",
        f"Sample ID: {sample_id}",
        f"姓名: 测试用户{index:03d}",
        f"年龄: {age}",
        f"性别: {gender}",
        f"身高: {height} cm",
        f"体重: {weight} kg",
        f"血压: {sbp}/{dbp} mmHg",
        "---- 检验项目 ----",
    ]

    metric_templates = {
        "BMI": [f"BMI {truth['BMI']} kg/m2", f"BMI: {truth['BMI']}", f"BMI    {truth['BMI']}"],
        "WBC": [f"WBC {truth['WBC']} 10^9/L", f"WBC: {truth['WBC']}", f"WBC    {truth['WBC']}"],
        "HGB": [f"HGB {truth['HGB']:.0f} g/L", f"HGB: {truth['HGB']:.0f}", f"HGB    {truth['HGB']:.0f}"],
        "PLT": [f"PLT {truth['PLT']:.0f} 10^9/L", f"PLT: {truth['PLT']:.0f}", f"PLT    {truth['PLT']:.0f}"],
        "ALT": [f"ALT {truth['ALT']:.0f} U/L", f"ALT: {truth['ALT']:.0f}", f"ALT    {truth['ALT']:.0f}"],
        "AST": [f"AST {truth['AST']:.0f} U/L", f"AST: {truth['AST']:.0f}", f"AST    {truth['AST']:.0f}"],
        "GGT": [f"GGT {truth['GGT']:.0f} U/L", f"GGT: {truth['GGT']:.0f}", f"GGT    {truth['GGT']:.0f}"],
        "Glu": [f"GLU {truth['Glu']} mmol/L", f"Glu: {truth['Glu']}", f"GLU    {truth['Glu']}"],
        "TC": [f"TC {truth['TC']} mmol/L", f"TC: {truth['TC']}", f"TC    {truth['TC']}"],
        "TG": [f"TG {truth['TG']} mmol/L", f"TG: {truth['TG']}", f"TG    {truth['TG']}"],
        "UA": [f"UA {truth['UA']:.0f} umol/L", f"UA: {truth['UA']:.0f}", f"UA    {truth['UA']:.0f}"],
        "HbA1c": [f"HbA1c {truth['HbA1c']} %", f"糖化血红蛋白 {truth['HbA1c']} %"],
        "Creatinine": [f"Creatinine {truth['Creatinine']:.0f} umol/L", f"肌酐 {truth['Creatinine']:.0f} umol/L"],
        "eGFR": [f"eGFR {truth['eGFR']:.0f} ml/min/1.73m2"],
        "HDL": [f"HDL-C {truth['HDL']} mmol/L"],
        "LDL": [f"LDL-C {truth['LDL']} mmol/L"],
    }

    ordered_fields = [
        "BMI",
        "WBC",
        "HGB",
        "PLT",
        "ALT",
        "AST",
        "GGT",
        "Glu",
        "TC",
        "TG",
        "UA",
        "HbA1c",
        "Creatinine",
        "eGFR",
        "HDL",
        "LDL",
    ]
    for field in ordered_fields:
        if field in optional_drop:
            truth.pop(field, None)
            continue
        report_lines.append(rng.choice(metric_templates[field]))

    report_lines.extend(
        [
            "---- 医生提示 ----",
            "本报告为阶段3自动生成的合成样本，仅用于结构化抽取评估。",
            "No real patient information is included.",
        ]
    )
    return SyntheticReport(sample_id=sample_id, text="\n".join(report_lines) + "\n", raw_truth=truth)


def generate_samples(sample_dir: Path, count: int, seed: int) -> list[SyntheticReport]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    reports = [make_report(index, rng) for index in range(1, count + 1)]

    truth_payload = {
        "schema_version": "synthetic_ocr_eval_truth.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "sample_count": count,
        "samples": [],
    }
    for report in reports:
        (sample_dir / f"{report.sample_id}.txt").write_text(report.text, encoding="utf-8")
        truth_payload["samples"].append(
            {
                "sample_id": report.sample_id,
                "file_name": f"{report.sample_id}.txt",
                "raw_truth": report.raw_truth,
            }
        )
    (sample_dir / "ground_truth.json").write_text(
        json.dumps(truth_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return reports


def load_samples(sample_dir: Path) -> list[SyntheticReport]:
    truth_file = sample_dir / "ground_truth.json"
    payload = json.loads(truth_file.read_text(encoding="utf-8"))
    reports: list[SyntheticReport] = []
    for item in payload["samples"]:
        text = (sample_dir / item["file_name"]).read_text(encoding="utf-8")
        reports.append(
            SyntheticReport(
                sample_id=item["sample_id"],
                text=text,
                raw_truth={key: float(value) for key, value in item["raw_truth"].items()},
            )
        )
    return reports


def values_match(expected: float, actual: Any) -> bool:
    try:
        return abs(float(actual) - float(expected)) <= FIELD_TOLERANCE
    except (TypeError, ValueError):
        return False


def extract_predictions(service: MedicalOCRService, text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_prediction = service._extract_by_regex(text)
    normalized = normalize_ocr_summary_payload(raw_prediction) or {}
    canonical_prediction: dict[str, Any] = {}
    for key, metric in (normalized.get("metrics") or {}).items():
        if isinstance(metric, dict):
            canonical_prediction[key] = metric.get("value")
    return raw_prediction, canonical_prediction


def canonical_truth(raw_truth: dict[str, float]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key, value in raw_truth.items():
        canonical_key = CANONICAL_ALIAS.get(key, key)
        result[canonical_key] = value
    return result


def evaluate_reports(reports: list[SyntheticReport]) -> dict[str, Any]:
    service = MedicalOCRService()
    raw_field_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    canonical_field_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    sample_rows: list[dict[str, Any]] = []

    for report in reports:
        raw_prediction, canonical_prediction = extract_predictions(service, report.text)
        present_truth_fields = sorted(report.raw_truth.keys())
        supported_truth_fields = [field for field in present_truth_fields if field in SUPPORTED_RAW_FIELDS]
        canonical_expected = canonical_truth(report.raw_truth)

        raw_correct = 0
        for field in ALL_EVAL_FIELDS:
            expected_present = field in report.raw_truth
            predicted_present = field in raw_prediction
            if expected_present and predicted_present and values_match(report.raw_truth[field], raw_prediction[field]):
                raw_field_counts[field]["tp"] += 1
                raw_correct += 1
            elif expected_present:
                raw_field_counts[field]["fn"] += 1
            elif predicted_present:
                raw_field_counts[field]["fp"] += 1

        canonical_correct = 0
        for field, expected_value in canonical_expected.items():
            predicted_present = field in canonical_prediction
            if predicted_present and values_match(expected_value, canonical_prediction[field]):
                canonical_field_counts[field]["tp"] += 1
                canonical_correct += 1
            else:
                canonical_field_counts[field]["fn"] += 1
        for field in canonical_prediction:
            if field not in canonical_expected:
                canonical_field_counts[field]["fp"] += 1

        supported_correct = sum(
            1
            for field in supported_truth_fields
            if field in raw_prediction and values_match(report.raw_truth[field], raw_prediction[field])
        )
        sample_rows.append(
            {
                "sample_id": report.sample_id,
                "truth_field_count": len(present_truth_fields),
                "supported_truth_field_count": len(supported_truth_fields),
                "raw_predicted_field_count": len(raw_prediction),
                "raw_correct_field_count": raw_correct,
                "supported_correct_field_count": supported_correct,
                "canonical_predicted_field_count": len(canonical_prediction),
                "canonical_correct_field_count": canonical_correct,
                "raw_supported_recall": supported_correct / len(supported_truth_fields) if supported_truth_fields else 0,
                "raw_overall_recall": raw_correct / len(present_truth_fields) if present_truth_fields else 0,
                "full_supported_match": supported_correct == len(supported_truth_fields),
            }
        )

    return {
        "raw_field_metrics": summarize_counts(raw_field_counts),
        "canonical_field_metrics": summarize_counts(canonical_field_counts),
        "sample_rows": sample_rows,
    }


def summarize_counts(counts: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in sorted(counts):
        tp = counts[field].get("tp", 0)
        fp = counts[field].get("fp", 0)
        fn = counts[field].get("fn", 0)
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and (precision + recall)
            else None
        )
        rows.append(
            {
                "field": field,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": tp + fn,
            }
        )
    return rows


def micro_average(rows: list[dict[str, Any]], fields: set[str] | None = None) -> dict[str, Any]:
    selected = [row for row in rows if fields is None or row["field"] in fields]
    tp = sum(row["tp"] for row in selected)
    fp = sum(row["fp"] for row in selected)
    fn = sum(row["fn"] for row in selected)
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall)
        else None
    )
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return f"{float(value):.3f}"
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_report_markdown(
    *,
    reports: list[SyntheticReport],
    metrics: dict[str, Any],
    metadata: dict[str, Any],
    output_paths: dict[str, Path],
) -> str:
    raw_rows = metrics["raw_field_metrics"]
    canonical_rows = metrics["canonical_field_metrics"]
    sample_rows = metrics["sample_rows"]

    raw_supported = micro_average(raw_rows, set(SUPPORTED_RAW_FIELDS))
    raw_overall = micro_average(raw_rows, set(ALL_EVAL_FIELDS))
    canonical_overall = micro_average(canonical_rows)
    full_supported = sum(1 for row in sample_rows if row["full_supported_match"])
    avg_supported_recall = sum(row["raw_supported_recall"] for row in sample_rows) / len(sample_rows)
    avg_overall_recall = sum(row["raw_overall_recall"] for row in sample_rows) / len(sample_rows)

    def metric_table(rows: list[dict[str, Any]]) -> list[str]:
        lines = [
            "| Field | Support | TP | FP | FN | Precision | Recall | F1 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in rows:
            lines.append(
                f"| {row['field']} | {row['support']} | {row['tp']} | {row['fp']} | {row['fn']} | "
                f"{fmt(row['precision'])} | {fmt(row['recall'])} | {fmt(row['f1'])} |"
            )
        return lines

    return "\n".join(
        [
            "# OCR Structured Extraction Evaluation Report",
            "",
            f"- Generated at: {metadata['generated_at']}",
            f"- Sample type: `{metadata['sample_type']}`",
            f"- Sample count: `{len(reports)}`",
            f"- Evaluation path: `{metadata['evaluation_path']}`",
            f"- Field tolerance: `+/-{FIELD_TOLERANCE}`",
            "",
            "## Interpretation Boundary",
            "",
            "This phase uses 50 synthetic text reports as OCR-after-text fixtures. It measures deterministic structured extraction quality after OCR text is available.",
            "It does not measure Baidu OCR image/PDF recognition accuracy, scanner quality, layout recovery, or external clinical validity.",
            "The result is still useful for resume/thesis evidence because it quantifies the platform's report-to-structured-fields step with reproducible samples and ground truth.",
            "",
            "## Summary Metrics",
            "",
            f"- Raw regex supported-field micro precision: `{fmt(raw_supported['precision'])}`",
            f"- Raw regex supported-field micro recall: `{fmt(raw_supported['recall'])}`",
            f"- Raw regex supported-field micro F1: `{fmt(raw_supported['f1'])}`",
            f"- Raw regex all-field micro precision: `{fmt(raw_overall['precision'])}`",
            f"- Raw regex all-field micro recall: `{fmt(raw_overall['recall'])}`",
            f"- Raw regex all-field micro F1: `{fmt(raw_overall['f1'])}`",
            f"- Canonical `ocr_summary.v1` micro precision: `{fmt(canonical_overall['precision'])}`",
            f"- Canonical `ocr_summary.v1` micro recall: `{fmt(canonical_overall['recall'])}`",
            f"- Canonical `ocr_summary.v1` micro F1: `{fmt(canonical_overall['f1'])}`",
            f"- Documents with all supported raw fields matched: `{full_supported}/{len(sample_rows)}`",
            f"- Average document supported-field recall: `{fmt(avg_supported_recall)}`",
            f"- Average document all-field recall: `{fmt(avg_overall_recall)}`",
            "",
            "## Raw Regex Field Metrics",
            "",
            *metric_table(raw_rows),
            "",
            "## Canonical OCR Summary Metrics",
            "",
            *metric_table(canonical_rows),
            "",
            "## Known Gaps Found By This Phase",
            "",
            "- AST, HGB, and UA are now included in canonical `ocr_summary.v1.metrics` after the approved report-level biomarker contract extension.",
            "- Real image/PDF OCR recognition quality still needs a provider-backed, de-identified report benchmark; this phase only measures post-OCR text extraction.",
            "",
            "## Output Files",
            "",
            f"- Synthetic samples: `{output_paths['sample_dir']}`",
            f"- Ground truth: `{output_paths['truth']}`",
            f"- Raw field metrics: `{output_paths['raw_csv']}`",
            f"- Canonical field metrics: `{output_paths['canonical_csv']}`",
            f"- Per-sample metrics: `{output_paths['sample_csv']}`",
            f"- JSON summary: `{output_paths['json']}`",
            f"- Markdown report: `{output_paths['markdown']}`",
            "",
            "## Suggested Resume Wording",
            "",
            f"- 可表述为：`构建 50 份合成体检报告样本及标准答案，完成 OCR 后文本结构化抽取评估；当前规则抽取链路在已覆盖字段上的 micro-F1 为 {fmt(raw_supported['f1'])}，并形成字段级误差分析，为后续 OCR/LLM 抽取优化提供依据。`",
            "- 不建议表述为：`真实 OCR 图片识别准确率` 或 `医院真实报告识别率`，除非后续补充真实脱敏报告和 OCR Provider 识别评测。",
            "",
            "## Phase Handoff",
            "",
            "- Current stage: Phase 3 - OCR structured extraction evaluation",
            "- Updated artifacts: `ai_core/evaluate_ocr_extraction.py`, `docs/evaluation/ocr-samples/*`, `docs/evaluation/ocr-*.csv`, `docs/evaluation/ocr-extraction-summary.json`, `docs/evaluation/ocr-evaluation-report.md`",
            "- Blockers: none for synthetic post-OCR extraction evaluation; real image/PDF OCR accuracy remains blocked on provider credentials and real de-identified reports.",
            "- Next stage: Phase 4 - RAG retrieval evaluation.",
        ]
    ) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-dir", type=Path, default=DEFAULT_SAMPLE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260424)
    parser.add_argument(
        "--use-existing-samples",
        action="store_true",
        help="Load existing samples instead of regenerating deterministic synthetic samples.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.use_existing_samples:
        reports = load_samples(args.sample_dir)
    else:
        reports = generate_samples(args.sample_dir, args.sample_count, args.seed)

    metrics = evaluate_reports(reports)
    raw_csv = args.output_dir / "ocr-raw-field-metrics.csv"
    canonical_csv = args.output_dir / "ocr-canonical-field-metrics.csv"
    sample_csv = args.output_dir / "ocr-sample-metrics.csv"
    json_path = args.output_dir / "ocr-extraction-summary.json"
    markdown_path = args.output_dir / "ocr-evaluation-report.md"
    truth_path = args.sample_dir / "ground_truth.json"

    write_csv(raw_csv, metrics["raw_field_metrics"])
    write_csv(canonical_csv, metrics["canonical_field_metrics"])
    write_csv(sample_csv, metrics["sample_rows"])

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sample_type": "synthetic_post_ocr_text_reports",
        "evaluation_path": "MedicalOCRService._extract_by_regex -> normalize_ocr_summary_payload",
        "sample_count": len(reports),
        "seed": args.seed,
    }
    summary = {"metadata": metadata, "metrics": metrics}
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report = make_report_markdown(
        reports=reports,
        metrics=metrics,
        metadata=metadata,
        output_paths={
            "sample_dir": args.sample_dir,
            "truth": truth_path,
            "raw_csv": raw_csv,
            "canonical_csv": canonical_csv,
            "sample_csv": sample_csv,
            "json": json_path,
            "markdown": markdown_path,
        },
    )
    markdown_path.write_text(report, encoding="utf-8")

    raw_supported = micro_average(metrics["raw_field_metrics"], set(SUPPORTED_RAW_FIELDS))
    raw_overall = micro_average(metrics["raw_field_metrics"], set(ALL_EVAL_FIELDS))
    print(f"Generated/evaluated {len(reports)} synthetic OCR text reports.")
    print(f"Raw supported-field F1: {fmt(raw_supported['f1'])}")
    print(f"Raw all-field F1: {fmt(raw_overall['f1'])}")
    print(f"Wrote {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
