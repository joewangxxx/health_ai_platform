"""Compatibility and reproducibility checks for model runtime assets.

Usage:
    python ai_core/check_model_compatibility.py
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as md
import warnings
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models"

PACKAGE_KEYS = [
    "xgboost",
    "torch",
    "torchvision",
    "scikit-learn",
    "joblib",
]

JOBLIB_ARTIFACTS = {
    "risk_assessment_models": MODELS_DIR / "risk_assessment_models.pkl",
    "lifestyle_xgb_model": MODELS_DIR / "lifestyle_xgb_model.pkl",
    "feature_scaler": MODELS_DIR / "feature_scaler.pkl",
}

TORCH_ARTIFACTS = {
    "nutrition_efficientnet": MODELS_DIR / "nutrition_efficientnet.pth",
    "food_resnet": MODELS_DIR / "food_resnet_model.pth",
    "glucose_lstm": MODELS_DIR / "glucose_lstm_model.pth",
}


def _package_versions() -> Dict[str, str]:
    versions: Dict[str, str] = {}
    for key in PACKAGE_KEYS:
        try:
            versions[key] = md.version(key)
        except md.PackageNotFoundError:
            versions[key] = "NOT_INSTALLED"
    return versions


def _check_joblib_artifacts() -> List[str]:
    issues: List[str] = []
    try:
        import joblib  # type: ignore
    except Exception as exc:  # pragma: no cover - env dependent
        return [f"BLOCKER: joblib import failed: {exc}"]

    for label, path in JOBLIB_ARTIFACTS.items():
        if not path.exists():
            issues.append(f"BLOCKER: missing artifact: {path}")
            continue

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                joblib.load(path)
            except Exception as exc:
                issues.append(f"BLOCKER: {label} load failed: {exc}")
                continue

        seen_warnings = set()
        for item in caught:
            name = item.category.__name__
            if name == "InconsistentVersionWarning":
                key = (name, str(item.message))
                if key in seen_warnings:
                    continue
                seen_warnings.add(key)
                issues.append(f"WARN: {label} emitted {name}: {item.message}")

    return issues


def _check_torch_artifacts() -> List[str]:
    issues: List[str] = []
    try:
        torch = importlib.import_module("torch")
    except Exception:
        return ["BLOCKER: torch not installed; cannot validate .pth model readability."]

    for label, path in TORCH_ARTIFACTS.items():
        if not path.exists():
            issues.append(f"BLOCKER: missing artifact: {path}")
            continue
        try:
            torch.load(path, map_location="cpu")
        except Exception as exc:
            issues.append(f"BLOCKER: {label} torch.load failed: {exc}")
    return issues


def _print_report(strict: bool) -> int:
    versions = _package_versions()
    print("=== package versions ===")
    for key in PACKAGE_KEYS:
        print(f"{key}=={versions[key]}")

    issues: List[str] = []
    issues.extend(_check_joblib_artifacts())
    issues.extend(_check_torch_artifacts())

    print("\n=== compatibility checks ===")
    if not issues:
        print("OK: no compatibility issues detected.")
        return 0

    for issue in issues:
        print(issue)

    has_blocker = any(line.startswith("BLOCKER:") for line in issues)
    if strict and has_blocker:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate model dependency compatibility.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when blocker-level issues are detected.",
    )
    args = parser.parse_args()
    return _print_report(strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
