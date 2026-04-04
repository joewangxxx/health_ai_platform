import logging
import warnings
from typing import Any, Optional

import joblib

logger = logging.getLogger(__name__)

try:
    from sklearn.exceptions import InconsistentVersionWarning
except Exception:  # pragma: no cover - sklearn may not expose this symbol
    InconsistentVersionWarning = None


def _build_warning_filters() -> None:
    if InconsistentVersionWarning is not None:
        warnings.simplefilter("error", InconsistentVersionWarning)


def load_joblib_artifact(
    path: str,
    *,
    component_label: str,
    failure_message: str,
    log: Optional[logging.Logger] = None,
) -> Any | None:
    active_logger = log or logger
    try:
        with warnings.catch_warnings():
            _build_warning_filters()
            return joblib.load(path)
    except Exception as exc:
        active_logger.warning("%s (%s).", failure_message, exc)
        return None
