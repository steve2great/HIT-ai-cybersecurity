# User guide (Stage 9)

## 1. Prerequisites

- Python 3.11+ (only needed if running notebooks outside Docker)
- Docker Desktop with Docker Compose
- A free Groq API key from <https://console.groq.com/keys>

## 2. First-time setup

```bash
# from the repo root
cd Project

# generate the dataset
python data/generate.py

# build the model (executes the notebook end-to-end)
jupyter nbconvert --to notebook --execute notebooks/02_isolation_forest.ipynb \
    --output 02_isolation_forest.ipynb
```

Verify that `models/isolation_forest.joblib` now exists.

## 3. Configure the LLM

```bash
cp app/.env.example app/.env
# then edit app/.env and paste your Groq key into API_KEY
```

You can also point at any OpenAI-compatible service by editing `API_BASE_URL`
and `MODEL` in `app/.env`.

## 4. Launch the UI

```bash
cd Project
docker compose up --build
```

Open <http://localhost:8000>.

## 5. Try the three interaction modes

### 5.1 Replay incident (the demo button)

Click **▶ Replay incident**. Five events stream through the pipeline:

- 3 benign events → three "OK" decisions, no LLM call (audit-cheap).
- 1 T1110.001 brute force from `185.243.115.84` → ALERT with high confidence.
- 1 T1078 valid-account abuse from `45.83.64.219` → ALERT with medium confidence.

Each tool call (detector, mapper, LLM) is shown as an expandable Step.

### 5.2 Paste a JSON event

Paste any single-line JSON event matching the schema below into the chat box:

```json
{"timestamp":"2024-10-10T02:31:09","user":"admin","source_ip":"185.243.115.84","service":"ssh","protocol":"tcp22","success":0,"failed_attempts_5min":42,"bytes_sent":240,"session_duration_ms":800,"user_is_known":1,"ip_is_known":0,"hour":2}
```

The pipeline runs end-to-end on that single event.

### 5.3 Ask SOC-Copilot in free text

Type a normal question (`what is T1110.003?`, `should I be worried about RDP from a residential IP?`). The LLM answers but is reminded by its system prompt not to fabricate technique IDs.

## 6. Audit trail

Every decision is appended to `Project/traffic_logs.log` as a JSON line:

```jsonc
{
  "ts_logged": "2024-10-10T02:31:14+00:00",
  "event": {...},
  "decision": "ALERT",
  "anomaly_score": 0.6213,
  "technique_id": "T1110.001",
  "confidence": "high",
  "explanation": "Brute-force attempt against `admin` from..."
}
```

In production this file would be shipped to a SIEM (Splunk, ELK, Sentinel).

## 7. Re-training

If you regenerate the dataset (`python data/generate.py --seed 123`), re-run notebook 02 to refresh the model. The app loads the artefact once per chat session, so click **New chat** in Chainlit to pick up the new model.
