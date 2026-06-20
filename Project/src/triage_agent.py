"""
AG2 ConversableAgent that takes a structured Alert and produces a
natural-language triage summary for a SOC analyst.

Design rule (the same one from Lab 3): the LLM never invents facts. It
receives the deterministic mapper output as input and is instructed to
only use those facts.
"""

from __future__ import annotations

import os
from typing import Any

from autogen import ConversableAgent

from .alert import Alert


SYSTEM_PROMPT = """You are SOC-Copilot, a triage assistant for a Tier-1 SOC analyst.

You receive a structured Alert object containing:
  - the raw authentication event
  - the anomaly score from an Isolation Forest detector
  - a MITRE ATT&CK technique ID and name assigned by a deterministic rule-based mapper
  - the rationale strings from the mapper
  - recommended_actions from the mapper (these are the mitigations)
  - reference URLs

Your job is to produce a SHORT, plain-English triage summary aimed at a junior
analyst. The summary must:

1. State what happened in one sentence (who, what, from where, when).
2. State the MITRE technique exactly as the mapper provided it -- DO NOT invent
   a different technique ID.
3. Quote at least one item from `rationale` so the analyst can see the
   evidence.
4. End with the 2-3 most relevant recommended_actions.
5. If `confidence` is 'low', say so explicitly and suggest one extra
   verification step.

Rules:
  - NEVER invent technique IDs, IOC attributions, or threat-actor names.
  - NEVER claim a fact that isn't in the Alert you were given.
  - Keep the whole reply under ~120 words.
  - No markdown headers; use a tight paragraph + a short bullet list of actions.
"""


def build_triage_agent() -> ConversableAgent:
    api_key   = os.environ.get("API_KEY", "")
    base_url  = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
    model     = os.environ.get("MODEL", "qwen/qwen3-32b")

    llm_config = {
        "config_list": [{
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "api_type": "openai",
        }],
        "temperature": 0.2,
    }

    return ConversableAgent(
        name="soc-copilot",
        system_message=SYSTEM_PROMPT,
        llm_config=llm_config,
        human_input_mode="NEVER",
    )


def format_alert_for_llm(alert: Alert) -> str:
    """Render the structured Alert as a compact, unambiguous prompt input."""
    ev = alert.event
    lines = [
        "ALERT OBJECT (this is the only ground truth):",
        f"  event:",
        f"    timestamp        : {ev.get('timestamp', '')}",
        f"    user             : {ev.get('user', '')}",
        f"    source_ip        : {ev.get('source_ip', '')}",
        f"    service          : {ev.get('service', '')}",
        f"    success          : {ev.get('success', '')}",
        f"    failed_attempts_5min : {ev.get('failed_attempts_5min', '')}",
        f"    hour             : {ev.get('hour', '')}",
        f"    ip_is_known      : {ev.get('ip_is_known', '')}",
        f"  detector           : {alert.detector}",
        f"  anomaly_score      : {alert.anomaly_score:.3f}",
        f"  technique_id       : {alert.technique_id}",
        f"  technique_name     : {alert.technique_name}",
        f"  tactic             : {alert.tactic}",
        f"  confidence         : {alert.confidence}",
        f"  rationale          :",
    ]
    for r in alert.rationale:
        lines.append(f"    - {r}")
    lines.append("  recommended_actions:")
    for a in alert.recommended_actions:
        lines.append(f"    - {a}")
    lines.append(f"  references         : {', '.join(alert.references)}")
    lines.append("")
    lines.append("Produce the triage summary now.")
    return "\n".join(lines)
