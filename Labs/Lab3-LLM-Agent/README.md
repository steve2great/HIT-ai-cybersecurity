# Lab 3 - CTI Triage Agent

**Student:** Stav Hefetz
**Framework:** [AG2](https://docs.ag2.ai/) (`ConversableAgent`) + [Chainlit](https://docs.chainlit.io/)
**LLM provider:** Groq (`qwen/qwen3-32b`) - any OpenAI-compatible service works

## What this lab demonstrates

A single LLM agent that helps a SOC analyst do **CTI triage**:

| Question the analyst asks | Tool the agent calls |
|---|---|
| *"What is T1110?"* / *"I see ntdsutil in logs"* | `lookup_mitre_technique` |
| *"Is 185.243.115.84 suspicious?"* | `check_ioc` |
| *"Tell me about Volt Typhoon"* | `get_threat_actor` |

The agent must call a tool to answer factual questions - the system prompt
explicitly forbids hallucinated ATT&CK / IOC / actor data. Every fact is
traceable in the Chainlit UI as an expandable Step.

**Full agent spec:** [`app/agent/README.md`](app/agent/README.md)
**Agent code:** [`app/agent/app.py`](app/agent/app.py)

---

## How to run

### 1. Configure the API key

Create a `.env` file in this directory:

```text
API_KEY=gsk_yourGroqKeyHere
```

Get a free Groq key at https://console.groq.com/keys.
To use a different OpenAI-compatible provider, edit `API_BASE_URL` and
`MODEL` in `compose.yml`.

### 2. Build the image

```bash
docker build -t cybersec-agent-chainlit-lab3 .
```

### 3. Start Chainlit

```bash
docker compose up
```

Open http://localhost:8000 and start chatting. Tool calls appear as
expandable **Steps** below each agent message.

### 4. Iterate

After editing `app/agent/app.py`, restart the container:

```bash
docker compose down
docker compose up
```

You don't need to rebuild unless you change `pyproject.toml`.

---

## Files

```
.
├── Dockerfile               # builds the Chainlit + AG2 image (uv-based)
├── compose.yml              # dev-mode mount of source code into /app
├── pyproject.toml           # ag2[openai] + chainlit
├── uv.lock                  # frozen dependency graph
├── chainlit.md              # welcome screen shown in the Chainlit UI
└── app/
    └── agent/
        ├── app.py           # the CTI triage agent
        └── README.md        # required agent documentation
```
