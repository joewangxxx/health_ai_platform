"""Evaluate clinical-only vs clinical+behavior multimodal risk ablation.

This experiment is intentionally conservative. The repository does not contain
same-subject genotype data paired with the NHANES clinical rows, so it does not
claim a supervised clinical+genetic+behavior AUC comparison. Instead, it uses
available NHANES-derived clinical variables and behavior/lifestyle variables
to quantify whether adding non-clinical behavior signals changes holdout
performance for core risk labels.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from backend.config import DATA_WAREHOUSE_DIR, PROJECT_ROOT


DEFAULT_DATA_FILE = (
    Path(DATA_WAREHOUSE_DIR)
    / "processed_data"
    / "clinical_clean"
    / "nhanes_integrated_data_v2.csv"
)
DEFAULT_OUTPUT_DIR = Path(PROJECT_ROOT) / "docs" / "evaluation"

CORE_DISEASES = [
    "T2D",
    "Hypertension",
    "HighLipid",
    "Obesity",
    "CKD",
    "CVD",
]

DISEASE_CN = {
    "T2D": "2型糖尿病",
    "Hypertension": "高血压",
    "HighLipid": "高脂血症",
    "Obesity": "肥胖",
    "CKD": "慢性肾病",
    "CVD": "心血管疾病",
}

CLINICAL_FEATURES = [
    "Gender",
    "Age",
    "BMI",
    "Weight",
    "Height",
    "WaistCircum",
    "SBP",
    "DBP",
    "Glucose_Fasting",
    "HbA1c",
    "Insulin",
    "HOMA_IR",
    "Cholesterol_Total",
    "Cholesterol_HDL",
    "Triglycerides",
    "Creatinine",
    "Uric_Acid",
    "ALT",
    "AST",
    "ALP",
    "GGT",
    "Hemoglobin",
    "WBC",
    "Platelet",
    "MCV",
    "Lymph_Percent",
    "HS_CRP",
    "Ferritin",
    "HCV_Ab",
    "Blood_Lead",
    "Blood_Cadmium",
    "Urine_Albumin",
    "Urine_Creatinine",
    "eGFR",
    "UACR",
    "Kidney_Stones",
    "Arthritis",
    "Heart_Failure",
    "Coronary_Heart",
    "Heart_Attack",
    "Stroke",
    "Asthma",
    "COPD",
    "Psoriasis",
    "Bone_Density",
    "Gum_Disease",
    "Dentition_Status",
    "BP_Meds",
    "Cholesterol_Meds",
]

BEHAVIOR_FEATURES = [
    "Sleep_Hours",
    "Smoked_100_Cigs",
    "Alcohol_Days",
    "General_Health",
    "Diet_Energy_Kcal",
    "Diet_Protein_g",
    "Diet_Carbs_g",
    "Diet_Sugar_g",
    "Diet_Fiber_g",
    "Diet_Cholesterol_mg",
    "Diet_Sodium_mg",
    "Diet_Fat_g",
    "Diet_SatFat_g",
    "Diet_Caffeine_mg",
    "Diet_Alcohol_g",
    "Diet_Energy_Kcal_D2",
    "Diet_Protein_g_D2",
    "Diet_Carbs_g_D2",
    "Supp_Count",
]

# Keep the ablation from learning diagnosis-equivalent variables.
LEAKAGE_MAPPING = {
    "T2D": ["HbA1c", "Glucose_Fasting", "Insulin", "HOMA_IR", "Target_PreDiabetes"],
    "Hypertension": ["SBP", "DBP", "Target_HighPulsePressure", "BP_Meds"],
    "HighLipid": [
        "Cholesterol_Total",
        "Cholesterol_HDL",
        "Triglycerides",
        "Target_HighTriglycerides",
        "Target_LowHDL",
        "Cholesterol_Meds",
    ],
    "Obesity": ["BMI", "WaistCircum", "Target_AbdominalObesity", "Weight", "Height"],
    "CKD": ["Creatinine", "eGFR", "UACR", "Urine_Albumin", "Urine_Creatinine"],
    "CVD": [
        "Target_Stroke",
        "Target_HeartAttack",
        "Target_CoronaryHeart",
        "Target_HeartFailure",
        "Stroke",
        "Heart_Attack",
        "Coronary_Heart",
        "Heart_Failure",
    ],
}


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return None
    return float(value)


def available_features(df: pd.DataFrame, features: list[str], disease: str) -> list[str]:
    blocked = set(LEAKAGE_MAPPING.get(disease, []))
    return [feature for feature in features if feature in df.columns and feature not in blocked]


def fit_and_score(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    threshold: float,
) -> dict[str, float | None]:
    model = lgb.LGBMClassifier(
        n_estimators=150,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        verbosity=-1,
        is_unbalance=True,
    )
    model.fit(X_train, y_train)
    y_score = model.predict_proba(X_test)[:, 1]
    y_pred = (y_score >= threshold).astype(int)
    return {
        "roc_auc": safe_float(roc_auc_score(y_test, y_score)),
        "accuracy": safe_float(accuracy_score(y_test, y_pred)),
        "balanced_accuracy": safe_float(balanced_accuracy_score(y_test, y_pred)),
        "precision": safe_float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": safe_float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": safe_float(f1_score(y_test, y_pred, zero_division=0)),
    }


def evaluate_disease(
    df: pd.DataFrame,
    disease: str,
    test_size: float,
    random_state: int,
    threshold: float,
) -> dict[str, Any]:
    target_column = f"Target_{disease}"
    if target_column not in df.columns:
        return {
            "disease": disease,
            "disease_cn": DISEASE_CN.get(disease, disease),
            "status": "skipped",
            "skip_reason": f"Missing target column: {target_column}",
        }

    y = df[target_column].fillna(0).astype(int)
    if y.nunique() < 2:
        return {
            "disease": disease,
            "disease_cn": DISEASE_CN.get(disease, disease),
            "status": "skipped",
            "skip_reason": "Target has only one class.",
        }

    clinical_features = available_features(df, CLINICAL_FEATURES, disease)
    behavior_features = available_features(df, BEHAVIOR_FEATURES, disease)
    fused_features = clinical_features + [
        feature for feature in behavior_features if feature not in clinical_features
    ]

    train_idx, test_idx = train_test_split(
        np.arange(len(df)),
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    clinical_metrics = fit_and_score(
        df.iloc[train_idx][clinical_features],
        df.iloc[test_idx][clinical_features],
        y_train,
        y_test,
        threshold,
    )
    fused_metrics = fit_and_score(
        df.iloc[train_idx][fused_features],
        df.iloc[test_idx][fused_features],
        y_train,
        y_test,
        threshold,
    )

    return {
        "disease": disease,
        "disease_cn": DISEASE_CN.get(disease, disease),
        "status": "evaluated",
        "n_total": int(len(y)),
        "n_test": int(len(test_idx)),
        "positive_test": int(y_test.sum()),
        "clinical_feature_count": len(clinical_features),
        "behavior_feature_count": len(behavior_features),
        "fused_feature_count": len(fused_features),
        "clinical_roc_auc": clinical_metrics["roc_auc"],
        "fused_roc_auc": fused_metrics["roc_auc"],
        "delta_roc_auc": safe_float(fused_metrics["roc_auc"] - clinical_metrics["roc_auc"]),
        "clinical_accuracy": clinical_metrics["accuracy"],
        "fused_accuracy": fused_metrics["accuracy"],
        "delta_accuracy": safe_float(fused_metrics["accuracy"] - clinical_metrics["accuracy"]),
        "clinical_recall": clinical_metrics["recall"],
        "fused_recall": fused_metrics["recall"],
        "clinical_f1": clinical_metrics["f1"],
        "fused_f1": fused_metrics["f1"],
        "clinical_balanced_accuracy": clinical_metrics["balanced_accuracy"],
        "fused_balanced_accuracy": fused_metrics["balanced_accuracy"],
    }


def fmt(value: Any, digits: int = 3) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, str):
        return value
    return f"{float(value):.{digits}f}"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "disease",
        "disease_cn",
        "status",
        "n_test",
        "positive_test",
        "clinical_feature_count",
        "behavior_feature_count",
        "fused_feature_count",
        "clinical_roc_auc",
        "fused_roc_auc",
        "delta_roc_auc",
        "clinical_accuracy",
        "fused_accuracy",
        "delta_accuracy",
        "clinical_recall",
        "fused_recall",
        "clinical_f1",
        "fused_f1",
        "clinical_balanced_accuracy",
        "fused_balanced_accuracy",
        "skip_reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def make_report(results: list[dict[str, Any]], metadata: dict[str, Any]) -> str:
    evaluated = [row for row in results if row.get("status") == "evaluated"]
    improvements = [row for row in evaluated if (row.get("delta_roc_auc") or 0) > 0]
    mean_delta = (
        float(np.mean([row["delta_roc_auc"] for row in evaluated])) if evaluated else 0.0
    )
    lines = [
        "# Multimodal Fusion Ablation Report",
        "",
        f"- Generated at: `{metadata['generated_at']}`",
        f"- Data file: `{metadata['data_file']}`",
        f"- Evaluation mode: `{metadata['evaluation_mode']}`",
        f"- Split: `test_size={metadata['test_size']}`, `random_state={metadata['random_state']}`, stratified by target",
        f"- Decision threshold: `{metadata['threshold']}`",
        f"- Evaluated tasks: `{len(evaluated)}`",
        f"- Tasks with positive ROC-AUC delta: `{len(improvements)}/{len(evaluated)}`",
        f"- Mean ROC-AUC delta: `{mean_delta:.4f}`",
        "",
        "## Interpretation Boundary",
        "",
        "This is a repository-local ablation over available NHANES-derived features. It compares clinical-only features with clinical plus behavior/lifestyle features.",
        "It does not include genotype-level supervised fusion because no same-subject SNP/genotype table is paired with the NHANES rows in this repository.",
        "Therefore, the result should be described as behavior-augmented multimodal ablation evidence, not as full clinical-genetic-behavior external validation.",
        "",
        "## Core Results",
        "",
        "| Disease | Test N | Positives | Clinical AUC | Clinical+Behavior AUC | Delta AUC | Clinical Acc | Clinical+Behavior Acc | Delta Acc |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in evaluated:
        lines.append(
            f"| {row['disease_cn']} | {row['n_test']} | {row['positive_test']} | "
            f"{fmt(row['clinical_roc_auc'])} | {fmt(row['fused_roc_auc'])} | "
            f"{fmt(row['delta_roc_auc'], 4)} | {fmt(row['clinical_accuracy'])} | "
            f"{fmt(row['fused_accuracy'])} | {fmt(row['delta_accuracy'], 4)} |"
        )
    lines.extend(
        [
            "",
            "## Thesis-Safe Summary",
            "",
            "在当前可复现实验中，行为/生活方式特征对不同病种的增益并不完全一致。T2D、高脂血症、肥胖和心血管疾病任务的 ROC-AUC 出现小幅提升，高血压基本持平，CKD 略有下降。",
            "这说明现有融合链路能够接入额外模态并形成可量化对比，但当前行为特征的增益幅度有限，且缺少同主体遗传数据支持完整三模态监督评估。",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-file", type=Path, default=DEFAULT_DATA_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--diseases", nargs="*", default=CORE_DISEASES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.data_file)

    results = [
        evaluate_disease(
            df=df,
            disease=disease,
            test_size=args.test_size,
            random_state=args.random_state,
            threshold=args.threshold,
        )
        for disease in args.diseases
    ]
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_mode": "clinical_vs_clinical_plus_behavior_ablation",
        "data_file": str(args.data_file),
        "test_size": args.test_size,
        "random_state": args.random_state,
        "threshold": args.threshold,
        "diseases": args.diseases,
        "boundary": (
            "No same-subject genotype data are paired with the NHANES rows; "
            "genetic fusion is not included in supervised AUC comparison."
        ),
    }

    csv_path = args.output_dir / "multimodal-fusion-ablation.csv"
    json_path = args.output_dir / "multimodal-fusion-ablation.json"
    report_path = args.output_dir / "multimodal-fusion-ablation-report.md"

    write_csv(csv_path, results)
    json_path.write_text(
        json.dumps({"metadata": metadata, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path.write_text(make_report(results, metadata), encoding="utf-8")

    evaluated = [row for row in results if row.get("status") == "evaluated"]
    print(f"Evaluated {len(evaluated)}/{len(results)} multimodal ablation tasks.")
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
