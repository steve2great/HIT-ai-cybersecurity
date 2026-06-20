"""Lab 3 - CTI Triage Agent.

A single LLM agent (AG2 ConversableAgent) that helps a SOC analyst do
first-pass triage by looking up MITRE ATT&CK techniques, threat actors,
and Indicators of Compromise in a small local database.

The agent must call a tool to answer factual questions. Pure-text answers
are not enough - Chainlit shows every tool call as an expandable Step.
"""

import json
import os
from typing import Annotated, Dict

import chainlit as cl
from autogen import ConversableAgent
from autogen.events.agent_events import (
    ExecuteFunctionEvent,
    ExecutedFunctionEvent,
)

# ---------------------------------------------------------------------------
# In-memory threat-intel "database"
#
# A real triage agent would query a TIP (Threat Intelligence Platform) such
# as MISP, OpenCTI, or a commercial feed. We use a hard-coded snapshot so
# the lab runs deterministically with no external dependencies.
# ---------------------------------------------------------------------------

MITRE_TECHNIQUES: Dict[str, Dict] = {
    "T1110": {
        "id": "T1110",
        "name": "Brute Force",
        "tactic": "Credential Access",
        "description": (
            "Adversaries may use brute force techniques to gain access to "
            "accounts when passwords are unknown or when password hashes "
            "are obtained."
        ),
        "common_subtechniques": [
            "T1110.001 Password Guessing",
            "T1110.003 Password Spraying",
            "T1110.004 Credential Stuffing",
        ],
        "mitigations": [
            "Account Lockout",
            "Multi-Factor Authentication",
            "Strong Password Policies",
        ],
        "url": "https://attack.mitre.org/techniques/T1110/",
    },
    "T1003": {
        "id": "T1003",
        "name": "OS Credential Dumping",
        "tactic": "Credential Access",
        "description": (
            "Adversaries may attempt to dump credentials to obtain account "
            "login and credential material from the operating system."
        ),
        "common_subtechniques": [
            "T1003.001 LSASS Memory",
            "T1003.003 NTDS",
        ],
        "mitigations": [
            "Credential Guard",
            "Restrict access to LSASS",
        ],
        "url": "https://attack.mitre.org/techniques/T1003/",
    },
    "T1190": {
        "id": "T1190",
        "name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "description": (
            "Adversaries may attempt to exploit a weakness in an "
            "Internet-facing host or system to initially access a network."
        ),
        "common_subtechniques": [],
        "mitigations": [
            "Application Isolation and Sandboxing",
            "Vulnerability Scanning",
            "Network Segmentation",
        ],
        "url": "https://attack.mitre.org/techniques/T1190/",
    },
    "T1059": {
        "id": "T1059",
        "name": "Command and Scripting Interpreter",
        "tactic": "Execution",
        "description": (
            "Adversaries may abuse command and script interpreters to "
            "execute commands, scripts, or binaries."
        ),
        "common_subtechniques": [
            "T1059.001 PowerShell",
            "T1059.003 Windows Command Shell",
        ],
        "mitigations": [
            "Disable or Remove Feature or Program",
            "Execution Prevention",
        ],
        "url": "https://attack.mitre.org/techniques/T1059/",
    },
    "T1090": {
        "id": "T1090",
        "name": "Proxy",
        "tactic": "Command and Control",
        "description": (
            "Adversaries may use a connection proxy to direct network "
            "traffic between systems or act as an intermediary."
        ),
        "common_subtechniques": [
            "T1090.001 Internal Proxy",
            "T1090.002 External Proxy",
        ],
        "mitigations": [
            "Filter Network Traffic",
            "Network Intrusion Prevention",
        ],
        "url": "https://attack.mitre.org/techniques/T1090/",
    },
}

# Quick lookup of "tool-style" command fragments to a technique ID. This is
# how an analyst would actually ask: "I saw `ntdsutil` in a log - what is
# that?".
COMMAND_TO_TECHNIQUE = {
    "ntdsutil": "T1003",
    "comsvcs.dll": "T1003",
    "lsass": "T1003",
    "mimikatz": "T1003",
    "netsh portproxy": "T1090",
    "frp": "T1090",
    "powershell -enc": "T1059",
    "hydra": "T1110",
    "ssh brute": "T1110",
}

