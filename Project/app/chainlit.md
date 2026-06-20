# SOC-Copilot

AI-assisted triage for authentication anomalies.

**How it works**

1. An Isolation Forest detector scores every authentication event.
2. A deterministic MITRE ATT&CK mapper labels every anomaly with a technique ID.
3. An LLM agent explains each alert in plain English - grounded in the mapper's output only.

Click **Replay incident** to watch a scripted attack timeline flow through the pipeline.
