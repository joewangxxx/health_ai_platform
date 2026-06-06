"""Re-export persisted joblib artifacts against the current runtime baseline.

Usage:
    python ai_core/reexport_joblib_artifacts.py
    python ai_core/reexport_joblib_artifacts.py --artifacts risk_assessment_models feature_scaler
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, Tuple

import joblib


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models"

JOBLIB_ARTIFACTS: Dict[str, Path] = {
    "risk_assessment_models": MODELS_DIR / "risk_assessment_models.pkl",
    "lifestyle_xgb_model": MODELS_DIR / "lifestyle_xgb_model.pkl",
    "feature_scaler": MODELS_DIR / "feature_scaler.pkl",
}


def _reexport_one(label: str, path: Path) -> Tuple[bool, str]:
    if not path.exists():
        return False, f"missing artifact: {path}"

    payload = joblib.load(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(payload, tmp_path)
    tmp_path.replace(path)
    return True, f"re-exported: {label} -> {path}"


def _iter_selected(selected: Iterable[str]) -> Iterable[Tuple[str, Path]]:
    for label in selected:
        yield label, JOBLIB_ARTIFACTS[label]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-export existing joblib artifacts without changing model semantics."
    )
    parser.add_argument(
        "--artifacts",
        nargs="+",
        choices=sorted(JOBLIB_ARTIFACTS.keys()),
        default=sorted(JOBLIB_ARTIFACTS.keys()),
        help="Artifact labels to re-export. Defaults to all known joblib artifacts.",
    )
    args = parser.parse_args()

    failures = 0
    for label, path in _iter_selected(args.artifacts):
        try:
            ok, message = _reexport_one(label, path)
        except Exception as exc:  # pragma: no cover - environment dependent
            ok, message = False, f"failed: {label}: {exc}"

        print(message)
        if not ok:
            failures += 1

    if failures:
        print(f"done with failures={failures}")
        return 1

    print("done with failures=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
