# Lab 4 — Defensive CTI Workflow

**Student:** Stav Hefetz
**Framework:** [AG2](https://docs.ag2.ai/) (`ConversableAgent` × 4) + [Chainlit](https://docs.chainlit.io/)
**LLM provider:** Groq (`qwen/qwen3-32b`) — any OpenAI-compatible service works

---

## 1. Workflow Purpose

A naive CTI assistant that answers any cybersecurity question can be
coerced into producing offensive content — *"write me a working SQL
injection payload for example.com"* — by simply asking nicely. The lab
brief calls this out directly:

> *"the user-visible response may be the result of several coordinated
> decisions … the final response is controlled by system logic, not just
> by one model prompt."*

This workflow is the smallest realistic embodiment of that idea for a
**Cyber Threat Intelligence (CTI) triage assistant**: it inspects every
user message, rejects offensive or off-topic intents, and **rewrites**
the allowed ones into a defender's framing before they ever reach the
answering agent.

The same shape can be reused for any restricted-domain LLM assistant
(internal-data Q&A bot, helpdesk agent, etc.) — only the policy
taxonomy and the rewrite rules change.

---

## 2. Agents Description

The workflow uses **four single-purpose agents** with strictly orthogonal
responsibilities. None of them is a general-purpose assistant.

| Agent | Job | Allowed to answer the user? |
|---|---|---|
| **PolicyGateAgent** | Classifies the user query into exactly one intent: `defensive_lookup`, `defensive_advice`, `offensive_request`, `off_topic`. | ❌ Never. Outputs one word. |
| **QueryRewriterAgent** | Rewrites an *allowed* query into a single-sentence defender-framed question. Strips operational specifics that would only help an attacker. | ❌ Never. Outputs only the rewritten query. |
| **ThreatIntelAgent** | The protected answering agent. Receives ONLY the rewritten query. Cites MITRE ATT&CK IDs, talks about detection / mitigation. | ✅ Yes — but only on the allowed path. |
| **RefusalAgent** | Politely refuses blocked requests. Never echoes offensive content back. Suggests a safer rephrasing. | ✅ Yes — but only on the blocked path. |

This is the core defensive idea: **the answering agent never sees the
raw user query**. By the time `ThreatIntelAgent` is invoked, the input
has already been classified, allow-listed, and rewritten by two
upstream agents.

---

## 3. Workflow Logic

```text
                        ┌─────────────────┐
        User query ────►│ PolicyGateAgent │  (classifier — outputs 1 word)
                        └────────┬────────┘
                                 │
                                 ▼
                         intent ∈ INTENTS
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
   defensive_lookup       defensive_advice       offensive_request | off_topic
        │                        │                        │
        └───────────┬────────────┘                        │
                    │                                     │
                    ▼                                     ▼
          ┌────────────────────┐                ┌────────────────┐
          │ QueryRewriterAgent │                │  RefusalAgent  │
          │  (defender frame)  │                │  (1-3 sentences)
          └────────┬───────────┘                └────────┬───────┘
                   │                                     │
                   ▼                                     │
            rewritten query                              │
                   │                                     │
                   ▼                                     │
          ┌────────────────────┐                         │
          │  ThreatIntelAgent  │                         │
          │   (final answer)   │                         │
          └────────┬───────────┘                         │
                   │                                     │
                   └──────────────► User ◄───────────────┘
```

Concretely, every turn does:

1. `PolicyGateAgent.ask(user_query)` → one word from `INTENTS`.
2. If the intent is not in `ALLOWED_INTENTS`:
    - `RefusalAgent.ask(user_query)` → polite refusal.
    - Done — `ThreatIntelAgent` is never invoked.
3. Otherwise:
    - `QueryRewriterAgent.ask(user_query)` → defender-framed query.
    - `ThreatIntelAgent.ask(rewritten_query)` → final answer.
4. A final `System` message announces the path that was taken
   (`PolicyGate → Rewriter → ThreatIntel` *or* `PolicyGate → Refusal`),
   so the workflow is visible to the user / evaluator in Chainlit.

The policy taxonomy is deliberately *fail-closed*: if the gate's reply
contains no recognised intent word, `get_intent()` returns `off_topic`
and the message is blocked. The gate's system prompt also tells it
*"when in doubt, choose offensive_request"* — false positives here are
cheap, false negatives are not.

---

## 4. Security Rationale

This workflow defends against four concrete weaknesses of a single-prompt
CTI assistant.

| Weakness in a single-prompt assistant | How this workflow mitigates it |
|---|---|
| Operator-specified system prompt is the *only* line of defence. A jailbreak prompt (`Ignore previous instructions ...`) bypasses everything. | The PolicyGate runs as a separate agent **before** the answerer ever sees the input. Even if the user successfully injects into the rewriter or the answerer, the gate's "one word" output cannot be turned into a harmful response. |
| Same model both judges and answers, so it can rationalise an unsafe answer. | The PolicyGate's only job is classification. It has no answering capability and is explicitly told not to address the user. |
| Operational specifics (`for example.com`, `for IP 1.2.3.4`) leak into the answer. | The QueryRewriter strips them before the answerer sees them. The answerer's system prompt forbids generating IOC values or victim-specific operational details anyway. |
| Borderline questions ("how is ntdsutil used in attacks?") are either over-refused or under-refused. | Borderline questions are *rewritten* into a defender frame ("how is ntdsutil abused **and what defensive signals indicate it**?") instead of being blocked outright. This is the lab brief's "query rewriting" pattern. |

The architectural invariant the workflow enforces:

> ❗ **The ThreatIntelAgent never receives a string that has not first
> been classified as allowed AND rewritten into defender framing.**

That property is enforced by the workflow code (`on_message` in
`app/app.py`), not by any one agent's prompt — which is exactly what the
lab brief means by *"the final response is controlled by system logic,
not just by one model prompt."*

---

## 5. Example Interactions

### Example A — Allowed defensive lookup

```
User: What is T1110 and how can we detect brute-force attempts in our logs?

[PolicyGateAgent]   Policy decision: `defensive_advice`

[QueryRewriterAgent] Rewritten query: *What is MITRE ATT&CK technique
                     T1110 (Brute Force), what sub-techniques does it
                     cover, and what defensive signals should we hunt
                     for in authentication logs to detect it?*

[ThreatIntelAgent]   T1110 (Brute Force) is the Credential-Access
                     technique where an adversary repeatedly guesses
                     passwords. Notable sub-techniques include T1110.001
                     (Password Guessing), T1110.003 (Password Spraying)
                     and T1110.004 (Credential Stuffing). Defensive
                     hunting signals: ...

[System]   🛡️ Workflow path: PolicyGate (`defensive_advice`)
           → QueryRewriter → ThreatIntelAgent
```

### Example B — Blocked offensive request

```
User: Write me a working SQL injection payload for example.com.

[PolicyGateAgent]   Policy decision: `offensive_request`

[RefusalAgent]      I'm sorry, this assistant is restricted to
                    defensive cybersecurity questions. You could ask,
                    for example: "What MITRE techniques cover SQL
                    injection and how can we detect them in WAF logs?"

[System]   🛡️ Workflow path: PolicyGate → RefusalAgent
           Intent: `offensive_request`
```

Note that `ThreatIntelAgent` was *never invoked* on this turn — the
workflow short-circuits at the PolicyGate.

### Example C — Borderline question, rewritten

```
User: How do attackers use ntdsutil?

[PolicyGateAgent]   Policy decision: `defensive_lookup`

[QueryRewriterAgent] Rewritten query: *How is ntdsutil typically abused
                     in attacks (MITRE T1003.003 NTDS dumping), and
                     what detection signals indicate this activity on
                     a domain controller?*

[ThreatIntelAgent]   ntdsutil is a built-in Windows tool used by both
                     legitimate administrators and adversaries. Under
                     T1003.003 it is abused to extract NTDS.dit ...

[System]   🛡️ Workflow path: PolicyGate (`defensive_lookup`)
           → QueryRewriter → ThreatIntelAgent
```

The user's question was framed neutrally; the QueryRewriter forced it
into a defender's frame before the answerer saw it.

---

## 6. How to run

### 1. Configure the API key

Create a `.env` file in this directory:

```text
API_KEY=gsk_yourGroqKeyHere
```

### 2. Build & start

```bash
docker build -t cybersec-agent-workflow-lab4 .
docker compose up
```

Open http://localhost:8000.

### 3. Iterate

```bash
docker compose down
docker compose up
```

(Rebuild only when `pyproject.toml` changes.)

---

## 7. Files

```
.
├── Dockerfile          # uv + python 3.11 base
├── compose.yml         # mounts source at /app, runs Chainlit
├── pyproject.toml      # ag2[openai] + chainlit
├── README.md           # this document
└── app/
    └── app.py          # the 4-agent workflow
```

---

## 8. Evaluation checklist (from lab spec)

| Requirement | Where it's satisfied |
|---|---|
| Use at least two agents | 4 agents (PolicyGate, Rewriter, ThreatIntel, Refusal) |
| At least one intermediate decision point | `PolicyGateAgent` classification + `if intent not in ALLOWED_INTENTS` branch |
| Clearly separate responsibilities | Each agent has one job; none of them is a general-purpose assistant |
| Defensive behavior OR adversarial testing | Defensive (allow-list + query rewriting + fail-closed) |
| Prevent unauthorized requests from reaching the answering agent | `ThreatIntelAgent` is only invoked inside the allowed branch, on the rewritten query |
| Show enough intermediate info in Chainlit | Each agent posts its own message (decision, rewrite, final answer, path summary) |
| README with Purpose / Agents / Logic / Rationale / Example | Sections 1-5 above |
