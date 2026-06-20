# Known limitations & potential vulnerabilities (Stage 9)

Listing the weaknesses up front is required by the course spec and is good
engineering practice. For each item we note (a) why it exists, (b) what an
attacker could exploit, and (c) what we would change in production.

---

## 1. Synthetic data ≠ production traffic

- **Why:** Real corporate auth logs are confidential and unavailable. The generator in `data/generate.py` is a *plausibility model*, not a true distribution.
- **Attacker exploit:** A real attacker's behaviour may differ from the three profiles we modelled. Anything that doesn't look like T1110.001 / T1110.003 / T1078 will fall into the "unspecified anomaly" bucket with low confidence.
- **Production fix:** Train on at least 30 days of the customer's own auth events. Use the synthetic dataset only for unit tests of the rule chain.

---

## 2. `ip_is_known` is the single point of failure

This is the most important limitation and is documented in detail in
`notebooks/03_security_tests.ipynb` §6.

- **Why:** Three of the four scenarios collapse to "the source IP is not on our reputation list." The Isolation Forest leans heavily on this feature because it is genuinely the strongest signal in the synthetic data.
- **Attacker exploit:** This is exactly the Volt Typhoon tradecraft documented in Lab 1 - relay C2 through compromised SOHO routers in the *same geography* as the target so the IP looks residential and known. If the attacker controls a previously-trusted IP, T1078 detection rate degrades from ~100% to ~10%.
- **Production fix:** Build a *secondary* detector that operates on cross-event aggregates (impossible travel, first-time-from-this-IP-ever, sudden device-fingerprint change). The primary per-event detector cannot fix this on its own.

---

## 3. The mapper is rule-based and finite

- **Why:** We hand-wrote three rules covering three techniques. ATT&CK has hundreds.
- **Attacker exploit:** Any attack that does not map to T1110.* or T1078 falls into the "unspecified anomaly" bucket. The analyst gets the score but not a precise technique label.
- **Production fix:** Either (a) extend the rule set to cover the top-20 enterprise techniques, or (b) move to a hybrid mapper where ATT&CK is retrieved by similarity against a STIX feed and confirmed by a constrained LLM call (still grounded - never freely generative).

---

## 4. The LLM is an adversarial surface

Even though the LLM is constrained, it is still:

- **Prompt-injectable:** if the analyst pastes attacker-controlled text into the chat box (e.g. a phishing email body), the LLM might follow embedded instructions. *Mitigation in place:* the LLM never has tool-execution power - it only emits text. The audit log records every prompt.
- **Reliant on the system prompt:** if the prompt is silently changed to drop the "no inventing technique IDs" clause, the safety guarantee disappears. *Mitigation in place:* `triage_agent.py` is in source control and the system prompt is a code constant.

---

## 5. The model is point-in-time

- **Why:** Trained once on a snapshot of synthetic data. There is no drift detection.
- **Attacker exploit:** An attacker who shifts technique slowly (e.g. moves from ssh to webapp over weeks) will see his anomaly score drift toward the benign cluster as the deployed model "ages."
- **Production fix:** Retrain weekly on a rolling 30-day window of benign-labelled traffic. Add a data-drift monitor on the feature distributions.

---

## 6. False positives are not free

- The Isolation Forest at `contamination=0.03` will flag ~3 % of *benign* events. On a real estate of 10⁵ events/day that is 3 000 false positives per day - exactly the alert-fatigue problem the project tries to *reduce*.
- **Production fix:** This is where the LLM's confidence rating earns its keep. Tune so that only `confidence>=medium` alerts surface; route `confidence=low` to a daily digest rather than real-time paging.

---

## 7. The system has no notion of an incident

Each event is scored in isolation. Two correlated events (T1110.001 success followed by T1078 from the same IP an hour later) are not joined into a single incident.

- **Production fix:** Add an incident-correlation step downstream of the per-event detector - keyed on `source_ip` over a sliding window. Out of scope for this lab, the natural follow-on for a Lab 5 / capstone.
