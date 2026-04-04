"""
[V2 LEGACY COMPONENT]
This module is retained for backward compatibility with V3 routes.
Do not delete until a V3 replacement is fully implemented.
"""

import logging
import os
import warnings

import joblib
import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover - depends on local environment
    torch = None
    nn = None
    TORCH_AVAILABLE = False

from backend.config import FEATURE_SCALER_PATH, GLUCOSE_MODEL_PATH
from backend.core.constants import THRESHOLD_HEART_STRESS

logger = logging.getLogger(__name__)
_runtime_warning_emitted = False

MODEL_PATH = GLUCOSE_MODEL_PATH
SCALER_PATH = FEATURE_SCALER_PATH

INPUT_SIZE = 11
HIDDEN_SIZE = 64
NUM_LAYERS = 2


def _emit_runtime_unavailable_warning():
    global _runtime_warning_emitted
    if _runtime_warning_emitted:
        return
    logger.warning("Glucose predictor unavailable; continuing without torch runtime.")
    _runtime_warning_emitted = True


if TORCH_AVAILABLE:
    class GlucoseLSTM(nn.Module):
        def __init__(self, input_size, hidden_size, num_layers, output_size=1):
            super().__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
            self.fc = nn.Linear(hidden_size, output_size)

        def forward(self, x):
            h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
            c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
            out, _ = self.lstm(x, (h0, c0))
            out = out[:, -1, :]
            return self.fc(out)
else:
    class GlucoseLSTM:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("torch runtime unavailable")


class Predictor:
    def __init__(self):
        self.device = torch.device("cpu") if TORCH_AVAILABLE else None
        self.scaler = None
        self.model = None
        self._loaded = False

    async def load_models(self):
        if self._loaded:
            return
        self._loaded = True

        if not TORCH_AVAILABLE:
            _emit_runtime_unavailable_warning()
            return

        try:
            if not os.path.exists(SCALER_PATH) or not os.path.exists(MODEL_PATH):
                raise FileNotFoundError("glucose predictor artifacts missing")

            with warnings.catch_warnings():
                try:
                    from sklearn.exceptions import InconsistentVersionWarning

                    warnings.simplefilter("error", InconsistentVersionWarning)
                except Exception:
                    pass
                self.scaler = joblib.load(SCALER_PATH)

            self.model = GlucoseLSTM(INPUT_SIZE, HIDDEN_SIZE, NUM_LAYERS)
            self.model.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
        except Exception:
            self.scaler = None
            self.model = None
            _emit_runtime_unavailable_warning()

    def predict_scenario(self, current_glucose, carbs, hr, prs_score):
        if self.scaler is None or self.model is None:
            return {"glucose": current_glucose, "stress_is_high": False}

        try:
            features_to_scale = {
                "Glucose": current_glucose,
                "HR": hr,
                "Carbs": carbs,
                "Protein": carbs * 0.15,
                "Fat": carbs * 0.1,
                "Calories": carbs * 4,
                "BMI": 24.0,
                "HbA1c": 5.5,
                "Age": 30,
                "PRS_Score": prs_score,
            }
            scaled_part = self.scaler.transform(pd.DataFrame([features_to_scale]))
            stress_val = 1 if hr > THRESHOLD_HEART_STRESS else 0
            final_input_vector = np.hstack((scaled_part, np.array([[stress_val]])))
            seq_input = np.tile(final_input_vector, (12, 1))
            tensor_input = torch.FloatTensor(seq_input).unsqueeze(0).to(self.device)

            with torch.no_grad():
                pred_scaled = self.model(tensor_input).item()

            dummy = np.zeros((1, 10))
            dummy[0, 0] = pred_scaled
            real_pred = self.scaler.inverse_transform(dummy)[0, 0]
            return {"glucose": round(real_pred, 2), "stress_is_high": bool(stress_val)}
        except Exception:
            return {"glucose": current_glucose, "stress_is_high": False}


if __name__ == "__main__":
    predictor = Predictor()
    print(predictor.predict_scenario(100, 50, 75, 0.9))
