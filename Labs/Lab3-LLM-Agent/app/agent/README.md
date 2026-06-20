# cti-triage-agent

## 1. Agent Name

**cti-triage-agent**

---

## 2. Agent Purpose

The agent is a **Cyber Threat Intelligence triage assistant** for a SOC
(Security Operations Centre) analyst. During incident triage, an analyst
typically asks three kinds of questions in quick succession:

1. *"I see this MITRE T-ID / built-in command in a log - what is it?"*
2. *"Is this IP / domain / file hash known-bad?"*
3. *"What is this threat actor known for?"*

The agent gives structured, evidence-backed answers to those questions by
delegating the *lookup* to local tools and using the LLM only to
**reason about and summarise** the structured results - not to invent
threat-intel facts.

This description is the technical task specification for the agent's
system prompt: the system prompt explicitly forbids hallucinated answers
and requires every factual claim to come from a tool call.

> **Educational focus**: the lab tests *tool integration mechanics*, not
> production-grade threat intelligence. The data inside the tools is a
> hand-curated snapshot, not a live feed.

---

## 3. Agent Tools

The agent exposes **three tools**, each modelled after a real CTI workflow
component:

### 3.1 `lookup_mitre_technique(technique_id)`

**Purpose:** resolve a MITRE ATT&CK technique by its T-ID.

**Input:**
- `technique_id` *(str)* - a T-ID such as `T1110` or `T1003.001`. Also
  accepts the names of common offensive tools (`ntdsutil`, `mimikatz`,
  `hydra`, `frp`, ...) which the tool internally maps to the
  corresponding parent technique.

**Output (success):**
```jsonc
{
  "ok": true,
  "technique": {
    "id": "T1110",
    "name": "Brute Force",
    "tactic": "Credential Access",
    "description": "...",
    "common_subtechniques": ["T1110.003 Password Spraying", ...],
    "mitigations": ["Multi-Factor Authentication", ...],
    "url": "https://attack.mitre.org/techniques/T1110/"
  }
}
```

**Output (miss):** `{ "ok": false, "error": "technique_not_found", "message": "..." }`

---

### 3.2 `check_ioc(value)`

**Purpose:** check whether an indicator (IP, domain, or SHA-256 file
hash) is present in the local threat-intel database.

**Input:**
- `value` *(str)* - the indicator to look up. Matching is
  case-insensitive.

**Output (success):**
```jsonc
{
  "ok": true,
  "found": true,
  "ioc": {
    "value": "185.243.115.84",
    "type": "ipv4",
    "first_seen": "2024-08-12",
    "last_seen":  "2024-11-03",
    "confidence": "high",
    "attributed_to": "Volt Typhoon",
    "notes": "Observed as C2 relay through compromised SOHO router."
  }
}
```

**Output (miss):** `{ "ok": true, "found": false, "message": "..." }`

The tool deliberately distinguishes *"not in our feed"* from *"feed
errored"* - a miss is not the same as a clean indicator, and the system
prompt makes the agent communicate that to the user.

---

### 3.3 `get_threat_actor(name)`

**Purpose:** return a short profile of a tracked threat actor (Volt
Typhoon, APT28, Lazarus Group, etc.) by name or alias.

**Input:**
- `name` *(str)* - actor name or one of its aliases
  (e.g. `STORM-0391`, `Fancy Bear`). Case-insensitive, with substring
  fallback.

**Output (success):**
```jsonc
{
  "ok": true,
  "actor": {
    "name": "Volt Typhoon",
    "aliases": ["STORM-0391", "BRONZE SILHOUETTE"],
    "attribution": "Suspected People's Republic of China (state-sponsored)",
    "active_since": "mid-2021",
    "targets": [...],
    "tradecraft": "...",
    "key_techniques": ["T1190", "T1003.001", ...],
    "reference": "https://www.microsoft.com/.../volt-typhoon-..."
  }
}
```

---

## 4. Tool-Agent Responsibility Split

