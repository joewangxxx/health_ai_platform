"""Evaluate persisted LightGBM risk models on a deterministic NHANES holdout.

This script is intentionally read-only for model assets. It loads the existing
model bundle, replays the repository training feature assembly, and writes
evaluation artifacts under docs/evaluation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from backend.config import DATA_WAREHOUSE_DIR, MODELS_DIR, PROJECT_ROOT


DEFAULT_DATA_FILE = (
    Path(DATA_WAREHOUSE_DIR)
    / "processed_data"
    / "clinical_clean"
    / "nhanes_integrated_data_v2.csv"
)
DEFAULT_MODEL_FILE = Path(MODELS_DIR) / "risk_assessment_models.pkl"
DEFAULT_OUTPUT_DIR = Path(PROJECT_ROOT) / "docs" / "evaluation"
RAW_NHANES_DIR = Path(DATA_WAREHOUSE_DIR) / "raw_data" / "NHANES"

DIET_FEATURES = [
    "DR1TKCAL",
    "DR1TPROT",
    "DR1TCARB",
    "DR1TSUGR",
    "DR1TFIBE",
    "DR1TSODI",
    "DR1TFAT",
    "DR1TSFAT",
    "DR1TCHOL",
    "DR1TCAFF",
    "DR1TALCO",
]
MICRONUTRIENT_FEATURES = ["LBXVIDMS", "LBXRBCF", "LBXB12"]
NUTRITION_FILES = {
    "DIET_DAY1": "P_DR1TOT.xpt",
    "DIET_DAY2": "P_DR2TOT.xpt",
    "VITD": "P_VID.xpt",
    "FOLATE": "P_FOLATE.xpt",
}

SUMMARY_ORDER = [
    "T2D",
    "Hypertension",
    "HighLipid",
    "Obesity",
    "CKD",
    "CVD",
    "Stroke",
    "CoronaryHeart",
    "Depression",
]


def clean_column_name(column_name: object) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(column_name))


def load_nhanes_nutrition_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Replay the nutrition merge used by the training script."""
    if "SEQN" not in df.columns:
        return df, ["Skipped NHANES nutrition merge because SEQN is absent."]

    merged = df.copy()
    notes: list[str] = []

    for name, filename in NUTRITION_FILES.items():
        path = RAW_NHANES_DIR / filename
        if not path.exists():
            notes.append(f"{name}: missing source file {path}")
            continue

        try:
            xpt_df = pd.read_sas(path, format="xport", encoding="utf-8")
        except Exception as exc:  # pragma: no cover - environment-dependent I/O
            notes.append(f"{name}: failed to read {filename}: {exc}")
            continue

        xpt_df.columns = [clean_column_name(column) for column in xpt_df.columns]
        if name.startswith("DIET"):
            candidate_columns = ["SEQN"] + [c for c in DIET_FEATURES if c in xpt_df.columns]
        else:
            candidate_columns = ["SEQN"] + [
                c for c in MICRONUTRIENT_FEATURES if c in xpt_df.columns
            ]

        available_columns = [c for c in candidate_columns if c in xpt_df.columns]
        if len(available_columns) <= 1:
            notes.append(f"{name}: no usable feature columns in {filename}")
            continue

        before_columns = set(merged.columns)
        merged = merged.merge(
            xpt_df[available_columns].copy(),
            on="SEQN",
            how="left",
            suffixes=("", f"_{name}"),
        )
        added = sorted(set(merged.columns) - before_columns)
        notes.append(f"{name}: merged {len(added)} new columns from {filename}")

    return merged, notes


def load_eval_dataframe(data_file: Path, include_nutrition: bool) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_csv(data_file)
    df = df.rename(columns=lambda column: clean_column_name(column))

    notes = [f"Loaded {len(df)} rows and {len(df.columns)} columns from {data_file}."]
    if include_nutrition:
        df, nutrition_notes = load_nhanes_nutrition_data(df)
        notes.extend(nutrition_notes)
    return df, notes


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return None
    return float(value)


