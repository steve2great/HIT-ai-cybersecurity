# Problem statement & goals (Stage 2)

## 2.1 The problem

A Security Operations Centre (SOC) is the team responsible for monitoring an
organisation's network and identity infrastructure for malicious activity.
SOC analysts are typically organised into three tiers:

- **Tier 1** - triage incoming alerts, decide which are real
- **Tier 2** - investigate real alerts, contain incidents
- **Tier 3** - threat hunting, red-team / purple-team work

Tier 1 is the bottleneck. Two specific pain points motivate this project:

1. **Alert volume.** A typical mid-size enterprise SIEM emits 10⁴-10⁵ alerts
   per day. Most are false positives. Analysts develop *alert fatigue* -
   they begin to dismiss alerts that look noisy without investigating.
2. **Context gap.** A raw alert (e.g. `event_id=4625, count=12,
   src_ip=185.243.115.84, user=admin`) tells the analyst *what* happened in
   the log but not *what it means* (T1110.003 password spraying) or *what to
   do about it* (block the source IP, rotate the credential, check for
   lateral movement). Translating from raw telemetry to MITRE ATT&CK and
   then to a response action is exactly the skill that Tier 1 lacks.

The combination of (1) and (2) means that genuine intrusions are dismissed
as noise - a documented failure mode in major breaches such as the 2013
Target breach (alerts fired, analysts dismissed them).

## 2.2 Threat model

| Element | Choice |
|---|---|
| **In scope** | Detection of anomalous authentication / login events on an enterprise estate (SSH, Windows, VPN). |
| **Out of scope** | Network-payload inspection (we do not parse packets), endpoint malware analysis, email phishing content. |
| **Adversary profile** | External attacker who has obtained or wishes to obtain valid credentials. Capabilities include brute force (T1110), credential stuffing (T1110.004), and use of valid stolen accounts (T1078). The adversary does **not** have the ability to tamper with the SOC's own logs. |
| **Trust boundary** | The detection system is trusted. The log source (the company's auth events) is *semi-trusted* - events may be benign or malicious, but the event metadata itself (timestamps, source IPs) is assumed accurate. |
| **Safety considerations** | The LLM in the triage agent must never invent technique IDs, IOCs or actor attributions. All factual claims must be traceable to a deterministic mapper output. This is enforced by both the system prompt and the architecture (the LLM only ever sees structured output, never raw threat-intel feeds). |

## 2.3 Goal

Build a working prototype that, end to end:

- ingests a stream of authentication events,
- detects the anomalous ones with an unsupervised model trained on benign traffic,
- maps each anomaly deterministically to MITRE ATT&CK,
- produces a natural-language explanation grounded in the mapper output,
- logs every decision to a persistent audit trail.

The prototype is evaluated on three axes:

1. **Detection quality** - precision / recall / F1 on a held-out test set
   that contains injected attack scenarios (T1110, T1078, T1003 patterns).
2. **Mapping correctness** - does the deterministic mapper assign the right
   technique to each injected scenario?
3. **Explanation faithfulness** - does the LLM's explanation contain only
   facts that are present in the mapper output? (Manual review on a sample.)

## 2.4 Non-goals

- Real-time stream processing at production scale. The pipeline is built to
  run on a single laptop with a CSV input.
- A production-grade threat-intel feed. The MITRE catalogue and IOC list
  used in the agent's tools is a hand-curated snapshot, identical in spirit
  to the Lab 3 CTI agent.
- Beating a state-of-the-art SIEM. The baseline is "what a Tier-1 analyst
  could do alone in 30 seconds per alert." If the system beats *that*, it
  is useful.