THREAT_ACTORS: Dict[str, Dict] = {
    "volt typhoon": {
        "name": "Volt Typhoon",
        "aliases": ["STORM-0391", "BRONZE SILHOUETTE"],
        "attribution": "Suspected People's Republic of China (state-sponsored)",
        "active_since": "mid-2021",
        "targets": [
            "US critical infrastructure (communications, utility, transportation)",
        ],
        "tradecraft": (
            "Living-off-the-land. Heavy reuse of built-in Windows utilities "
            "(ntdsutil, netsh, wmic, PowerShell). Routes C2 through "
            "compromised SOHO routers."
        ),
        "key_techniques": ["T1190", "T1003.001", "T1003.003", "T1090", "T1078"],
        "reference": (
            "https://www.microsoft.com/en-us/security/blog/2023/05/24/"
            "volt-typhoon-targets-us-critical-infrastructure-with-"
            "living-off-the-land-techniques/"
        ),
    },
    "apt28": {
        "name": "APT28",
        "aliases": ["Fancy Bear", "Sofacy", "STRONTIUM"],
        "attribution": "Russian military intelligence (GRU Unit 26165)",
        "active_since": "2004",
        "targets": ["Government", "Military", "Media", "NGO"],
        "tradecraft": (
            "Spear-phishing, custom malware families (X-Agent, X-Tunnel), "
            "credential harvesting via fake login pages."
        ),
        "key_techniques": ["T1566", "T1078", "T1059", "T1003"],
        "reference": "https://attack.mitre.org/groups/G0007/",
    },
    "lazarus": {
        "name": "Lazarus Group",
        "aliases": ["HIDDEN COBRA", "Diamond Sleet"],
        "attribution": "Democratic People's Republic of Korea",
        "active_since": "2009",
        "targets": ["Financial sector", "Cryptocurrency exchanges", "Defense"],
        "tradecraft": (
            "Long-running custom toolchains. Heavy use of supply-chain "
            "compromise and credential theft for financial exfiltration."
        ),
        "key_techniques": ["T1190", "T1059", "T1486", "T1041"],
        "reference": "https://attack.mitre.org/groups/G0032/",
    },
}

# Curated mini IOC database. In production this would be a TIP feed.
IOC_DATABASE: Dict[str, Dict] = {
    "185.243.115.84": {
        "value": "185.243.115.84",
        "type": "ipv4",
        "first_seen": "2024-08-12",
        "last_seen": "2024-11-03",
        "confidence": "high",
        "attributed_to": "Volt Typhoon",
        "notes": "Observed as C2 relay through compromised SOHO router.",
    },
    "evil-update.com": {
        "value": "evil-update.com",
        "type": "domain",
        "first_seen": "2024-01-05",
        "last_seen": "2024-09-22",
        "confidence": "medium",
        "attributed_to": "Lazarus Group",
        "notes": "Fake software-update domain used for initial access lure.",
    },
    "baeffeb5fdef2f42a752c65c2d2a52e84fb57efc906d981f89dd518c314e231c": {
        "value": "baeffeb5fdef2f42a752c65c2d2a52e84fb57efc906d981f89dd518c314e231c",
        "type": "sha256",
        "first_seen": "2023-05-20",
        "last_seen": "2024-10-01",
        "confidence": "high",
        "attributed_to": "Volt Typhoon",
        "notes": "Custom Fast Reverse Proxy (FRP) binary used for C2.",
    },
}


# ---------------------------------------------------------------------------
# Tools - plain Python functions that AG2 will expose to the agent.
#
# Each tool returns a *structured* dict so the LLM can reason about the
# data without us pre-formatting it. Use Annotated[...] to give AG2 the
# parameter description that ends up in the tool schema.
# ---------------------------------------------------------------------------


