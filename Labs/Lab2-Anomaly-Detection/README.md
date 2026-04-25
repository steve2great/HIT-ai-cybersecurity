# Lab 2 — Anomaly Detection

📓 **Deliverable:** [`lab2.ipynb`](lab2.ipynb) — fully executed notebook with embedded plots.

---

## Design summary

| Choice | Value | Why |
|---|---|---|
| Dataset | Synthetic (Faker + numpy) | Full control over the attack/normal mix; no download or licence concerns |
| MITRE technique modeled | [T1110 — Brute Force](https://attack.mitre.org/techniques/T1110/) | Maps cleanly to authentication telemetry; both noisy and stealthy variants exist in the wild |
| Volume | 10 000 events, 3 % anomalies | Within the 1-5 % band the lab requires for unsupervised detection |
| Detection model | Isolation Forest (`n_estimators=200`, `contamination=0.03`) | Required by the lab; well-suited to mixed numeric + binary feature space |
| Projection | PCA, 2 components | Deterministic, fast, no extra deps; preserves enough variance to make the anomaly clusters visible |

## Feature design

| Feature | Type | Source |
|---|---|---|
| `hour` | time-based | login timestamp |
| `failed_attempts` | numeric | failed-login counter for the surrounding window |
| `login_duration_ms` | numeric | session length |
| `bytes_sent` | numeric | session payload |
| `protocol` (one-hot) | categorical | ssh / rdp / https |
| `user_is_known` | binary | `username ∈ legitimate-user list` |
| `ip_is_known` | binary | `source_ip ∈ legitimate-IP list` |

`username` and `source_ip` are deliberately **not** one-hot encoded — they are
high-cardinality identifiers, and one-hot encoding would both explode the
feature space and prevent the model from generalising across new accounts
or addresses. Reducing them to a *known-population* boolean mirrors what a
real SOC reputation list provides and is what gives the detector a meaningful
signal on previously-unseen IPs.

## Two attacker profiles

To make the detection problem realistic, anomalies are split between:

- **Loud (~75 %)** — off-hours, unknown user, unknown IP, 8-40 failed attempts,
  very short sessions. Easy for any unsupervised detector.
- **Stealthy (~25 %)** — *credential stuffing* in working hours against
  **known** usernames, only 3-6 failed attempts each. Designed to overlap
  with typo-prone legitimate users so that perfect detection is impossible.

## Result

| Metric | Value |
|---|---|
| Anomalies injected | 300 / 10 000 |
| Anomalies detected | 300 / 10 000 |
| Precision | ≈ 0.987 |
| Recall | ≈ 0.987 |
| F1 | ≈ 0.987 |

The remaining errors are concentrated on the stealthy profile, as expected.
The notebook's PCA plot makes this visible: the loud anomalies sit on a
clearly separated arc, while the stealthy ones are embedded near the normal
cluster.

## How to run

The course-provided Docker image is the supported path:

```bash
cd "labs/lab2 Anomaly Detection"   # in the course repo
docker build -t cybersec-jupyter .
docker compose up
# open http://127.0.0.1:8888/lab and load lab2.ipynb from this folder
```

Or locally:

```bash
pip install numpy pandas scikit-learn matplotlib seaborn faker jupyter
jupyter lab lab2.ipynb
```
