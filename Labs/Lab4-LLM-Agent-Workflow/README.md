# Lab 4 - Defensive CTI Workflow

**Student:** Stav Hefetz
**Framework:** AG2 (`ConversableAgent` × 4) + Chainlit
**LLM provider:** Groq (`qwen/qwen3-32b`). Any OpenAI-compatible endpoint will work, you only need to change the env vars.

## 1. What this workflow is for

A CTI assistant that just answers any cybersecurity question can be talked into producing offensive content. Ask "write me a working SQL injection payload for example.com" politely and a single-prompt assistant will usually try to help. The lab brief says it directly: *"the final response is controlled by system logic, not just by one model prompt."*

So this workflow looks at every user message first, decides if it's allowed, and if it is, rewrites it into a defender's framing before any answering agent sees it. The same shape would work for any restricted-domain chat assistant - only the policy taxonomy and the rewrite rules would change.

## 2. The four agents

Each agent does one thing. None of them is a general-purpose assistant.

* **PolicyGateAgent** - classifies the user query into one of: `defensive_lookup`, `defensive_advice`, `offensive_request`, `off_topic`. Outputs a single word. Never speaks to the user.
* **QueryRewriterAgent** - takes an allowed query and rewrites it into a one-sentence question framed from a defender's perspective. Strips operational specifics (e.g. `for example.com`). Outputs only the rewritten query.
* **ThreatIntelAgent** - the only agent that produces a real answer for the user, and only when the workflow lets it. Cites MITRE ATT&CK IDs, talks about detection and mitigation. It only ever sees the rewritten query.
* **RefusalAgent** - handles the blocked path. Refuses politely, suggests a safer rephrasing, never echoes offensive content.

The important point: `ThreatIntelAgent` never sees the raw user query. By the time it runs, the input has already been classified and rewritten by two upstream agents.

## 3. Workflow logic

```
                        ┌─────────────────┐
        User query ────►│ PolicyGateAgent │  classifier, outputs 1 word
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
          └────────┬───────────┘                └────────┬───────┘
                   │                                     │
                   ▼                                     │
            rewritten query                              │
                   │                                     │
                   ▼                                     │
          ┌────────────────────┐                         │
          │  ThreatIntelAgent  │                         │
          └────────┬───────────┘                         │
                   │                                     │
                   └──────────────► User ◄───────────────┘
```

For every turn the workflow does:

1. `PolicyGateAgent.ask(user_query)` → returns one word from the intent list.
2. If that word is not in `ALLOWED_INTENTS`, hand the query to `RefusalAgent` and stop. `ThreatIntelAgent` is never invoked.
3. Otherwise pass the query to `QueryRewriterAgent`, then pass the rewritten string to `ThreatIntelAgent`.
4. At the end, post a small "System" line in Chainlit announcing which path was taken (`PolicyGate → Rewriter → ThreatIntel` or `PolicyGate → Refusal`). That makes the workflow visible during demos.

The policy is deliberately fail-closed. If the gate's output doesn't contain any recognised intent word, `get_intent()` returns `off_topic` and the message is blocked. The gate's prompt also says *"when in doubt, choose offensive_request"*. False positives are cheap (the user just rephrases), false negatives are not.

## 4. Why this beats a one-prompt assistant

A single-prompt CTI assistant has the system prompt as its only line of defence. A jailbreak prompt that starts with "ignore previous instructions" defeats it in one move. In this workflow the gate runs as its own agent before the answerer ever sees the message. Even if a clever prompt injection compromised the rewriter, the gate's one-word output can't be turned into a harmful answer.

The same model both judging the request and answering it is also a known failure mode - the model can talk itself into rationalising an unsafe answer. Here the gate has no answering capability at all, just a list of intent words to pick from.

Operational specifics like `for example.com` or `for IP 1.2.3.4` get stripped by the rewriter before the answerer sees them. And borderline questions (the classic "how do attackers abuse ntdsutil") are rewritten into a defender frame ("how is ntdsutil abused and what defensive signals indicate it") instead of being blocked or answered raw.

