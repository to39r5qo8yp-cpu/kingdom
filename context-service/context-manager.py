#!/usr/bin/env python3
"""
OpenClawBot Context Manager
----------------------------
Processes conversation sessions, extracts context, and maintains
openclaw.db with user profiles, interaction history, and entity tracking.

Runs as a cron task every 30 minutes. Writes CONTEXT.md to the workspace
so the bot has live context injected at session start.

Self-cleaning: entries expire automatically via expires_at TTL.
"""

import sqlite3
import json
import os
import ast
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
OPENCLAW_DIR   = Path.home() / ".openclaw"
DB_PATH        = OPENCLAW_DIR / "openclaw.db"
SESSIONS_DIR   = OPENCLAW_DIR / "agents" / "main" / "sessions"
SESSIONS_INDEX = SESSIONS_DIR / "sessions.json"
WORKSPACE_DIR  = OPENCLAW_DIR / "workspace"
CONTEXT_MD     = WORKSPACE_DIR / "CONTEXT.md"

# ── TTLs ─────────────────────────────────────────────────────────────────────
TTL_RECENT_INTERACTION = timedelta(days=7)
TTL_USER_PROFILE       = timedelta(days=90)
TTL_ENTITY             = timedelta(days=30)
TTL_CRON_LOG           = timedelta(days=3)
MAX_INTERACTIONS_PER_SCOPE = 20  # keep latest N per user/channel


# ── Database ─────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions_processed (
                session_id       TEXT PRIMARY KEY,
                last_line        INTEGER DEFAULT 0,
                scope            TEXT,
                scope_id         TEXT,
                processed_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS context (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                scope       TEXT    NOT NULL,
                scope_id    TEXT    NOT NULL,
                key         TEXT    NOT NULL,
                value       TEXT    NOT NULL,
                source      TEXT,
                created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                expires_at  TEXT,
                UNIQUE(scope, scope_id, key)
            );

            CREATE INDEX IF NOT EXISTS idx_ctx_lookup  ON context(scope, scope_id);
            CREATE INDEX IF NOT EXISTS idx_ctx_expires ON context(expires_at)
                WHERE expires_at IS NOT NULL;

            CREATE TABLE IF NOT EXISTS interaction_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                scope       TEXT    NOT NULL,
                scope_id    TEXT    NOT NULL,
                summary     TEXT    NOT NULL,
                msg_count   INTEGER DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                expires_at  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_ilog_scope   ON interaction_log(scope, scope_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_ilog_expires ON interaction_log(expires_at)
                WHERE expires_at IS NOT NULL;

            CREATE TABLE IF NOT EXISTS entities (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_id        TEXT    NOT NULL,
                entity_type     TEXT    NOT NULL,
                name            TEXT    NOT NULL,
                metadata        TEXT,
                mention_count   INTEGER DEFAULT 1,
                first_seen      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                last_seen       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                expires_at      TEXT,
                UNIQUE(scope_id, entity_type, name)
            );

            CREATE INDEX IF NOT EXISTS idx_ent_scope   ON entities(scope_id);
            CREATE INDEX IF NOT EXISTS idx_ent_expires ON entities(expires_at)
                WHERE expires_at IS NOT NULL;
        """)


# ── Self-cleaning ─────────────────────────────────────────────────────────────

def clean_expired(conn):
    now = _now()
    ctx = conn.execute("DELETE FROM context WHERE expires_at IS NOT NULL AND expires_at < ?", (now,)).rowcount
    log = conn.execute("DELETE FROM interaction_log WHERE expires_at IS NOT NULL AND expires_at < ?", (now,)).rowcount
    ent = conn.execute("DELETE FROM entities WHERE expires_at IS NOT NULL AND expires_at < ?", (now,)).rowcount

    # Trim interaction log to MAX per scope
    conn.execute("""
        DELETE FROM interaction_log WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY scope, scope_id ORDER BY created_at DESC) rn
                FROM interaction_log
            ) WHERE rn > ?
        )
    """, (MAX_INTERACTIONS_PER_SCOPE,))

    total = ctx + log + ent
    if total:
        print(f"[clean] Removed {ctx} context, {log} interactions, {ent} entities (expired)")
    return total


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires(delta: timedelta):
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Session index parsing ──────────────────────────────────────────────────────

def load_session_index():
    """Return {session_key: {sessionId, scope, scope_id, display_name}}"""
    if not SESSIONS_INDEX.exists():
        return {}
    with open(SESSIONS_INDEX) as f:
        raw = json.load(f)

    sessions = {}
    for key, val in raw.items():
        try:
            meta = ast.literal_eval(val) if isinstance(val, str) else val
        except Exception:
            continue
        sid = meta.get("sessionId")
        if not sid:
            continue

        # Parse key: agent:main:{scope_type}:...
        parts = key.split(":")
        if len(parts) < 3:
            continue
        scope_type = parts[2] if len(parts) > 2 else "unknown"

        # Normalise scope and scope_id
        if scope_type == "discord":
            surface = parts[3] if len(parts) > 3 else "unknown"
            scope_id = ":".join(parts[4:]) if len(parts) > 4 else "unknown"
            if surface == "direct":
                scope = "discord_user"
            elif surface == "channel":
                scope = "discord_channel"
            else:
                scope = "discord"
        elif scope_type == "cron":
            scope = "cron"
            # key format: agent:main:cron:{jobId}:run:{sessionId}
            # Use jobId only as scope_id so all runs of same job aggregate
            scope_id = parts[3] if len(parts) > 3 else "unknown"
        else:
            scope = scope_type
            scope_id = ":".join(parts[3:]) if len(parts) > 3 else "main"

        # Display name from origin if available
        origin = meta.get("origin", {})
        display = origin.get("label") or meta.get("displayName") or scope_id

        sessions[sid] = {
            "session_id": sid,
            "scope": scope,
            "scope_id": scope_id,
            "display_name": display,
        }
    return sessions


# ── Session processing ────────────────────────────────────────────────────────

def extract_text(content):
    """Flatten n8n/openclaw message content to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                parts.append(c.get("text", ""))
        return " ".join(parts)
    return str(content)