The agent follows the course rule:

> **Tools** are responsible for *data retrieval, normalisation and
> structuring*. The **LLM** is responsible for *reasoning, explanation,
> and triage advice*.

Concrete consequences for this agent:

| Responsibility | Where it lives |
|---|---|
| Maintaining the ATT&CK / IOC / actor records | Tools (`MITRE_TECHNIQUES`, `IOC_DATABASE`, `THREAT_ACTORS`) |
| Mapping fuzzy input (e.g. `ntdsutil` → `T1003`) | Tool (`COMMAND_TO_TECHNIQUE`) |
| Deciding *which* tool to call given the user's intent | LLM, guided by the system prompt |
| Combining results from two tool calls (e.g. actor + technique) | LLM |
| Refusing to invent facts when a tool returns `ok: false` | LLM, enforced by the system prompt |

This split is what makes the agent *auditable*: every factual claim in
the final answer is traceable to an expandable Chainlit Step.

---

## 5. Implementation Details

- **Framework:** AG2 `ConversableAgent` (single-agent tool pattern).
- **UI:** Chainlit, with each tool call rendered as an expandable Step.
- **LLM provider:** Groq by default (`qwen/qwen3-32b`) via OpenAI-compatible
  API. Set `API_KEY` in `.env`; the model and base URL are configurable in
  `compose.yml`.
- **Tool wiring:** `functions=[lookup_mitre_technique, check_ioc,
  get_threat_actor]` on the `ConversableAgent` constructor - the AG2
  framework derives JSON schemas from the `Annotated[...]` parameter
  hints automatically.

---

## 6. Example Interaction

### Example 1 - Technique lookup from a built-in command

```
User: I see ntdsutil being invoked in a domain controller event log,
      what is that?

[Step] lookup_mitre_technique
  input:  { "technique_id": "ntdsutil" }
  output: { "ok": true, "technique": { "id": "T1003", ... } }

Agent: ntdsutil maps to T1003 - OS Credential Dumping (Credential Access).
       It is commonly abused to dump the NTDS.dit database from a domain
       controller for offline hash cracking. Recommended mitigations are
       Credential Guard and tight restrictions on LSASS access.
```

### Example 2 - IOC + actor combined

```
User: I see traffic to 185.243.115.84 - what is it?

[Step] check_ioc
  input:  { "value": "185.243.115.84" }
  output: { "ok": true, "found": true, "ioc": { ..., "attributed_to": "Volt Typhoon" } }

[Step] get_threat_actor
  input:  { "name": "Volt Typhoon" }
  output: { "ok": true, "actor": { ... } }

Agent: 185.243.115.84 is in our IOC feed with HIGH confidence as a
       Volt Typhoon C2 relay (last seen 2024-11-03). Volt Typhoon is a
       suspected PRC state-sponsored group known for living-off-the-land
       tradecraft and routing C2 through compromised SOHO routers.
       Recommend isolating the host and pivoting to hunt for ntdsutil
       / LSASS-dump activity (T1003).
```

### Example 3 - Honest miss

```
User: Is 8.8.8.8 dangerous?

[Step] check_ioc
  input:  { "value": "8.8.8.8" }
  output: { "ok": true, "found": false, "message": "8.8.8.8 is not in
            the local IOC database. This does not necessarily mean..." }

Agent: 8.8.8.8 is not in our local IOC feed. That alone is not proof it
       is safe - it just means we have no record. If you want a stronger
       opinion, enrich it against an external feed (VirusTotal, OTX).
```

---

## 7. Limitations

- The technique / IOC / actor records are **hard-coded snapshots**.
  Refreshing them against a live feed (MISP, OpenCTI, MITRE STIX) is out
  of scope for this lab.
- The agent has no notion of *case context* - it answers one IOC at a
  time. Aggregation across an incident timeline is a Lab 4 / 5 problem.
- The fuzzy `name → actor` matching is intentionally simple and may
  misfire on ambiguous aliases.
