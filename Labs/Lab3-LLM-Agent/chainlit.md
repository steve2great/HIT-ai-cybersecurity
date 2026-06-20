# Lab 3 - CTI Triage Agent

This is the Chainlit UI for the **Cyber Threat Intelligence Triage Agent**.

The agent is designed to help a SOC analyst rapidly screen what they are
looking at during a triage by exposing three structured lookups:

- `lookup_mitre_technique` - resolve a MITRE ATT&CK technique by its T-ID.
- `check_ioc` - check whether an IP / domain / file hash is in the local
  threat-intel database.
- `get_threat_actor` - return a short profile of a tracked threat actor.

What to pay attention to:

- The agent does not just generate text - every fact it states should come
  from a tool call.
- Tool calls appear in the UI as expandable **Steps** with the JSON input
  and output visible.

Try the following prompts:

- `What is T1110?`
- `Is 185.243.115.84 suspicious?`
- `Tell me about Volt Typhoon.`
- `I see a process invoking ntdsutil - which technique is that?`

The agent is implemented in `app/agent/app.py`. Documentation is in
`app/agent/README.md`.
