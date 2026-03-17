# Kingdom

Infrastructure, automations, and configuration for the home server stack.

## Contents

| Directory | Description |
|-----------|-------------|
| [n8n-workflows/](n8n-workflows/) | n8n automation workflows (exported JSON + docs) |

## Stack

- **n8n** — self-hosted workflow automation (Oracle Cloud VPS, port 5678)
- **Ollama** — local LLM inference (runs on-device)
- **Discord** — notification and command interface for all workflows
- **Google Calendar / Gmail** — calendar management and email monitoring (OAuth2)
