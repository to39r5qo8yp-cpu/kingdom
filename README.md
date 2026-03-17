# Kingdom

Infrastructure, automation, and AI agent configuration for this server.

## Structure

| Path | Description |
|------|-------------|
| `n8n-workflows/` | n8n workflow JSON exports (5 active workflows) |
| `context-service/` | SQLite-backed context management service (port 3456) + cron manager |

## Services

### n8n (port 5678)
Workflow automation engine. Runs as systemd service `n8n`.

### Context Service (port 3456)
Flask API backed by SQLite at `/home/ubuntu/context-service/context.db`.
Provides key-value context storage and conversation history for bots and workflows.
Runs as systemd service `context-service`. Auto-cleans expired entries every 5 minutes.

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

| Workflow | Status | Trigger | Description |
|----------|--------|---------|-------------|
| Calendar Bot | ✅ Active | Every 30 min | Polls Discord, parses natural language calendar commands via Ollama, routes to Google Calendar create/delete operations |
| Calendar Notifier | ✅ Active | Every hour | Fetches upcoming Google Calendar events, filters already-notified ones, sends Discord alerts |
| Daily News Brief | ✅ Active | 6 AM PDT daily | Fetches BBC/Investing/Crypto RSS feeds, summarises with AI (Ollama), posts to Discord |
| Email Monitor | ✅ Active | Gmail Trigger (unread) | Detects new unread emails via Gmail, marks as read, categorises with AI, sends Discord notification |
| Test AI Agent | ⏸ Inactive | Manual | Development sandbox for testing AI agent chains |

## Context Manager (OpenClaw cron)

Script: `context-service/context-manager.py`
Schedule: every 30 minutes (OpenClaw cron job `context-manager-cron-001`)

Processes OpenClaw session JSONL files, extracts:
- User/channel profiles and last-seen timestamps
- Interaction summaries per scope
- Entity tracking (topics, commands)

Writes live context snapshot to `/home/ubuntu/.openclaw/workspace/CONTEXT.md`.

**Self-cleaning TTLs:**
| Table | TTL |
|-------|-----|
| Recent interactions | 7 days |
| User profiles | 90 days |
| Entities | 30 days |

## n8n Workflow Details

### Calendar Bot
- **File:** `n8n-workflows/calendar-bot.json`
- **Trigger:** Schedule every 30 min
- **Credential:** `googleCalendarOAuth2Api` (ID: gpzlCfoO3Gbg5AZX)
- **Flow:** Fetch Discord messages → Filter new (static lastMessageId) → Skip bots → Build Ollama prompt → Parse intent → Route: create/delete/unclear/ignore → Google Calendar action → Discord confirm

### Calendar Notifier
- **File:** `n8n-workflows/calendar-notifier.json`
- **Trigger:** Schedule every hour
- **Credential:** `googleCalendarOAuth2Api` (ID: gpzlCfoO3Gbg5AZX)
- **Flow:** Get upcoming events → Filter & format (skip already-notified IDs via static data) → Send Discord alert → Save notified ID

### Daily News Brief
- **File:** `n8n-workflows/daily-news-brief.json`
- **Trigger:** Schedule 6 AM PDT + manual trigger
- **Flow:** Fetch BBC + Investing.com + CoinDesk RSS in parallel → Merge → Prepare articles → AI summarise (Ollama) → Format → Post to Discord

### Email Monitor with AI Categorization
- **File:** `n8n-workflows/email-monitor.json`
- **Trigger:** Gmail Trigger (polls unread, marks as read) — IMAP trigger disabled
- **Credential:** `gmailOAuth2` (ID: tfKyJaeALmrkFNaS)
- **Flow:** Gmail Trigger → Mark As Read → Prepare Email Data → AI Agent (Ollama) → Process & Filter Response → Discord Notification

### Test AI Agent
- **File:** `n8n-workflows/test-ai-agent.json`
- **Trigger:** Manual
- **Flow:** Manual Trigger → Prepare Input → AI Agent (Ollama) → (output)