def evaluate_one_model(
    disease: str,
    model: Any,
    features: list[str],
    df: pd.DataFrame,
    test_size: float,
    random_state: int,
    threshold: float,
) -> dict[str, Any]:
    target_column = f"Target_{disease}"
    if target_column not in df.columns:
        return {
            "disease": disease,
            "status": "skipped",
            "skip_reason": f"Missing target column: {target_column}",
        }

    y = df[target_column].fillna(0).astype(int)
    if y.nunique() < 2:
        return {
            "disease": disease,
            "status": "skipped",
            "skip_reason": "Target has only one class after fillna(0).",
            "n_total": int(len(y)),
            "positive_total": int(y.sum()),
        }

    eval_df = df.copy()
    missing_features = [feature for feature in features if feature not in eval_df.columns]
    for feature in missing_features:
        eval_df[feature] = np.nan

    X = eval_df[features]
    _, X_test, _, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    y_score = model.predict_proba(X_test)[:, 1]
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()

    result = {
        "disease": disease,
        "status": "evaluated",
        "n_total": int(len(y)),
        "n_test": int(len(y_test)),
        "positive_total": int(y.sum()),
        "positive_test": int(y_test.sum()),
        "prevalence_total": safe_float(y.mean()),
        "prevalence_test": safe_float(y_test.mean()),
        "feature_count": int(len(features)),
        "missing_feature_count": int(len(missing_features)),
        "missing_features": ";".join(missing_features),
        "threshold": threshold,
        "roc_auc": safe_float(roc_auc_score(y_test, y_score)),
        "pr_auc": safe_float(average_precision_score(y_test, y_score)),
        "accuracy": safe_float(accuracy_score(y_test, y_pred)),
        "balanced_accuracy": safe_float(balanced_accuracy_score(y_test, y_pred)),
        "precision": safe_float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": safe_float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": safe_float(f1_score(y_test, y_pred, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
    result["specificity"] = safe_float(tn / (tn + fp)) if (tn + fp) else None
    return result


def fmt(value: Any, digits: int = 3) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, str):
        return value
    return f"{float(value):.{digits}f}"


def make_markdown_report(
    results: list[dict[str, Any]],
    metadata: dict[str, Any],
    output_paths: dict[str, Path],
) -> str:
    evaluated = [row for row in results if row.get("status") == "evaluated"]
    skipped = [row for row in results if row.get("status") != "evaluated"]
    sorted_by_auc = sorted(evaluated, key=lambda row: row.get("roc_auc") or 0, reverse=True)
    summary_rows = [
        row for disease in SUMMARY_ORDER for row in evaluated if row["disease"] == disease
    ]

    def table(rows: list[dict[str, Any]]) -> list[str]:
        lines = [
            "| Disease | Test N | Positives | ROC-AUC | PR-AUC | Accuracy | Balanced Acc | Precision | Recall | F1 | Missing Features |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        row["disease"],
                        str(row["n_test"]),
                        str(row["positive_test"]),
                        fmt(row["roc_auc"]),
                        fmt(row["pr_auc"]),
                        fmt(row["accuracy"]),
                        fmt(row["balanced_accuracy"]),
                        fmt(row["precision"]),
                        fmt(row["recall"]),
                        fmt(row["f1"]),
                        str(row["missing_feature_count"]),
                    ]
                )
                + " |"
            )
        return lines

    best_auc = max((row.get("roc_auc") or 0 for row in evaluated), default=0)
    median_auc = float(np.median([row["roc_auc"] for row in evaluated])) if evaluated else 0
    low_missing = sum(1 for row in evaluated if row.get("missing_feature_count", 0) == 0)

    lines = [
        "# Risk Model Offline Evaluation Report",
        "",
        f"- Generated at: {metadata['generated_at']}",
        f"- Model bundle: `{metadata['model_file']}`",
        f"- Evaluation data: `{metadata['data_file']}`",
        f"- Evaluation mode: `{metadata['evaluation_mode']}`",
        f"- Split: `test_size={metadata['test_size']}`, `random_state={metadata['random_state']}`, stratified by target",
        f"- Decision threshold: `{metadata['threshold']}`",
        f"- Evaluated models: `{len(evaluated)}`",
        f"- Skipped models: `{len(skipped)}`",
        f"- Best ROC-AUC: `{best_auc:.3f}`",
        f"- Median ROC-AUC: `{median_auc:.3f}`",
        f"- Models with complete replay features: `{low_missing}/{len(evaluated)}`",
        "",
        "## Interpretation Boundary",
        "",
        "These numbers are suitable as repository-local offline evaluation evidence, but they should not be described as external clinical validation.",
        "The persisted model bundle does not store the exact original training indices, so this script replays a deterministic stratified split against the current data and evaluates the persisted artifacts on that split.",
        "If the persisted artifacts were trained on the full dataset or an overlapping split, the metrics may be optimistic. For thesis-grade claims, follow this phase with a fresh train/validation/test rerun that saves split IDs.",
        "",
        "## Data Assembly Notes",
        "",
    ]

    lines.extend(f"- {note}" for note in metadata["data_notes"])
    lines.extend(
        [
            "",
            "## Core Resume-Relevant Models",
            "",
            *table(summary_rows),
            "",
            "## Top Models By ROC-AUC",
            "",
            *table(sorted_by_auc[:12]),
            "",
            "## All Evaluated Models",
            "",
            *table(sorted(evaluated, key=lambda row: row["disease"])),
        ]
    )

    if skipped:
        lines.extend(["", "## Skipped Models", "", "| Disease | Reason |", "|---|---|"])
        for row in skipped:
            lines.append(f"| {row['disease']} | {row.get('skip_reason', '-')} |")

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- CSV metrics: `{output_paths['csv']}`",
            f"- JSON metrics: `{output_paths['json']}`",
            f"- Markdown report: `{output_paths['markdown']}`",
            "",
            "## Suggested Resume Wording",
            "",
            f"- 可表述为：`完成 LightGBM 慢病风险模型离线评估，覆盖 {len(evaluated)} 个疾病/风险标签，固定分层回放测试集 ROC-AUC 中位数 {median_auc:.3f}，核心标签如 T2D/高血压/血脂异常/肥胖等形成可复现实验记录。`",
            "- 不建议表述为：`达到临床诊断准确率`、`已完成真实世界临床验证` 或 `外部验证集准确率`，除非后续补充独立外部数据集。",
            "",
            "## Phase Handoff",
            "",
            "- Current stage: Phase 2 - risk-model offline evaluation",
            "- Updated artifacts: `ai_core/evaluate_risk_models.py`, `docs/evaluation/risk-model-metrics.csv`, `docs/evaluation/risk-model-metrics.json`, `docs/evaluation/model-evaluation-report.md`",
            "- Blockers: none for repository-local offline evaluation; external clinical validation remains out of scope.",
            "- Next stage: Phase 3 - OCR structured extraction evaluation.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-file", type=Path, default=DEFAULT_DATA_FILE)
    parser.add_argument("--model-file", type=Path, default=DEFAULT_MODEL_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--skip-nutrition-merge",
        action="store_true",
        help="Do not replay the NHANES nutrition XPT merge from training.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle = joblib.load(args.model_file)
    models = bundle.get("models", {})
    features_map = bundle.get("features_map", {})
    df, data_notes = load_eval_dataframe(
        args.data_file, include_nutrition=not args.skip_nutrition_merge
    )

    results = [
        evaluate_one_model(
            disease=disease,
            model=model,
            features=list(features_map.get(disease, [])),
            df=df,
            test_size=args.test_size,
            random_state=args.random_state,
            threshold=args.threshold,
        )
        for disease, model in models.items()
    ]

    csv_path = output_dir / "risk-model-metrics.csv"
    json_path = output_dir / "risk-model-metrics.json"
    report_path = output_dir / "model-evaluation-report.md"

    pd.DataFrame(results).to_csv(csv_path, index=False, encoding="utf-8")

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_mode": "persisted_artifact_stratified_holdout_replay",
        "model_file": str(args.model_file),
        "data_file": str(args.data_file),
        "test_size": args.test_size,
        "random_state": args.random_state,
        "threshold": args.threshold,
        "data_notes": data_notes,
    }
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump({"metadata": metadata, "results": results}, fh, ensure_ascii=False, indent=2)

    report = make_markdown_report(
        results,
        metadata,
        {"csv": csv_path, "json": json_path, "markdown": report_path},
    )
    report_path.write_text(report, encoding="utf-8")

    evaluated_count = sum(1 for row in results if row.get("status") == "evaluated")
    print(f"Evaluated {evaluated_count}/{len(results)} persisted risk models.")
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
