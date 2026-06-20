"""Alert data class -- the single object that flows detector -> mapper -> LLM."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Alert:
    """An anomaly that has been mapped to MITRE ATT&CK.

    The Alert is the *only* thing the LLM Triage Agent ever sees. It is
    fully structured -- no raw log lines, no upstream JSON blobs -- so the
    LLM cannot accidentally repeat unverified facts.
    """

    # the raw event that triggered the alert
    event: dict[str, Any]

    # detector output
    anomaly_score: float                 # lower = more anomalous (sklearn convention)
    detector: str = "IsolationForest"

    # mapper output
    technique_id: str = ""               # e.g. "T1110.001"
    technique_name: str = ""             # e.g. "Brute Force: Password Guessing"
    tactic: str = ""                     # e.g. "Credential Access"
    confidence: str = "medium"           # "low" | "medium" | "high"
    rationale: list[str] = field(default_factory=list)   # mapper reasoning

    # triage advice (filled in by mapper, NOT by LLM)
    recommended_actions: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)  # MITRE URLs

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
