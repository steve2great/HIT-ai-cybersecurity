# SOC-Copilot - AI-Assisted Triage for Authentication Anomalies

**Course:** Introduction to AI for Cybersecurity
**Institute:** Holon Institute of Technology (HIT)
**Instructors:** Dr. Andrei Kojukhov & Viacheslav Nefedov
**Students:** Stav Hefetz, Bar Koldanov
**Project type:** Type 2 - Integrated Project

---

## Demo video

🎬 **YouTube:** *(link will be added after recording - see [`docs/demo-script.md`](docs/demo-script.md))*

---

## 1. One-line pitch

> **Traditional SOC tools generate alerts. SOC-Copilot generates _explanations_.**

SOC-Copilot is a prototype Security Operations Centre assistant that detects
suspicious authentication events with an unsupervised anomaly-detection model,
maps each detection to a **MITRE ATT&CK** technique, and uses an LLM to
explain - in plain English - *why* the event is suspicious and *what the
analyst should do next*.

---

## 2. Problem statement

Modern SOC analysts drown in alerts. Two failure modes follow:

1. **Alert fatigue** - junior analysts cannot tell a real attack from a noisy
   benign event because alerts arrive without context.
2. **Skill gap** - interpreting a raw alert (`5 failed SSH logins, then 1
   success, from 185.243.115.84 at 03:14 UTC`) requires deep ATT&CK
   knowledge that most Tier-1 analysts do not yet have.

The result is missed intrusions (false negatives ignored) and exhausted
analysts (true positives never reach a senior responder).

---

## 3. Project goal

Build an end-to-end prototype that, given a stream of authentication events:

1. **Detects** anomalies with a classical ML model (Isolation Forest) trained
   on normal traffic - no labels needed at training time.
2. **Classifies** each detection against the MITRE ATT&CK framework using a
   deterministic rule-based mapper (auditable, no hallucination).
3. **Explains** each alert in natural language using an LLM agent that is
   *grounded* in the structured output of steps 1 and 2 - the LLM is
   forbidden from inventing technique IDs or IOCs.
4. **Logs and alerts** every decision to a persistent audit trail
   (`traffic_logs.log`) so the system is reviewable after the fact.

---

## 4. Why this matters (uniqueness for poster)

| Conventional SOC tool | SOC-Copilot |
|---|---|
| Alerts as opaque rules (e.g. "5 failed logins in 60 s") | Alerts as **stories** ("brute-force attempt against `admin` from an unknown IP - MITRE T1110.001") |
| Junior analysts must memorise ATT&CK | The system *teaches* ATT&CK on every alert |
| LLM-only systems hallucinate technique IDs | The mapper is **deterministic**; the LLM only summarises facts the mapper produced |
| Detection logic and explanation are decoupled | A single auditable pipeline: `event → detector → mapper → LLM → analyst` |

---

## 5. High-level architecture

```
┌─────────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Synthetic auth logs │──▶ │ Feature pipeline │──▶ │ Isolation Forest │
└─────────────────────┘    └──────────────────┘    └────────┬─────────┘
                                                            │ anomalies
                                                            ▼
                                                  ┌────────────────────┐
                                                  │ MITRE ATT&CK mapper│
                                                  │  (rule-based)      │
                                                  └────────┬───────────┘
                                                           │ Alert{event, technique}
                                                           ▼
                                                  ┌────────────────────┐
                                                  │ LLM Triage Agent   │
                                                  │  (AG2 + Chainlit)  │
                                                  └────────┬───────────┘
                                                           ▼
                                                  ┌────────────────────┐
                                                  │ Analyst UI +       │
                                                  │ traffic_logs.log   │
                                                  └────────────────────┘
```

Full architecture diagram: [`docs/architecture.md`](docs/architecture.md).

---

## 6. Mapping to course project stages

| # | Stage | Artifact in this repo |
|---|-------|-----------------------|
| 1 | Scope & team | This README |
| 2 | Problem & goal | [`docs/problem-statement.md`](docs/problem-statement.md) |
| 3 | Data collection | [`data/generate.py`](data/generate.py) → `soc_events.csv` |
| 4 | EDA + baseline | [`notebooks/01_eda_baseline.ipynb`](notebooks/01_eda_baseline.ipynb) |
| 5 | Modeling | [`notebooks/02_isolation_forest.ipynb`](notebooks/02_isolation_forest.ipynb) |
| 6 | Security testing | [`notebooks/03_security_tests.ipynb`](notebooks/03_security_tests.ipynb) |
| 7+8 | MVP + evaluation | [`app/`](app/) Chainlit app |
| 9 | Documentation | [`docs/`](docs/) |
| 10 | Final submission | [`REPORT.md`](REPORT.md), [`poster/poster.md`](poster/poster.md), [`docs/demo-script.md`](docs/demo-script.md) |

