"""
Thin wrapper around the trained Isolation Forest artefact.

The model artefact (`models/isolation_forest.joblib`) is produced by
`notebooks/02_isolation_forest.ipynb` and bundles:
    - the trained `IsolationForest`
    - the fitted `StandardScaler`
    - the canonical feature column order
    - the fitted `PCA` (for visualisation only)
"""

from __future__ import annotations

import joblib
import numpy as np
from pathlib import Path
from typing import Any

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "models" / "isolation_forest.joblib"


class AnomalyDetector:
    def __init__(self, artefact_path: Path = _DEFAULT_PATH):
        if not artefact_path.exists():
            raise FileNotFoundError(
                f"Model not found at {artefact_path}. "
                "Run notebooks/02_isolation_forest.ipynb first."
            )
        bundle = joblib.load(artefact_path)
        self.model         = bundle["model"]
        self.scaler        = bundle["scaler"]
        self.feature_cols  = bundle["feature_columns"]

    def _featurise(self, event: dict[str, Any]) -> np.ndarray:
        row = {c: 0 for c in self.feature_cols}
        for k in ["hour", "failed_attempts_5min", "success",
                  "bytes_sent", "session_duration_ms",
                  "user_is_known", "ip_is_known"]:
            row[k] = event[k]
        svc_col = f"svc_{event['service']}"
        if svc_col in row:
            row[svc_col] = 1
        return np.array([row[c] for c in self.feature_cols], dtype=float)

    def score(self, event: dict[str, Any]) -> tuple[bool, float]:
        """Return (is_anomaly, anomaly_score). Higher score = more anomalous."""
        x  = self._featurise(event).reshape(1, -1)
        xs = self.scaler.transform(x)
        is_anom = bool(self.model.predict(xs)[0] == -1)
        score   = float(-self.model.score_samples(xs)[0])
        return is_anom, score
