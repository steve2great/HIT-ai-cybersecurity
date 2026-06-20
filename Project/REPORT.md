# SOC-Copilot - Final Report

**Course:** Introduction to AI for Cybersecurity
**Institute:** Holon Institute of Technology (HIT)
**Instructors:** Dr. Andrei Kojukhov & Viacheslav Nefedov
**Students:** Stav Hefetz, Bar Koldanov
**Project type:** Type 2 - Integrated project
**Repo:** <https://github.com/steve2great/HIT-ai-cybersecurity> (folder `Project/`)

---

## 1. Abstract

SOC-Copilot is a working prototype of an AI-assisted triage assistant for a
Security Operations Centre. It ingests authentication events, detects
anomalies with an Isolation Forest model trained on benign-only traffic,
maps each anomaly to a MITRE ATT&CK technique using a deterministic
rule-based mapper, and produces a natural-language explanation through an
LLM agent that is *grounded* in the mapper's structured output. Every
decision is logged to a persistent audit trail.

The project integrates three components in a way no single component
delivers alone: classical unsupervised ML provides cheap, scalable
detection; the deterministic mapper guarantees auditable technique
attribution; the LLM converts both into analyst-friendly prose. The
result is a system that *teaches* MITRE ATT&CK on every alert.

---

## 2. Problem statement and goals

A Tier-1 SOC analyst faces two pain points:

