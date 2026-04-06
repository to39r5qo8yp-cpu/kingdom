# Kingdom

Infrastructure, automation, and AI agent configuration for this server.

## Structure

| Path | Description |
|------|-------------|
| `n8n-workflows/` | n8n workflow JSON exports (17 workflows) |
| `context-service/` | SQLite-backed context management service (port 3456) |
| `infra/` | Systemd service units and OpenClaw cron job configuration |

## Services

### n8n (port 5678)
Workflow automation engine. Currently running via nohup.

```bash
# Status
curl -s http://localhost:5678/healthz

# Restart
pkill -9 -f n8n && sleep 3 && nohup ~/.npm-global/bin/n8n start > ~/.n8n/n8n.log 2>&1 &
```

### Context Service (port 3456)
Flask API backed by SQLite at `/home/ubuntu/context-service/context.db`.
Provides key-value context storage and conversation history for bots and workflows.

**Endpoints:**
- `GET /health`
- `GET /context/<workflow>/<session>` — full context object
- `POST /context/<workflow>/<session>` — set keys `{key, value, ttl_seconds?}` or `{data:{...}, ttl_seconds?}`
- `DELETE /context/<workflow>/<session>` — clear session
- `POST /context/<workflow>/<session>/history` — append `{role, content, ttl_seconds?}`
- `GET /context/<workflow>/<session>/history?limit=N` — get history
- `POST /clean` — manual cleanup
- `GET /stats` — row counts per workflow

Default TTL: 24h. History capped at 50 entries per session.

## n8n Workflows

See `n8n-workflows/README.md` for full list. Key workflows:

| Workflow | Trigger | Description |
|----------|---------|-------------|
| Email Monitor AI | Manual/Trigger | Email triage with AI categorization |
| News Daily Brief | Schedule 6 AM | RSS feeds + AI summary → Discord |
| Health System | Schedule | System health monitoring |
| Trading Quant Core | Manual | Quantitative analysis |
| Trading Signals Enhanced | Schedule | Trading signal generation |

## Infrastructure

Configuration files tracked in `infra/`:

| File | Description |
|------|-------------|
| `n8n.service` | systemd unit for n8n (not currently installed) |
| `context-service.service` | systemd unit for context service (not currently installed) |
| `openclaw-cron-jobs.json` | OpenClaw cron job definitions |

## Context Manager (OpenClaw cron)

Script: `context-service/context-manager.py`
Schedule: every 30 minutes (OpenClaw cron job `context-manager-cron-001`)

Processes OpenClaw session JSONL files, extracts:
- User/channel profiles and last-seen timestamps
- Interaction summaries per scope
- Entity tracking (topics, commands)

Writes live context snapshot to `/home/ubuntu/.openclaw/workspace/CONTEXT.md`.

## Reference

For full system reference, see the OpenClaw workspace:
- `~/.openclaw/workspace/SYSTEM.md` — Comprehensive ecosystem reference
- `~/.openclaw/workspace/TOOLS.md` — Service URLs, channels, credentials

---

*Last updated: April 2026*