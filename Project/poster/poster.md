# SOC-Copilot - Poster

> _This file holds the **content** for the poster. To turn it into the
> visual artefact, paste each block into your poster template (PowerPoint,
> Canva, LaTeX `tikzposter`, etc.). The layout suggested below is a
> standard 3-column academic poster._

---

## TITLE BAR

**SOC-Copilot - AI-Assisted Triage for Authentication Anomalies**

> Traditional SOC tools generate alerts. *SOC-Copilot generates explanations.*

Stav Hefetz & Bar Koldanov · HIT · Course: Introduction to AI for Cybersecurity
Instructors: Dr. Andrei Kojukhov & Viacheslav Nefedov

---

## COLUMN 1

### The problem

Tier-1 SOC analysts drown in alerts. Two failure modes:
- **Alert fatigue** - too many alerts, most are noise.
- **Context gap** - analyst sees raw events, not MITRE techniques or
  recommended actions. The skill required to bridge the gap is exactly
  what Tier-1 lacks.

Result: real intrusions get dismissed as noise. (Documented in the 2013
Target breach and many others.)

### Our angle

Three components, each with a sharp job:

1. **Unsupervised detector** - Isolation Forest trained on benign-only
   traffic. No attacker labels needed.
2. **Deterministic MITRE mapper** - rule chain that assigns the technique
   ID and explains *why*.
3. **Constrained LLM agent** - turns the structured alert into a
   plain-English triage paragraph for a junior analyst.

The LLM never sees raw threat-intel data, so it cannot invent technique
IDs. Every claim it makes is traceable to the mapper output.

---

## COLUMN 2

### Architecture

```
event → detector → mapper → LLM agent → analyst
                                ↓
                          traffic_logs.log
```

### Data

10,000 synthetic authentication events / week, 3 % attack contamination,
labelled against three MITRE techniques:

- T1110.001 Brute Force: Password Guessing
- T1110.003 Brute Force: Password Spraying
- T1078 Valid Accounts (stolen credentials)

Open-source generator: `data/generate.py` - fully reproducible.

### Headline results

| Metric | Value |
|---|---|
| ROC-AUC | **0.996** |
| Recall (all attacks) | 0.95 |
| F1 (anomalous) | 0.65 |
| Recall T1110.001 | **100 %** |
| Recall T1110.003 | **100 %** |
| Recall T1078 | 64 % |
| LLM-explanation faithfulness (manual review) | **100 %** |

---

## COLUMN 3

### Scenario probes - adversarial robustness

| Scenario | MITRE | Detection |
|---|---|---|
| A burst brute force | T1110.001 | 100 % |
| B low-and-slow spray | T1110.003 | 100 % |
| C valid-account abuse | T1078 | 65 % |
| D evasive (attacker mimics benign) | T1078 | **0 %** |

The 0 % on scenario D is **honest**: per-event detection cannot defeat
an attacker who first compromises a trusted IP (the Volt Typhoon SOHO-router
playbook). Future work: cross-event correlation.

### What's unique

- The LLM is **constrained by architecture**, not just by prompt.
- Every alert is also a **teachable moment** - it quotes MITRE and
  recommends a next step.
- Fully reproducible: `docker compose up`.

### Project links

- GitHub: <https://github.com/steve2great/HIT-ai-cybersecurity> →
  folder `Project/`
- Source CTI reference: Microsoft *Volt Typhoon* report (May 2023)
- MITRE ATT&CK techniques used: T1110, T1078

### Frameworks & tools

`scikit-learn` (Isolation Forest, PCA, LR baseline) · `AG2`
(ConversableAgent) · `Chainlit` (analyst UI) · `Groq` (LLM API,
OpenAI-compatible) · `Docker Compose` · `Python 3.11`

---

## FOOTER

Students: **Stav Hefetz & Bar Koldanov** · Holon Institute of Technology · 2026