1. **Alert fatigue** - thousands of alerts per day, most are noise.
2. **Context gap** - translating a raw event ("admin, 42 fails, unknown IP,
   03:14 UTC") into a MITRE technique and an action plan requires deep
   experience the analyst may not have.

SOC-Copilot's goal is to attack both pain points: reduce noise via an
anomaly detector, and close the context gap via a grounded LLM
explanation. The full problem statement, threat model, in-scope / out-of-scope
boundaries and non-goals are documented in
[`docs/problem-statement.md`](docs/problem-statement.md).

---

## 3. Data parsing module

The data layer (Stage 3) is implemented by `data/generate.py`. Real
corporate auth logs cannot be shared in a student project, so we generate
a controlled synthetic dataset with three attacker behaviours labelled
against MITRE techniques.

**Dataset characteristics**

- 10,000 authentication events spread across one simulated week
- 4 services: ssh, rdp, vpn, webapp
- 25 users (20 humans + 5 admin / service accounts)
- 3 % contamination, split across:
  - T1110.001 (Brute Force: Password Guessing) - 50 % of anomalies
  - T1110.003 (Brute Force: Password Spraying) - 30 %
  - T1078 (Valid Accounts) - 20 %

**Feature schema (the model's input)**

| Feature | Type | Why |
|---|---|---|
| `hour` | int 0-23 | Off-hours bias for some attacks |
| `failed_attempts_5min` | int | Brute-force signal |
| `success` | bool | T1078 only ever succeeds |
| `bytes_sent` | int | Real session ≠ guessing attempt |
| `session_duration_ms` | int | Same |
| `user_is_known` | bool | Reputation flag for the user |
| `ip_is_known` | bool | Reputation flag for the IP - the strongest single feature |
| `service` | one-hot | Different attack mixes per service |

The CSV is the single source of truth for all downstream work and is
fully reproducible from `--seed`.

---

## 4. AI model

`notebooks/02_isolation_forest.ipynb` implements Stage 5.

**Model choice.** Isolation Forest, the canonical scikit-learn anomaly
detector. Rationale (see also `docs/architecture.md` §4): no labels
needed for training; fast on CPU; deterministic given a seed; produces a
continuous anomaly score the downstream LLM can use as a confidence
input.

**Training regime.** Trained on the *benign-only* slice of the train
split (7,275 events). The 25 % test split is mixed (benign + anomalous,
n=2,500 with 75 attacks). This is the proper unsupervised setup - the
model never sees a labelled attack at training time.

**Hyperparameters.**

```python
IsolationForest(n_estimators=200, contamination=0.03,
                max_samples="auto", random_state=42, n_jobs=-1)
```

**Persistence.** The trained model, the fitted StandardScaler, the
feature-column order, and a fitted PCA (for visualisation) are bundled
into `models/isolation_forest.joblib` so the live Chainlit app can
hydrate them in milliseconds.

---

## 5. Judging module (the MITRE mapper)

`src/mitre_mapper.py` is what the course brief calls the "judging module."
It takes a detector output `(event, anomaly_score)` and decides which
MITRE technique to assign.

**Why rule-based, not LLM-based?** Course rule (from Lab 3): tools
retrieve facts, the LLM only reasons over them. A rule chain is:

- **Auditable** - we can show *exactly* which clauses fired and why.
- **Deterministic** - same event → same technique every time.
- **Cheap** - runs locally, no API call, sub-millisecond.

The mapper covers three rules + a defensive fallback:

| Rule | Trigger | Confidence |
|---|---|---|
| T1110.001 | `failed_attempts_5min >= 10` AND `ip_is_known == 0` AND `success == 0` | high |
| T1110.003 | `1 ≤ failed_attempts_5min ≤ 5` AND `ip_is_known == 0` AND `service ∈ {webapp, vpn}` | medium / high |
| T1078 | `success == 1` AND `ip_is_known == 0` (and ideally off-hours) | medium |
| Fallback | anomalous but no rule fires | low - explicitly surfaced to the analyst |

Every rule that fires attaches a *human-readable* rationale string. Those
strings are the only facts the LLM is allowed to quote in its
explanation.

---

## 6. Results representation

### 6.1 Stage-5 model results (held-out test set, n=2,500)

| Metric | Value |
|---|---|
| Precision (anomalous) | 0.500 |
| Recall (anomalous) | 0.947 |
| F1 (anomalous) | 0.654 |
| ROC-AUC | 0.996 |
| False positive rate | 2.9 % |

The strong ROC-AUC (0.996) shows the model has correctly learned what
"benign" looks like - it ranks attacks very high in anomaly score. The
modest precision (0.50) is expected at the operating point where recall
is 0.95: at a 3 % contamination cut-off the model surfaces ~71 false
positives per 2,425 benign events. The LLM's confidence rating is what
shields the analyst from those false positives - see §6.4.

**Per-technique recall (the honest picture):**

| Technique | n in test | Recall |
|---|---|---|
| T1110.001 brute force | 41 | **100 %** |
| T1110.003 password spray | 23 | **100 %** |
| T1078 valid accounts | 11 | 64 % |

The pattern is the project's central finding: detection difficulty
*tracks the strength of the per-event signal*. Brute force is loud and
solved; spraying is solvable because each attempt still comes from a
flagged IP; valid-account abuse is genuinely hard because a successful
login from a known user on a never-before-seen IP is *not unconditionally
suspicious* (legitimate users do exactly this from hotels).

### 6.2 Stage-6 scenario probes (`notebooks/03_security_tests.ipynb`)

We constructed four synthetic incident scenarios and measured detection
*and* mapping accuracy:

| Scenario | MITRE | Detection rate | Mapper output |
|---|---|---|---|
| A. Burst brute force | T1110.001 | **100 %** (50/50) | 100 % correct → T1110.001 |
| B. Low-and-slow spray | T1110.003 | **100 %** (30/30) | 100 % correct → T1110.003 |
| C. Valid-account abuse | T1078 | **65 %** (13/20) | 100 % correct → T1078 |
| D. Evasive T1078 (attacker mimics benign byte/duration/hour) | T1078 | **0 %** (0/20) | n/a (not detected) |

### 6.3 Adversarial robustness - what if the attacker compromises a trusted IP?

We flipped `ip_is_known` from 0 to 1 in every scenario above, simulating
the Volt Typhoon-style "SOHO router pivot" documented in Lab 1. The
Isolation Forest holds up better than expected because it is
*multivariate*: scenarios A, B and C still detect at the same rate even
without the `ip_is_known` signal, because they retain other tells
(brute-force counts, in-hours camouflage failing, etc.). Scenario D was
already at 0 % - the model simply has no signal left.

### 6.4 LLM-explanation faithfulness

Spot-checking 20 generated explanations against the structured Alert
they were grounded in (manual review), 100 % of explanations:

1. Quoted the technique ID exactly as the mapper provided it.
2. Quoted at least one rationale string verbatim or near-verbatim.
3. Did not introduce any technique ID, IOC or actor name not present in
   the Alert.

This is the *qualitative* result that justifies the deterministic-mapper
+ constrained-LLM architecture.

---

## 7. Evaluation module

`notebooks/03_security_tests.ipynb` is the evaluation harness. It is
deliberately **scenario-based** rather than only metric-based:

- Average F1 over a random split is the *necessary* metric.
- Per-technique recall is the *honest* metric.
- Scripted-scenario detection rates are the *operational* metric - they
  tell the SOC manager "how does this thing perform on the playbooks I
  actually care about."

The harness is reproducible (`--seed 1..4` for the four scenarios) and
its outputs (numbers + mapper labels + flip-test table) are persisted in
the executed notebook.

---

## 8. Prototype (MVP)

Stage 7/8 deliverable: a Chainlit web app at `app/app.py`. Three
interaction modes:

1. **Replay incident** - streams a scripted 5-event timeline (3 benign
   + 1 T1110.001 + 1 T1078) through the full pipeline. Used in the demo
   video.
2. **JSON paste** - analyst pastes a single event in JSON; the pipeline
   scores it live.
3. **Free-form chat** - analyst asks a question in plain English; the
   constrained LLM answers.

Every tool call (detector, mapper, LLM) renders as an expandable
**Chainlit Step**, so the analyst can audit *how* a decision was made,
not just what it was. Every decision is mirrored to
`Project/traffic_logs.log` as a JSONL audit record.

A full user guide is in [`docs/user-guide.md`](docs/user-guide.md).

---

## 9. Architecture

A diagram-rich treatment is in [`docs/architecture.md`](docs/architecture.md).
Key idea: three trust zones - Trusted Core (code), Constrained LLM Zone
(prompt + ground-truth Alert input), Analyst UI. The LLM is *never*
allowed to invent technique IDs because it never sees raw threat-intel
data - only what the deterministic mapper produced.

---

## 10. Conclusions

1. The unsupervised Isolation Forest works well on **loud** attacks
   (T1110 variants) and predictably struggles on **quiet** attacks
   (T1078). This is not a bug, it is the limit of per-event detection
   when the only signal is "we have never seen this IP."

2. A deterministic mapper between the detector and the LLM is the right
   architectural choice. It gives us auditable technique attribution
   *and* it makes the LLM's job small enough that hallucination becomes
   structurally hard. In 20 sampled explanations, zero contained
   fabricated technique IDs.

3. The 0 % detection on the evasive T1078 scenario is the honest
   limitation: per-event models are defeated by attackers who first
   compromise a trusted IP. The follow-on work is *cross-event*
   correlation (impossible travel, first-time-from-this-IP, etc.) -
   sketched in `docs/limitations.md`.

4. The "AI in cybersecurity" lever here is *not* better detection
   accuracy. It is **lower cost to action**. The LLM turns every alert
   into a teachable moment that quotes MITRE and recommends a concrete
   next step. That is what closes the Tier-1 skill gap.

---

## 11. Repository map

| Stage | Where |
|---|---|
| 1 - Scope | [`README.md`](README.md) |
| 2 - Problem & goal | [`docs/problem-statement.md`](docs/problem-statement.md) |
| 3 - Data | [`data/generate.py`](data/generate.py), `data/soc_events.csv` |
| 4 - EDA + baseline | [`notebooks/01_eda_baseline.ipynb`](notebooks/01_eda_baseline.ipynb) |
| 5 - Modeling | [`notebooks/02_isolation_forest.ipynb`](notebooks/02_isolation_forest.ipynb), `src/detector.py` |
| 6 - Security testing | [`notebooks/03_security_tests.ipynb`](notebooks/03_security_tests.ipynb) |
| 7+8 - MVP + eval | [`app/`](app/), `src/triage_agent.py`, `src/mitre_mapper.py`, `src/logger.py` |
| 9 - Documentation | [`docs/`](docs/) |
| 10 - Final submission | This report, [`poster/poster.md`](poster/poster.md), [`docs/demo-script.md`](docs/demo-script.md), `traffic_logs.log` (generated) |
