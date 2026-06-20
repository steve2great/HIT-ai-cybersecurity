# Workflow diagrams (Stage 9)

## 1. End-to-end alert flow (per event)

```mermaid
sequenceDiagram
    autonumber
    participant E as Auth event
    participant D as Detector
    participant M as MITRE mapper
    participant A as LLM Triage Agent
    participant U as Analyst UI
    participant L as traffic_logs.log

    E->>D: featurise + score
    D-->>D: is_anomaly?
    alt benign
        D->>L: write "OK" line
        D->>U: status pill "OK"
    else anomalous
        D->>M: event + anomaly_score
        M-->>M: rule chain (T1110.001 / .003 / T1078 / fallback)
        M->>A: Alert{event, technique_id, rationale, recommended_actions}
        A->>A: format_alert_for_llm() + system prompt
        A-->>U: natural-language summary
        A->>L: write "ALERT" line + explanation
    end
```

## 2. Training & evaluation workflow (offline, build-time)

```mermaid
flowchart TD
    G[data/generate.py] --> CSV[(soc_events.csv)]
    CSV --> NB1[01_eda_baseline.ipynb<br/>EDA + LR baseline]
    CSV --> NB2[02_isolation_forest.ipynb<br/>train IF + persist]
    NB2 --> ART[(models/isolation_forest.joblib)]
    NB2 --> NB3[03_security_tests.ipynb<br/>scenario probes + adversarial flip]
    ART --> APP[app/app.py<br/>live UI]
```

## 3. Demo scenario timeline (used by the Replay button)

```mermaid
gantt
    title  Replay incident -- 5 events streamed in order
    dateFormat  YYYY-MM-DDTHH:mm:ss
    axisFormat  %Hh
    section Benign
    alice on VPN, in-hours      :done, e1, 2024-10-09T09:14:11, 5m
    bob on RDP, in-hours        :done, e2, 2024-10-09T10:02:33, 5m
    carol on SSH, in-hours      :done, e3, 2024-10-09T11:48:02, 5m
    section Attacks
    admin BF burst (T1110.001)  :crit, a1, 2024-10-10T02:31:09, 5m
    alice T1078 valid abuse     :crit, a2, 2024-10-10T03:14:22, 5m
```

The replay tests *both* the benign path (three "OK" decisions, no LLM call) and the alert path (two ALERTs with full LLM explanation), in roughly 30 seconds of streaming -- ideal for the 2-5 minute demo video.