def lookup_mitre_technique(
    technique_id: Annotated[
        str,
        (
            "MITRE ATT&CK technique ID, e.g. 'T1110' or 'T1003'. "
            "Sub-technique IDs like 'T1003.001' are accepted - only the "
            "parent technique is looked up."
        ),
    ],
) -> Dict:
    """Look up a MITRE ATT&CK technique by its T-ID.

    Returns the technique name, tactic, description, common sub-techniques,
    and recommended mitigations. Use this when the user mentions a specific
    T-ID (e.g. 'what is T1110?') or refers to a built-in tool whose name
    maps to a known technique (e.g. 'ntdsutil', 'mimikatz').
    """

    tid = (technique_id or "").strip().upper()
    # Accept 'T1003.001' by stripping the sub-technique part.
    parent_id = tid.split(".")[0] if "." in tid else tid

    # Also accept queries like "ntdsutil" by mapping through the
    # COMMAND_TO_TECHNIQUE table.
    if parent_id.lower() in COMMAND_TO_TECHNIQUE:
        parent_id = COMMAND_TO_TECHNIQUE[parent_id.lower()]

    record = MITRE_TECHNIQUES.get(parent_id)
    if record is None:
        return {
            "ok": False,
            "error": "technique_not_found",
            "message": (
                f"Technique '{technique_id}' is not in the local database. "
                f"Known IDs: {', '.join(sorted(MITRE_TECHNIQUES.keys()))}."
            ),
        }
    return {"ok": True, "technique": record}


def check_ioc(
    value: Annotated[
        str,
        (
            "The indicator to look up. Can be an IPv4 address "
            "(e.g. '185.243.115.84'), a domain (e.g. 'evil-update.com'), "
            "or a SHA-256 file hash."
        ),
    ],
) -> Dict:
    """Check whether an IOC (IP, domain, or SHA-256 hash) is in the local
    threat-intel database.

    Returns the IOC type, confidence, first/last-seen dates, attributed
    actor, and free-form notes. Use this whenever the user asks about a
    specific indicator they have seen in their telemetry.
    """

    key = (value or "").strip().lower()
    record = IOC_DATABASE.get(key)
    if record is None:
        # `ok` is True because the tool worked correctly - there is simply
        # no record. `found` is the operationally relevant signal for the
        # LLM and the system prompt tells it to communicate the miss
        # honestly instead of inventing a verdict.
        return {
            "ok": True,
            "found": False,
            "message": (
                f"'{value}' is not in the local IOC database. This does "
                f"not necessarily mean the indicator is benign - it just "
                f"means the local feed has no record."
            ),
        }
    return {"ok": True, "found": True, "ioc": record}


def get_threat_actor(
    name: Annotated[
        str,
        (
            "Threat actor name or alias to look up. Matching is "
            "case-insensitive (e.g. 'Volt Typhoon', 'STORM-0391', "
            "'Fancy Bear')."
        ),
    ],
) -> Dict:
    """Return a short profile of a tracked threat actor: attribution,
    targets, tradecraft, and the key MITRE techniques they are known to
    use.

    Use this when the user asks about a named adversary or one of its
    aliases.
    """

    needle = (name or "").strip().lower()
    if not needle:
        return {
            "ok": False,
            "error": "empty_name",
            "message": "Please provide an actor name or alias.",
        }

    for actor_key, actor in THREAT_ACTORS.items():
        aliases = [actor_key] + [a.lower() for a in actor.get("aliases", [])]
        aliases.append(actor["name"].lower())
        if needle in aliases or any(needle == a for a in aliases):
            return {"ok": True, "actor": actor}

    # Fall back to a fuzzy "contains" match.
    for actor_key, actor in THREAT_ACTORS.items():
        aliases = [actor_key, actor["name"].lower()] + [
            a.lower() for a in actor.get("aliases", [])
        ]
        if any(needle in a for a in aliases):
            return {"ok": True, "actor": actor}

    return {
        "ok": False,
        "error": "actor_not_found",
        "message": (
            f"Actor '{name}' is not tracked in the local database. "
            f"Known actors: {', '.join(a['name'] for a in THREAT_ACTORS.values())}."
        ),
    }


# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------

api_base_url = os.getenv("API_BASE_URL")
api_key = os.getenv("API_KEY")
model = os.getenv("MODEL", "qwen/qwen3-32b")

if not api_key:
    raise RuntimeError(
        "API_KEY is not set. "
        "Put it in the lab .env file (e.g. `API_KEY=gsk_...`) before "
        "running `docker compose up`."
    )

