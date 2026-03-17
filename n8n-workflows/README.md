# n8n Workflows

This directory contains all n8n workflow definitions exported from the self-hosted n8n instance (Oracle Cloud, port 5678).

## Workflow Index

| File | Name | Status | Trigger |
|------|------|--------|---------|
| [calendar-bot.json](calendar-bot.json) | Calendar Bot | Active | Every 30 min |
| [calendar-notifier.json](calendar-notifier.json) | Calendar Notifier | Active | Every hour |
| [daily-news-brief.json](daily-news-brief.json) | Daily News Brief | Active | Daily 6AM PDT |
| [email-monitor.json](email-monitor.json) | Email Monitor with AI Categorization | Active | Gmail (new unread emails) |
| [test-ai-agent.json](test-ai-agent.json) | Test AI Agent | Inactive | Manual |

---

## Calendar Bot

**File:** `calendar-bot.json`
**Status:** Active
**Trigger:** Schedule — every 30 minutes

Monitors a Discord channel for calendar-related commands, uses Ollama AI to parse intent, and creates or deletes Google Calendar events based on user messages.

**Flow:**
1. Poll Discord channel for new messages
2. Filter out bot messages and already-processed messages
3. Build prompt and send to Ollama for intent parsing
4. Route by intent: `create` or `delete`
5. **Create:** prepare fields → create Google Calendar event → confirm in Discord
6. **Delete:** search Google Calendar → check match count → delete event → confirm in Discord (or reply with multiple matches / not found)

**Credentials required:**
- Discord Bot
- Google Calendar (OAuth2)
- Ollama (local)

---

## Calendar Notifier

**File:** `calendar-notifier.json`
**Status:** Active
**Trigger:** Schedule — every hour

Polls Google Calendar for events starting within the next hour and sends a Discord alert for any not yet notified. Tracks notified event IDs in workflow static data to avoid duplicate alerts.

**Flow:**
1. Fetch upcoming events (next 60 min) from primary Google Calendar
2. Filter out already-notified event IDs
3. Format message: `📅 Starting soon: **{title}** at {time}`
4. Send Discord alert
5. Save event ID to static data

**Credentials required:**
- Google Calendar (OAuth2)
- Discord Bot

---

## Daily News Brief

**File:** `daily-news-brief.json`
**Status:** Active
**Trigger:** Schedule — every 24 hours (6AM PDT); also supports manual trigger

Fetches headlines from BBC, Investing.com, and Crypto news sources, combines them, summarizes via Ollama AI, and posts a formatted brief to Discord.

**Flow:**
1. Fetch articles from BBC, Investing.com, Crypto (parallel HTTP requests)
2. Merge all sources and prepare article list
3. AI Agent (Ollama) summarizes into a news brief
4. Format and send to Discord

**Credentials required:**
- Discord Bot
- Ollama (local)

---

## Email Monitor with AI Categorization

**File:** `email-monitor.json`
**Status:** Active
**Trigger:** Gmail Trigger (polls for new unread emails, marks as read)

Monitors Gmail for new unread emails, uses Ollama AI to categorize and summarize them, and sends relevant notifications to Discord. The original IMAP trigger is disabled but preserved.

**Flow:**
1. Gmail Trigger fires on new unread email
2. Mark email as read (Gmail action node)
3. Prepare email data (extract subject, sender, body)
4. AI Agent (Ollama) categorizes and summarizes the email
5. Process & filter response (applies category rules)
6. Send Discord notification for qualifying emails

**Nodes:**
- `Gmail Trigger` — active trigger (OAuth2, polls unread)
- `Email Trigger (IMAP)` — disabled (preserved for reference)
- `Mark As Read` — marks message as read via Gmail API

**Credentials required:**
- Gmail (OAuth2)
- Discord Bot
- Ollama (local)

---

## Test AI Agent

**File:** `test-ai-agent.json`
**Status:** Inactive (manual only)

Basic AI agent test workflow used for validating Ollama connectivity and agent behavior.

**Flow:**
1. Manual trigger
2. Prepare input
3. AI Agent (Ollama)

**Credentials required:**
- Ollama (local)

---

## Importing a Workflow

To import any of these workflows into n8n:
1. Open n8n editor → **Workflows** → **Import from file**
2. Select the JSON file
3. Re-link credentials (IDs are instance-specific)
4. Activate the workflow