---

## 7. How to run

### Prerequisites

- Docker + Docker Compose
- A free Groq API key from <https://console.groq.com/keys>

### Quick start

```bash
# 1. Generate the dataset
python Project/data/generate.py

# 2. Train the model (creates Project/models/isolation_forest.joblib)
jupyter nbconvert --to notebook --execute Project/notebooks/02_isolation_forest.ipynb

# 3. Configure API key
echo "API_KEY=gsk_yourGroqKeyHere" > Project/app/.env

# 4. Launch the Chainlit UI
cd Project && docker compose up
```

Then open <http://localhost:8000>. Click the **"Replay incident"** action
button to stream a recorded attack scenario through the pipeline live.

Detailed instructions: [`docs/user-guide.md`](docs/user-guide.md).

---

## 7a. Input format (scoring your own events)

There are three ways to drive the app:

1. **▶ Replay incident** - replays a built-in 5-event timeline (defined in
   `app/app.py`). Nothing runs until you click it; the app does not
   auto-load any file on startup.
2. **Paste a JSON event** - paste a single authentication event (one JSON
   object) into the chat box and it is scored live through
   detector → mapper → LLM.
3. **Ask a free-form question** - e.g. `what is T1110.003?`.

> **Note on file uploads:** the app accepts events as **pasted JSON**, not as
> uploaded files. There is no file-ingestion path, so the file-upload button is
> disabled in the UI on purpose (`features.spontaneous_file_upload = false` in
> `app/.chainlit/config.toml`). To score a batch, paste events one at a time.

### Expected JSON schema

Every field below should be present. Types matter: `success`,
`user_is_known`, `ip_is_known` are `0`/`1`; counts are integers.

| Field | Type | Meaning |
|---|---|---|
| `timestamp` | string (ISO-8601) | when the event occurred |
| `user` | string | account name |
| `source_ip` | string | source IP address |
| `service` | `ssh` \| `rdp` \| `vpn` \| `webapp` | target service |
| `protocol` | string | e.g. `tcp22` (informational) |
| `success` | `0` \| `1` | did the auth succeed |
| `failed_attempts_5min` | int | failed logins in the preceding 5 min |
| `bytes_sent` | int | bytes sent in the session |
| `session_duration_ms` | int | session length in milliseconds |
| `user_is_known` | `0` \| `1` | is the user previously seen |
| `ip_is_known` | `0` \| `1` | is the source IP previously seen |
| `hour` | int 0-23 | hour of day |

### Example - a brute-force event (produces a T1110.001 alert)

```json
{"timestamp":"2024-10-10T02:45:00","user":"root","source_ip":"203.0.113.66","service":"ssh","protocol":"tcp22","success":0,"failed_attempts_5min":37,"bytes_sent":210,"session_duration_ms":650,"user_is_known":1,"ip_is_known":0,"hour":2}
```

### Example - a benign event (produces an "OK" decision)

```json
{"timestamp":"2024-10-09T09:14:11","user":"alice","source_ip":"10.20.41.7","service":"vpn","protocol":"udp1194","success":1,"failed_attempts_5min":0,"bytes_sent":4123,"session_duration_ms":215000,"user_is_known":1,"ip_is_known":1,"hour":9}
```

---

## 8. Repository layout

```
Project/
├── README.md                  ← you are here
├── REPORT.md                  ← Stage 10 written report
├── data/
│   ├── generate.py            ← synthetic auth-log generator
│   └── soc_events.csv         ← generated dataset (gitignored if large)
├── notebooks/
│   ├── 01_eda_baseline.ipynb  ← Stage 4
│   ├── 02_isolation_forest.ipynb ← Stage 5
│   └── 03_security_tests.ipynb   ← Stage 6
├── src/
│   ├── detector.py            ← trained-model wrapper
│   ├── mitre_mapper.py        ← deterministic ATT&CK mapper
│   ├── alert.py               ← Alert dataclass
│   └── triage_agent.py        ← AG2 agent + tools
├── app/
│   ├── app.py                 ← Chainlit entry point
│   ├── chainlit.md            ← welcome screen
│   └── .env.example
├── docs/
│   ├── problem-statement.md   ← Stage 2
│   ├── architecture.md        ← Stage 9
│   ├── workflow.md            ← Stage 9
│   ├── user-guide.md          ← Stage 9
│   ├── limitations.md         ← Stage 9
│   └── demo-script.md         ← 2-5 min recording plan
├── poster/
│   └── poster.md              ← Stage 10 poster content
├── models/
│   └── isolation_forest.joblib (generated)
├── traffic_logs.log           (generated by app)
├── Dockerfile
├── compose.yml
└── pyproject.toml
```