llm_config = {
    "config_list": [
        {
            "model": model,
            "api_key": api_key,
            "base_url": api_base_url,
            "price": [0, 0],
        }
    ],
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a Cyber Threat Intelligence triage assistant for a SOC analyst.
You answer questions about MITRE ATT&CK techniques, tracked threat actors,
and suspicious indicators of compromise (IPs, domains, file hashes).

You have access to three tools:

- lookup_mitre_technique(technique_id):
  Resolve a MITRE ATT&CK T-ID. Also accepts the name of a built-in tool
  (e.g. 'ntdsutil', 'mimikatz') and maps it to the corresponding technique.

- check_ioc(value):
  Look up an IOC in the local threat-intel database. Use this whenever
  the user mentions a specific IP, domain, or SHA-256 hash.

- get_threat_actor(name):
  Get a short profile of a tracked threat actor by name or alias.

Operating rules:

1. ALWAYS call a tool to answer factual questions. Never invent a MITRE
   technique, an actor attribution, or an IOC confidence level.

2. If a tool returns 'ok': false, tell the user honestly that the local
   database has no record. Do NOT fabricate a fallback answer.

3. If the user asks about a command-line fragment or a known offensive
   tool name (e.g. 'ntdsutil', 'hydra', 'frp'), call
   lookup_mitre_technique with the fragment as the argument - the tool
   knows how to map common tools to techniques.

4. When the user mentions a threat actor and one of its known
   techniques together, call BOTH tools and combine the results.

5. Keep responses concise. SOC analysts are usually triaging under time
   pressure. After the tool result, give a 2-3 sentence summary.

6. For casual small talk (hello, thanks), answer briefly without calling
   a tool.

Always answer in English.
"""


WELCOME_MESSAGE = """\
Hello. I am the **CTI Triage Agent** for this lab.

I can answer threat-intel questions by querying three local tools:

- 🎯 **MITRE technique lookup** - `What is T1110?` or `I see ntdsutil in logs.`
- 🌐 **IOC check** - `Is 185.243.115.84 suspicious?`
- 🦹 **Threat actor profile** - `Tell me about Volt Typhoon.`

Every fact I state should come from a tool call. Tool calls appear below
as expandable **Steps** so you can verify exactly what I queried.
"""


# ---------------------------------------------------------------------------
# Chainlit handlers
# ---------------------------------------------------------------------------


def _format_content(content: object) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list, tuple)):
        return json.dumps(content, ensure_ascii=True, indent=2)
    return str(content)


@cl.on_chat_start
async def on_chat_start():
    """Create the AG2 assistant and store it in the user session."""

    assistant = ConversableAgent(
        name="cti_triage_agent",
        system_message=SYSTEM_PROMPT,
        llm_config=llm_config,
        human_input_mode="NEVER",
        functions=[lookup_mitre_technique, check_ioc, get_threat_actor],
    )

    cl.user_session.set("assistant", assistant)
    await cl.Message(content=WELCOME_MESSAGE, author="cti_triage_agent").send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle each user message using AG2 async single-agent execution."""

    assistant: ConversableAgent = cl.user_session.get("assistant")

    response = await assistant.a_run(
        message=message.content,
        clear_history=False,
        max_turns=6,
        summary_method="last_msg",
        user_input=False,
    )

    tool_inputs: dict[str, dict[str, str]] = {}

    async for event in response.events:
        if isinstance(event, ExecuteFunctionEvent):
            event_data = event.content
            tool_key = getattr(event_data, "call_id", None) or event_data.func_name
            tool_inputs[tool_key] = {
                "name": event_data.func_name,
                "input": _format_content(event_data.arguments) or "(no arguments)",
            }
            continue

        if not isinstance(event, ExecutedFunctionEvent):
            continue

        event_data = event.content
        tool_key = getattr(event_data, "call_id", None) or event_data.func_name
        step_data = tool_inputs.get(
            tool_key,
            {
                "name": event_data.func_name,
                "input": "(no arguments)",
            },
        )
        async with cl.Step(name=step_data["name"], type="tool") as step:
            step.input = step_data["input"]
            step.output = _format_content(event_data.content)

    summary = await response.summary
    final_text = _format_content(summary)
    await cl.Message(content=final_text).send()
