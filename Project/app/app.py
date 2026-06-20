"""
SOC-Copilot Chainlit application -- Stage 7/8 MVP.

This is the analyst-facing UI. Three interaction modes:

1. **Replay incident**  -- streams a scripted attack scenario through the full
   pipeline (detector -> mapper -> LLM). The point is to demonstrate the
   end-to-end behaviour in the 2-5 minute video.

2. **Process CSV row**  -- analyst pastes a row from the SIEM (or a JSON
   event) and we score it live.

3. **Ask SOC-Copilot**  -- free-form chat. The LLM still must call into the
   detector + mapper to ground its answer.

Every decision is mirrored to traffic_logs.log for audit.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import chainlit as cl

# Make `Project.src.*` importable when chainlit runs us from /app
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))

from Project.src.alert import Alert
from Project.src.detector import AnomalyDetector
from Project.src.logger import log_decision
from Project.src.mitre_mapper import map_event
from Project.src.triage_agent import build_triage_agent, format_alert_for_llm


# ---------------------------------------------------------------------------
# Scripted demo scenario (used by the "Replay incident" action button)
# ---------------------------------------------------------------------------
# A miniature timeline: 3 benign events, then a brute force burst, then a
# stealthy T1078 success. This is what the analyst sees when they hit "Replay".

DEMO_TIMELINE: list[dict[str, Any]] = [
    {"timestamp": "2024-10-09T09:14:11", "user": "alice", "source_ip": "10.20.41.7",
     "service": "vpn", "protocol": "udp1194", "success": 1,
     "failed_attempts_5min": 0, "bytes_sent": 4123, "session_duration_ms": 215_000,
     "user_is_known": 1, "ip_is_known": 1, "hour": 9},
    {"timestamp": "2024-10-09T10:02:33", "user": "bob", "source_ip": "10.20.13.91",
     "service": "rdp", "protocol": "tcp3389", "success": 1,
     "failed_attempts_5min": 0, "bytes_sent": 6210, "session_duration_ms": 320_000,
     "user_is_known": 1, "ip_is_known": 1, "hour": 10},
    {"timestamp": "2024-10-09T11:48:02", "user": "carol", "source_ip": "10.20.7.45",
     "service": "ssh", "protocol": "tcp22", "success": 1,
     "failed_attempts_5min": 1, "bytes_sent": 2800, "session_duration_ms": 120_000,
     "user_is_known": 1, "ip_is_known": 1, "hour": 11},
    # ====== brute force burst (T1110.001) ======
    {"timestamp": "2024-10-10T02:31:09", "user": "admin", "source_ip": "185.243.115.84",
     "service": "ssh", "protocol": "tcp22", "success": 0,
     "failed_attempts_5min": 42, "bytes_sent": 240, "session_duration_ms": 800,
     "user_is_known": 1, "ip_is_known": 0, "hour": 2},
    # ====== valid-account abuse (T1078) ======
    {"timestamp": "2024-10-10T03:14:22", "user": "alice", "source_ip": "45.83.64.219",
     "service": "vpn", "protocol": "udp1194", "success": 1,
     "failed_attempts_5min": 0, "bytes_sent": 9_200, "session_duration_ms": 720_000,
     "user_is_known": 1, "ip_is_known": 0, "hour": 3},
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def _clean_reply(reply: Any) -> str:
    """Extract text from an AG2 reply and strip any <think>...</think>
    reasoning block emitted by reasoning models (e.g. qwen3)."""
    text = reply.get("content", "") if isinstance(reply, dict) else str(reply)
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


async def run_pipeline(event: dict[str, Any]) -> None:
    """Score one event, render the result, log the decision."""
    detector: AnomalyDetector = cl.user_session.get("detector")
    triage = cl.user_session.get("triage_agent")

    # 1. detector step
    async with cl.Step(name="1. Isolation Forest detector", type="tool") as s_det:
        s_det.input = json.dumps(event, indent=2)
        is_anom, score = detector.score(event)
        s_det.output = f"is_anomaly = {is_anom}\nanomaly_score = {score:.4f}"

    if not is_anom:
        await cl.Message(
            author="SOC-Copilot",
            content=f"**Decision: OK** - event from `{event['user']}@{event['source_ip']}` "
                    f"is within normal range (anomaly_score = {score:.3f}).",
        ).send()
        log_decision(event=event, is_anomaly=False, anomaly_score=score)
        return

    # 2. mapper step
    async with cl.Step(name="2. MITRE ATT&CK mapper", type="tool") as s_map:
        alert: Alert = map_event(event, anomaly_score=score)
        s_map.input  = json.dumps(event, indent=2)
        s_map.output = json.dumps(
            {"technique": alert.technique_id, "name": alert.technique_name,
             "confidence": alert.confidence, "rationale": alert.rationale},
            indent=2,
        )

    # 3. LLM triage step
    async with cl.Step(name="3. LLM triage agent", type="tool") as s_llm:
        prompt = format_alert_for_llm(alert)
        s_llm.input = prompt
        try:
            reply = await triage.a_generate_reply(messages=[{"role": "user", "content": prompt}])
            reply_text = _clean_reply(reply)
        except Exception as e:
            reply_text = f"(LLM unavailable: {e})\n\nFalling back to deterministic summary:\n" \
                         f"{alert.technique_id} {alert.technique_name} - {alert.rationale}"
        s_llm.output = reply_text

    # 4. surface the headline message
    headline = (
        f"### 🚨 ALERT - {alert.technique_id} {alert.technique_name}\n"
        f"**Confidence:** {alert.confidence}  |  **Anomaly score:** {score:.3f}  |  "
        f"**Tactic:** {alert.tactic}\n\n"
        f"{reply_text}\n\n"
        f"**Evidence (mapper):**\n" + "\n".join(f"- {r}" for r in alert.rationale) + "\n\n"
        f"**Reference:** {alert.references[0] if alert.references else 'n/a'}"
    )
    await cl.Message(author="SOC-Copilot", content=headline).send()

    log_decision(
        event=event, is_anomaly=True, anomaly_score=score,
        technique_id=alert.technique_id, confidence=alert.confidence,
        explanation=reply_text,
    )


# ---------------------------------------------------------------------------
# Chainlit lifecycle
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start() -> None:
    try:
        detector = AnomalyDetector()
        cl.user_session.set("detector", detector)
    except FileNotFoundError as e:
        await cl.Message(
            author="SOC-Copilot",
            content=f"⚠️ {e}\n\nRun `notebooks/02_isolation_forest.ipynb` first to train the model.",
        ).send()
        return

    try:
        cl.user_session.set("triage_agent", build_triage_agent())
    except Exception as e:
        await cl.Message(
            author="SOC-Copilot",
            content=f"⚠️ Could not initialise LLM agent: {e}\n\nMake sure `API_KEY` is set in `.env`.",
        ).send()

    actions = [
        cl.Action(name="replay", payload={"action": "run"}, label="▶ Replay incident",
                  tooltip="Stream the scripted attack timeline through the pipeline."),
    ]
    await cl.Message(
        author="SOC-Copilot",
        content=(
            "**SOC-Copilot ready.**\n\n"
            "Try one of these:\n"
            "- Click ▶ **Replay incident** below for the canned demo.\n"
            "- Paste a JSON auth event (one line) and I will score it.\n"
            "- Or ask a question (e.g. `what is T1110.003?`).\n"
        ),
        actions=actions,
    ).send()


@cl.action_callback("replay")
async def on_replay(_action: cl.Action) -> None:
    await cl.Message(author="SOC-Copilot",
                     content=f"▶ Replaying **{len(DEMO_TIMELINE)} events**...").send()
    for ev in DEMO_TIMELINE:
        await cl.Message(author="event-stream",
                         content=f"`{ev['timestamp']}  {ev['user']}@{ev['source_ip']}  "
                                 f"{ev['service']}  success={ev['success']}  "
                                 f"fails5m={ev['failed_attempts_5min']}`").send()
        await run_pipeline(ev)


# ---------------------------------------------------------------------------
# Free-form message handler
# ---------------------------------------------------------------------------

JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


@cl.on_message
async def on_message(message: cl.Message) -> None:
    text = message.content.strip()

    # If the analyst pasted JSON, treat it as an event to score
    match = JSON_RE.search(text)
    if match:
        try:
            event = json.loads(match.group(0))
            await run_pipeline(event)
            return
        except json.JSONDecodeError:
            pass  # fall through to chat mode

    # Otherwise, route to the LLM as a chat
    triage = cl.user_session.get("triage_agent")
    if triage is None:
        await cl.Message(author="SOC-Copilot",
                         content="LLM not available. Paste a JSON event to score, "
                                 "or click ▶ Replay incident.").send()
        return
    try:
        reply = await triage.a_generate_reply(messages=[{"role": "user", "content": text}])
        reply_text = _clean_reply(reply)
    except Exception as e:
        reply_text = f"(LLM error: {e})"
    await cl.Message(author="SOC-Copilot", content=reply_text).send()
