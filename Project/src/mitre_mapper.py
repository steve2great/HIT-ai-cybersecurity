"""
Deterministic MITRE ATT&CK mapper.

Design rule
-----------
This file is the *only* place where an event's raw features are translated
into ATT&CK technique IDs.  The LLM in the triage agent receives the
mapper's structured output and must ground its explanation in those facts.

The rules are intentionally simple and auditable -- if a rule fires, the
mapper attaches both the technique *and* the human-readable reason that it
fired ("48 failed attempts in a 5-minute window from an unknown IP").
That reason is what the LLM is later allowed to quote.

The mapper rules below cover the three attack profiles produced by the
synthetic generator:

    T1110.001 Brute Force: Password Guessing
    T1110.003 Brute Force: Password Spraying
    T1078     Valid Accounts

plus a catch-all `T1078`-style "unknown IP, off-hours" rule that fires when
no specific rule matches but the event is still anomalous.
"""

from __future__ import annotations

from typing import Any

from .alert import Alert


# ---------------------------------------------------------------------------
# ATT&CK catalogue (snapshot, mirrors Lab 3's tool)
# ---------------------------------------------------------------------------

ATTACK_CATALOGUE: dict[str, dict[str, Any]] = {
    "T1110.001": {
        "name": "Brute Force: Password Guessing",
        "tactic": "Credential Access",
        "url": "https://attack.mitre.org/techniques/T1110/001/",
        "mitigations": [
            "Enforce account lockout policies",
            "Require multi-factor authentication on internet-facing services",
            "Rate-limit failed login attempts at the network edge",
        ],
    },
    "T1110.003": {
        "name": "Brute Force: Password Spraying",
        "tactic": "Credential Access",
        "url": "https://attack.mitre.org/techniques/T1110/003/",
        "mitigations": [
            "Detect distributed failure patterns across many user accounts from a single source",
            "Enforce strong password policies that defeat common-password sprays",
            "Require MFA for all externally reachable services",
        ],
    },
    "T1078": {
        "name": "Valid Accounts",
        "tactic": "Defense Evasion / Persistence / Initial Access",
        "url": "https://attack.mitre.org/techniques/T1078/",
        "mitigations": [
            "Alert on successful logins from previously-unseen IPs or geographies",
            "Tie session approval to device posture (managed laptop, MDM)",
            "Time-of-day conditional access for admin accounts",
        ],
    },
    "T1190": {
        "name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "url": "https://attack.mitre.org/techniques/T1190/",
        "mitigations": [
            "Patch externally exposed services",
            "Put a WAF in front of public web applications",
        ],
    },
}


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def _rule_brute_force(ev: dict[str, Any]) -> tuple[bool, list[str]]:
    """T1110.001 -- many failed logins in 5 min, unknown IP, single user."""
    reasons: list[str] = []
    if ev["failed_attempts_5min"] >= 10:
        reasons.append(
            f"{ev['failed_attempts_5min']} failed logins in a 5-minute window "
            f"(threshold = 10)"
        )
    if not ev["ip_is_known"]:
        reasons.append(f"source IP {ev['source_ip']} is not in the known-good list")
    if ev["success"] == 0 and reasons:
        reasons.append("attempt did not succeed (consistent with guessing)")
    fired = len(reasons) >= 2 and ev["failed_attempts_5min"] >= 10
    return fired, reasons


def _rule_password_spray(ev: dict[str, Any]) -> tuple[bool, list[str]]:
    """T1110.003 -- low per-user fails BUT unknown IP, in-hours camouflage.

    The single-event signal is weak (1-3 fails); we lean on
    `ip_is_known == 0` + `success == 0` + a service that is internet-facing
    (`webapp` / `vpn`).
    """
    reasons: list[str] = []
    if not ev["ip_is_known"]:
        reasons.append(f"source IP {ev['source_ip']} is not in the known-good list")
    if ev["success"] == 0 and 1 <= ev["failed_attempts_5min"] <= 5:
        reasons.append(
            f"{ev['failed_attempts_5min']} failed attempt(s) -- consistent with "
            "low-and-slow spraying"
        )
    if ev["service"] in {"webapp", "vpn"}:
        reasons.append(f"target service '{ev['service']}' is internet-facing")
    fired = len(reasons) >= 3 and ev["success"] == 0
    return fired, reasons


def _rule_valid_accounts(ev: dict[str, Any]) -> tuple[bool, list[str]]:
    """T1078 -- SUCCESS from unknown IP, off-hours."""
    reasons: list[str] = []
    if ev["success"] == 1 and not ev["ip_is_known"]:
        reasons.append(
            f"successful login from unknown IP {ev['source_ip']} "
            f"(user '{ev['user']}' has no prior session from this address)"
        )
    if ev["hour"] in {0, 1, 2, 3, 4, 5, 22, 23}:
        reasons.append(f"login occurred at {ev['hour']:02d}:xx -- outside business hours")
    fired = ev["success"] == 1 and not ev["ip_is_known"] and len(reasons) >= 1
    return fired, reasons


# the order matters -- specific rules win over generic ones
_RULES = [
    ("T1110.001", _rule_brute_force),
    ("T1110.003", _rule_password_spray),
    ("T1078",     _rule_valid_accounts),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def map_event(event: dict[str, Any], anomaly_score: float) -> Alert:
    """Turn one anomalous event into a fully-populated Alert."""
    technique_id = ""
    rationale: list[str] = []
    confidence = "low"

    for tid, rule in _RULES:
        fired, reasons = rule(event)
        if fired:
            technique_id = tid
            rationale = reasons
            confidence = "high" if len(reasons) >= 3 else "medium"
            break

    if not technique_id:
        # the detector flagged the event but no specific rule matched
        # -> still useful: surface what we *do* know
        rationale = [
            f"anomaly_score = {anomaly_score:.3f} (lower is more anomalous)",
            "no single MITRE rule matched -- treat as 'unspecified credential anomaly'",
        ]
        if not event.get("ip_is_known", 1):
            rationale.append(f"source IP {event['source_ip']} is unknown")
            technique_id = "T1078"        # default to the most defensible label
            confidence = "low"
        else:
            technique_id = "T1078"
            confidence = "low"

    meta = ATTACK_CATALOGUE[technique_id]
    return Alert(
        event=event,
        anomaly_score=float(anomaly_score),
        technique_id=technique_id,
        technique_name=meta["name"],
        tactic=meta["tactic"],
        confidence=confidence,
        rationale=rationale,
        recommended_actions=meta["mitigations"],
        references=[meta["url"]],
    )