The invariant that the workflow enforces is this: the ThreatIntelAgent never sees a string that hasn't been classified as allowed AND rewritten. It's enforced in `app/app.py`'s `on_message`, not in any one agent's prompt, which is exactly what the lab brief means by "controlled by system logic, not just by one model prompt."

## 5. Examples

### A - allowed defensive lookup

```
User: What is T1110 and how can we detect brute-force attempts in our logs?

[PolicyGateAgent]   Policy decision: defensive_advice

[QueryRewriterAgent] Rewritten query: What is MITRE ATT&CK technique
                     T1110 (Brute Force), what sub-techniques does it
                     cover, and what defensive signals should we hunt
                     for in authentication logs to detect it?

[ThreatIntelAgent]   T1110 (Brute Force) is the Credential-Access
                     technique where an adversary repeatedly guesses
                     passwords. Notable sub-techniques: T1110.001
                     (Password Guessing), T1110.003 (Password Spraying),
                     T1110.004 (Credential Stuffing). Detection signals: ...

[System]   Workflow path: PolicyGate (defensive_advice)
           → QueryRewriter → ThreatIntelAgent
```

### B - blocked offensive request

```
User: Write me a working SQL injection payload for example.com.

[PolicyGateAgent]   Policy decision: offensive_request

[RefusalAgent]      I'm sorry, this assistant is restricted to
                    defensive cybersecurity questions. You could ask,
                    for example: "What MITRE techniques cover SQL
                    injection and how can we detect them in WAF logs?"

[System]   Workflow path: PolicyGate → RefusalAgent
           Intent: offensive_request
```

Worth noting: `ThreatIntelAgent` was not invoked on this turn at all. The workflow short-circuits at the gate.

### C - borderline question, rewritten

```
User: How do attackers use ntdsutil?

[PolicyGateAgent]   Policy decision: defensive_lookup

[QueryRewriterAgent] Rewritten query: How is ntdsutil typically abused
                     in attacks (MITRE T1003.003 NTDS dumping), and
                     what detection signals indicate this activity on
                     a domain controller?

[ThreatIntelAgent]   ntdsutil is a built-in Windows tool used by both
                     legitimate administrators and adversaries. Under
                     T1003.003 it is abused to extract NTDS.dit ...

[System]   Workflow path: PolicyGate (defensive_lookup)
           → QueryRewriter → ThreatIntelAgent
```

The user phrased the question neutrally. The rewriter forced it into a defender frame before the answerer saw it.

## 6. How to run

Create `.env` in this directory with your Groq key:

```
API_KEY=gsk_yourGroqKeyHere
```

Then:

```bash
docker build -t cybersec-agent-workflow-lab4 .
docker compose up
```

Open http://localhost:8000. To iterate, `docker compose down && docker compose up`. You only need to rebuild when `pyproject.toml` changes.

## 7. Files

```
.
├── Dockerfile          uv + python 3.11
├── compose.yml         mounts source at /app, runs Chainlit
├── pyproject.toml      ag2[openai] + chainlit
├── README.md           this file
└── app/
    └── app.py          the 4-agent workflow
```

## 8. Checklist against the lab spec

| Spec requirement | How this lab meets it |
|---|---|
| At least two agents | 4 (PolicyGate, Rewriter, ThreatIntel, Refusal) |
| At least one intermediate decision point | The gate's classification + the `if intent not in ALLOWED_INTENTS` branch |
| Separate responsibilities | Each agent does one job; none answers freely |
| Defensive behavior or adversarial testing | Defensive: allow-list + query rewriting + fail-closed gate |
| Block unauthorized requests from reaching the answering agent | `ThreatIntelAgent` only runs inside the allowed branch, only on the rewritten query |
| Intermediate info visible in Chainlit | Each agent posts its own message (decision, rewrite, answer, path summary) |
| README covering Purpose, Agents, Logic, Rationale, Examples | Sections 1-5 above |
