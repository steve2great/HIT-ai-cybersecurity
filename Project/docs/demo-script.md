# 2-5 minute demo video script

Per Slava's email (2025-05-22): the project requires a short video (2-5 min)
posted to YouTube, with the link placed in the GitHub README. This script
lands at ~3 minutes 30 seconds at natural pace - comfortably inside the
window.

---

## 0:00 - 0:25  Hook

> "Hi, we're Stav Hefetz and Bar Koldanov. This is SOC-Copilot - our Type-2
> integrated project for the Introduction to AI for Cybersecurity course.
>
> SOC analysts drown in alerts. The few that matter look identical to the
> noise. SOC-Copilot detects anomalous authentication events, maps each
> one to MITRE ATT&CK, and explains it in plain English to a junior
> analyst - without hallucinating, because the LLM never sees raw threat
> intelligence."

[Show the GitHub README briefly.]

---

## 0:25 - 1:00  Architecture (talking head + diagram)

> "Three components. An Isolation Forest detector trained on benign-only
> traffic. A deterministic rule-based mapper that assigns the MITRE
> technique ID. And an LLM agent that turns the mapper's structured
> output into a triage paragraph. The LLM is *constrained by
> architecture*, not just by its prompt - it has no way to invent a
> technique ID because it never sees the threat-intel catalogue."

[Show `docs/architecture.md` diagram briefly.]

---

## 1:00 - 2:30  Live demo (the centerpiece)

> "Let me show it running."

[Switch to `localhost:8000`. Click ▶ **Replay incident**.]

> "Five events are streaming through the pipeline. The first three are
> benign - alice, bob, carol logging in from the office in business
> hours. The detector returns 'OK' for each, no LLM call.
>
> Fourth event: 42 failed SSH logins against `admin` from
> `185.243.115.84` at 02:31. The detector flags it. The mapper labels it
> T1110.001 Password Guessing with high confidence and three rationale
> strings. The LLM produces the analyst-facing paragraph.
>
> Fifth event: a *successful* VPN login from alice on a new external IP
> at 03:14. This is the hard one - successful logins from known users
> aren't unconditionally suspicious. The detector still flags it, the
> mapper labels it T1078 Valid Accounts with medium confidence, and the
> LLM explicitly tells the analyst this could be legitimate (hotel WiFi)
> or stolen-credential abuse - and to verify by callback."

[Click open one of the Step blocks to show the structured tool output
visibly.]

---

## 2:30 - 3:10  Results + honesty

> "Headline numbers: ROC-AUC 0.996, recall 0.95. Per-technique recall is
> 100 % on the two brute-force variants and 64 % on valid-account abuse -
> the documented hard case. I also ran an *evasive* scenario where the
> attacker mimics every benign feature except the unknown IP - detection
> drops to 0 %. That's the limit of per-event detection, and it's
> exactly the Volt Typhoon SOHO-router playbook from Lab 1. Future work
> is cross-event correlation."

[Show `notebooks/03_security_tests.ipynb` summary table.]

---

## 3:10 - 3:30  Wrap

> "Every decision the system makes is logged to `traffic_logs.log` as
> JSONL for audit. Full code on my GitHub. Thanks for watching."

[End screen with repo URL.]

---

## Recording checklist

- [ ] Restart `docker compose up` ~30 seconds before recording so the LLM is warm.
- [ ] Pre-open browser tabs: GitHub README, architecture diagram, Chainlit UI, notebook 03 summary.
- [ ] Mic check; 1920×1080 screen recorder (OBS / Loom / Windows Game Bar).
- [ ] One dry-run of the Replay incident to confirm the LLM responds in < 5 s/alert.
- [ ] Upload to YouTube as **Unlisted** so only people with the link can view it.
- [ ] Paste the YouTube link into the top-level `README.md` and `Project/README.md` under a "Demo video" section, AND under the QR code on the poster.
