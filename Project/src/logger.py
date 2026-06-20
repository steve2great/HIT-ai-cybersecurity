"""
Persistent alert logger -- writes one JSON line per decision to
`traffic_logs.log`. The course spec explicitly requires a logging /
alerting module for Stage 7/8.

Format: JSONL (one JSON object per line). Easy to grep, easy to ingest
into ELK / Splunk in a production deployment.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_logger(log_path: Path | None = None) -> logging.Logger:
    if log_path is None:
        log_path = Path(__file__).resolve().parent.parent / "traffic_logs.log"

    logger = logging.getLogger("soc_copilot")
    logger.setLevel(logging.INFO)
    # only add a handler once -- Chainlit reloads modules across messages
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        h = logging.FileHandler(log_path, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(h)
    return logger


def log_decision(
    *,
    event: dict[str, Any],
    is_anomaly: bool,
    anomaly_score: float,
    technique_id: str = "",
    confidence: str = "",
    explanation: str = "",
) -> None:
    rec = {
        "ts_logged": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "decision": "ALERT" if is_anomaly else "OK",
        "anomaly_score": round(float(anomaly_score), 4),
        "technique_id": technique_id,
        "confidence": confidence,
        "explanation": explanation,
    }
    get_logger().info(json.dumps(rec, ensure_ascii=False))