def process_session(conn, session_meta):
    sid = session_meta["session_id"]
    scope = session_meta["scope"]
    scope_id = session_meta["scope_id"]
    display = session_meta["display_name"]

    session_file = SESSIONS_DIR / f"{sid}.jsonl"
    if not session_file.exists():
        return

    # Get last processed line
    row = conn.execute("SELECT last_line FROM sessions_processed WHERE session_id = ?", (sid,)).fetchone()
    last_line = row["last_line"] if row else 0

    lines = session_file.read_text(errors="replace").splitlines()
    new_lines = lines[last_line:]
    if not new_lines:
        return

    messages = []
    for line in new_lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "message":
            continue
        msg = event.get("message", {})
        role = msg.get("role", "")
        content = extract_text(msg.get("content", ""))
        if not content or not role:
            continue
        # Skip system-like injections (very long, starts with [cron:...])
        if content.startswith("[cron:") or content.startswith("System:"):
            continue
        messages.append({"role": role, "content": content})

    if not messages:
        # Still mark as processed
        upsert_session_marker(conn, sid, scope, scope_id, len(lines))
        return

    # Build short summary of this batch
    user_msgs = [m["content"][:200] for m in messages if m["role"] == "user"]
    assistant_msgs = [m["content"][:200] for m in messages if m["role"] == "assistant"]

    if user_msgs:
        summary_parts = []
        summary_parts.append("User: " + " | ".join(user_msgs[:3]))
        if assistant_msgs:
            summary_parts.append("Bot: " + assistant_msgs[-1][:150])
        summary = " → ".join(summary_parts)
    else:
        summary = "Bot activity: " + " | ".join(assistant_msgs[:2])

    # Log interaction
    conn.execute("""
        INSERT INTO interaction_log (session_id, scope, scope_id, summary, msg_count, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (sid, scope, scope_id, summary[:500], len(messages), _expires(TTL_RECENT_INTERACTION)))

    # Update last_seen for user/channel
    upsert_context(conn, scope, scope_id, "display_name", display, sid, TTL_USER_PROFILE)
    upsert_context(conn, scope, scope_id, "last_seen", _now(), sid, TTL_USER_PROFILE)

    # Extract entities from user messages
    for msg in messages:
        if msg["role"] == "user":
            extract_and_store_entities(conn, scope_id, msg["content"], sid)

    upsert_session_marker(conn, sid, scope, scope_id, len(lines))
    print(f"[process] {scope}/{scope_id} session={sid[:8]} +{len(messages)} msgs")


def upsert_context(conn, scope, scope_id, key, value, source, ttl):
    now = _now()
    exp = _expires(ttl)
    conn.execute("""
        INSERT INTO context (scope, scope_id, key, value, source, created_at, updated_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(scope, scope_id, key) DO UPDATE SET
            value=excluded.value, updated_at=excluded.updated_at, expires_at=excluded.expires_at
    """, (scope, scope_id, key, json.dumps(value), source, now, now, exp))


def upsert_session_marker(conn, sid, scope, scope_id, line_count):
    now = _now()
    conn.execute("""
        INSERT INTO sessions_processed (session_id, last_line, scope, scope_id, processed_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET last_line=excluded.last_line, processed_at=excluded.processed_at
    """, (sid, line_count, scope, scope_id, now))


# ── Entity extraction ─────────────────────────────────────────────────────────

ENTITY_PATTERNS = [
    ("topic", r"\b(calendar|email|discord|n8n|workflow|cron|ollama|python|script|notion|github|trading|crypto|bitcoin|news)\b"),
    ("command", r"\b(create|delete|update|fix|add|remove|run|start|stop|check|show|list|schedule)\b"),
]


def extract_and_store_entities(conn, scope_id, text, source):
    text_lower = text.lower()
    now = _now()
    exp = _expires(TTL_ENTITY)
    for etype, pattern in ENTITY_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            name = match.group(0)
            conn.execute("""
                INSERT INTO entities (scope_id, entity_type, name, mention_count, first_seen, last_seen, expires_at)
                VALUES (?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(scope_id, entity_type, name) DO UPDATE SET
                    mention_count = mention_count + 1,
                    last_seen = excluded.last_seen,
                    expires_at = excluded.expires_at
            """, (scope_id, etype, name, now, now, exp))


# ── CONTEXT.md generation ─────────────────────────────────────────────────────

CRON_JOB_NAMES = {
    "4269be19-f8a3-4495-9fbf-916e46adde5c": "Daily Auto-Update",
    "8e4fcf1e-cefe-4d72-b368-26f4abfbb0c2": "Daily News Brief",
    "7d949674-a11d-437e-a6a2-5c0f0ed56588": "Instance Health Check",
    "8a9a01ba-36ed-41e4-bb07-25f1b1fcfdcf": "n8n Failure Tracker",
}


def _fmt_ts(ts):
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        if delta.total_seconds() < 3600:
            return f"{int(delta.total_seconds() / 60)}m ago"
        if delta.days == 0:
            return f"{int(delta.total_seconds() / 3600)}h ago"
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return ts


def _scope_label(scope, scope_id):
    if scope == "cron":
        return CRON_JOB_NAMES.get(scope_id, f"cron:{scope_id[:8]}")
    if scope == "discord_user":
        return f"@{scope_id}"
    if scope == "discord_channel":
        return f"#{scope_id}"
    return scope_id


def generate_context_md(conn):
    lines = [
        "# Active Context",
        f"_Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
    ]

    # ── Active scopes (users + channels only, not individual cron runs) ──────
    scope_rows = conn.execute("""
        SELECT scope, scope_id, key, value FROM context
        WHERE key IN ('display_name', 'last_seen')
          AND scope IN ('discord_user', 'discord_channel', 'main')
        ORDER BY scope, scope_id, key
    """).fetchall()

    scope_data = {}
    for r in scope_rows:
        k = (r["scope"], r["scope_id"])
        scope_data.setdefault(k, {})[r["key"]] = json.loads(r["value"])

    if scope_data:
        lines.append("## Known Users & Channels")
        for (scope, sid), data in sorted(scope_data.items()):
            name = data.get("display_name", sid)
            last = _fmt_ts(data.get("last_seen", ""))
            label = _scope_label(scope, sid)
            lines.append(f"- **{scope}** {label} — last active: {last}")
        lines.append("")

    # ── Cron job last runs ────────────────────────────────────────────────────
    cron_rows = conn.execute("""
        SELECT scope_id, MAX(created_at) as last_run, summary
        FROM interaction_log
        WHERE scope = 'cron'
        GROUP BY scope_id
        ORDER BY last_run DESC
    """).fetchall()

    if cron_rows:
        lines.append("## Cron Jobs (last run)")
        for r in cron_rows:
            name = CRON_JOB_NAMES.get(r["scope_id"], f"cron:{r['scope_id'][:8]}")
            ts = _fmt_ts(r["last_run"])
            summary = r["summary"][:120] if r["summary"] else ""
            lines.append(f"- **{name}** ({ts}): {summary}")
        lines.append("")

    # ── Recent user interactions (last 5) ─────────────────────────────────────
    recent = conn.execute("""
        SELECT scope, scope_id, summary, msg_count, created_at
        FROM interaction_log
        WHERE scope IN ('discord_user', 'discord_channel', 'main')
        ORDER BY created_at DESC
        LIMIT 5
    """).fetchall()

    if recent:
        lines.append("## Recent User Interactions")
        for r in recent:
            ts = _fmt_ts(r["created_at"])
            label = _scope_label(r["scope"], r["scope_id"])
            summary = r["summary"][:150] if r["summary"] else ""
            lines.append(f"- `{ts}` {label}: {summary}")
        lines.append("")

    # ── Frequent topics per user/channel ─────────────────────────────────────
    entities = conn.execute("""
        SELECT e.scope_id, e.entity_type, e.name, e.mention_count, c.scope
        FROM entities e
        LEFT JOIN context c ON c.scope_id = e.scope_id AND c.key = 'display_name'
        WHERE e.entity_type = 'topic'
        ORDER BY e.scope_id, e.mention_count DESC
    """).fetchall()

    by_scope = {}
    for e in entities:
        by_scope.setdefault(e["scope_id"], []).append(e)

    if by_scope:
        lines.append("## Frequent Topics")
        for scope_id, ents in by_scope.items():
            topics = [f"`{e['name']}` ({e['mention_count']}x)" for e in ents[:6]]
            if topics:
                lines.append(f"- **{scope_id}**: {', '.join(topics)}")
        lines.append("")

    # DB stats
    ctx_count  = conn.execute("SELECT COUNT(*) FROM context").fetchone()[0]
    log_count  = conn.execute("SELECT COUNT(*) FROM interaction_log").fetchone()[0]
    ent_count  = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    sess_count = conn.execute("SELECT COUNT(*) FROM sessions_processed").fetchone()[0]
    lines.append(f"_Context DB: {ctx_count} context rows · {log_count} interactions · {ent_count} entities · {sess_count} sessions tracked_")

    CONTEXT_MD.write_text("\n".join(lines) + "\n")
    print(f"[context] Written CONTEXT.md ({len(lines)} lines)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[context-manager] Starting — {_now()}")
    init_db()

    sessions = load_session_index()
    print(f"[context-manager] Found {len(sessions)} sessions in index")

    with get_db() as conn:
        clean_expired(conn)

        for sid, meta in sessions.items():
            try:
                process_session(conn, meta)
            except Exception as e:
                print(f"[error] session {sid[:8]}: {e}")

    with get_db() as conn:
        generate_context_md(conn)

    print(f"[context-manager] Done — {_now()}")


if __name__ == "__main__":
    main()
