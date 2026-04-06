"""
Context Management Service
Provides SQLite-backed key/value context storage for n8n workflows.
Supports TTL-based expiry and self-cleaning.

Master Prompt System:
  Stores client digital identities for AI context injection.
  Based on Dan Martell's Master Prompt Architecture - provides
  business context to AI conversations for consistent, high-quality outputs.

API:
  GET    /health
  GET    /context/<workflow>/<session>            - get full context object
  GET    /context/<workflow>/<session>/<key>      - get single key
  POST   /context/<workflow>/<session>            - set keys (body: {key, value, ttl_seconds?} or {data: {...}, ttl_seconds?})
  DELETE /context/<workflow>/<session>            - clear entire session
  DELETE /context/<workflow>/<session>/<key>      - delete single key
  POST   /context/<workflow>/<session>/history    - append to message history
  GET    /context/<workflow>/<session>/history    - get message history
  DELETE /context/<workflow>/<session>/history    - clear message history
  POST   /clean                                   - manual cleanup of expired rows
  GET    /stats                                   - row counts per workflow

Master Prompt API:
  GET    /master-prompt                           - list all clients with master prompts
  GET    /master-prompt/<client>                  - get client's master prompt
  POST   /master-prompt/<client>                  - create/update master prompt
  DELETE /master-prompt/<client>                  - delete master prompt
  GET    /master-prompt/<client>/format            - get formatted for AI injection
"""

import sqlite3
import json
import threading
import time
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify

DB_PATH = "/home/ubuntu/context-service/context.db"
MASTER_PROMPT_DIR = "/home/ubuntu/context-service/master_prompts"
CLEAN_INTERVAL_SECONDS = 300  # auto-clean every 5 minutes
DEFAULT_TTL_SECONDS = 86400   # 24 hours default TTL
MAX_HISTORY_ENTRIES = 50      # cap history per session

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS context (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow    TEXT    NOT NULL,
                session     TEXT    NOT NULL,
                key         TEXT    NOT NULL,
                value       TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                expires_at  TEXT,
                UNIQUE(workflow, session, key)
            );

            CREATE INDEX IF NOT EXISTS idx_ctx_lookup   ON context(workflow, session, key);
            CREATE INDEX IF NOT EXISTS idx_ctx_expires  ON context(expires_at)
                WHERE expires_at IS NOT NULL;

            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow    TEXT    NOT NULL,
                session     TEXT    NOT NULL,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                expires_at  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_hist_lookup  ON history(workflow, session, created_at);
            CREATE INDEX IF NOT EXISTS idx_hist_expires ON history(expires_at)
                WHERE expires_at IS NOT NULL;

            CREATE TABLE IF NOT EXISTS master_prompt (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client      TEXT    NOT NULL UNIQUE,
                prompt_data TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            CREATE INDEX IF NOT EXISTS idx_mp_client ON master_prompt(client);
        """)
    log.info("Database initialised at %s", DB_PATH)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def clean_expired():
    with get_db() as conn:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")
        ctx_deleted = conn.execute(
            "DELETE FROM context WHERE expires_at IS NOT NULL AND expires_at < ?", (now,)
        ).rowcount
        hist_deleted = conn.execute(
            "DELETE FROM history WHERE expires_at IS NOT NULL AND expires_at < ?", (now,)
        ).rowcount
        if ctx_deleted or hist_deleted:
            log.info("Cleaned %d expired context rows, %d expired history rows", ctx_deleted, hist_deleted)
    return ctx_deleted, hist_deleted


def _auto_clean_loop():
    while True:
        time.sleep(CLEAN_INTERVAL_SECONDS)
        try:
            clean_expired()
        except Exception as e:
            log.error("Auto-clean error: %s", e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def expires_at_from_ttl(ttl_seconds):
    if not ttl_seconds:
        ttl_seconds = DEFAULT_TTL_SECONDS
    ts = time.time() + int(ttl_seconds)
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


def upsert_key(conn, workflow, session, key, value, ttl_seconds=None):
    exp = expires_at_from_ttl(ttl_seconds)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")
    conn.execute("""
        INSERT INTO context (workflow, session, key, value, created_at, updated_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(workflow, session, key) DO UPDATE SET
            value      = excluded.value,
            updated_at = excluded.updated_at,
            expires_at = excluded.expires_at
    """, (workflow, session, key, json.dumps(value), now, now, exp))


# ---------------------------------------------------------------------------
# Routes — health / stats
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/stats")
def stats():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT workflow, COUNT(*) as count FROM context GROUP BY workflow"
        ).fetchall()
        hist = conn.execute(
            "SELECT workflow, COUNT(*) as count FROM history GROUP BY workflow"
        ).fetchall()
    return jsonify({
        "context": {r["workflow"]: r["count"] for r in rows},
        "history": {r["workflow"]: r["count"] for r in hist},
    })


# ---------------------------------------------------------------------------
# Routes — context
# ---------------------------------------------------------------------------

@app.get("/context/<workflow>/<session>")
def get_context(workflow, session):
    clean_expired()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key, value, updated_at, expires_at FROM context WHERE workflow=? AND session=?",
            (workflow, session)
        ).fetchall()
    return jsonify({r["key"]: {
        "value": json.loads(r["value"]),
        "updated_at": r["updated_at"],
        "expires_at": r["expires_at"],
    } for r in rows})


@app.get("/context/<workflow>/<session>/<key>")
def get_key(workflow, session, key):
    clean_expired()
    with get_db() as conn:
        row = conn.execute(
            "SELECT value, updated_at, expires_at FROM context WHERE workflow=? AND session=? AND key=?",
            (workflow, session, key)
        ).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({"value": json.loads(row["value"]), "updated_at": row["updated_at"], "expires_at": row["expires_at"]})


@app.post("/context/<workflow>/<session>")
def set_context(workflow, session):
    body = request.get_json(force=True) or {}
    ttl = body.get("ttl_seconds")

    with get_db() as conn:
        # Bulk set: {"data": {"key1": val1, ...}, "ttl_seconds": N}
        if "data" in body:
            for k, v in body["data"].items():
                upsert_key(conn, workflow, session, k, v, ttl)
        else:
            # Single key: {"key": "k", "value": v, "ttl_seconds": N}
            key = body.get("key")
            value = body.get("value")
            if not key:
                return jsonify({"error": "key required"}), 400
            upsert_key(conn, workflow, session, key, value, ttl)

    clean_expired()
    return jsonify({"ok": True})


@app.delete("/context/<workflow>/<session>")
def delete_session(workflow, session):
    with get_db() as conn:
        n = conn.execute(
            "DELETE FROM context WHERE workflow=? AND session=?", (workflow, session)
        ).rowcount
    return jsonify({"deleted": n})


@app.delete("/context/<workflow>/<session>/<key>")
def delete_key(workflow, session, key):
    with get_db() as conn:
        n = conn.execute(
            "DELETE FROM context WHERE workflow=? AND session=? AND key=?",
            (workflow, session, key)
        ).rowcount
    return jsonify({"deleted": n})


# ---------------------------------------------------------------------------
# Routes — history (conversation turns)
# ---------------------------------------------------------------------------

@app.post("/context/<workflow>/<session>/history")
def append_history(workflow, session):
    body = request.get_json(force=True) or {}
    role = body.get("role", "user")
    content = body.get("content", "")
    ttl = body.get("ttl_seconds", DEFAULT_TTL_SECONDS)
    exp = expires_at_from_ttl(ttl)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")

    with get_db() as conn:
        conn.execute(
            "INSERT INTO history (workflow, session, role, content, created_at, expires_at) VALUES (?,?,?,?,?,?)",
            (workflow, session, role, content, now, exp)
        )
        # Trim to MAX_HISTORY_ENTRIES — keep the most recent
        conn.execute("""
            DELETE FROM history WHERE id IN (
                SELECT id FROM history WHERE workflow=? AND session=?
                ORDER BY created_at DESC
                LIMIT -1 OFFSET ?
            )
        """, (workflow, session, MAX_HISTORY_ENTRIES))

    clean_expired()
    return jsonify({"ok": True})


@app.get("/context/<workflow>/<session>/history")
def get_history(workflow, session):
    limit = request.args.get("limit", 20, type=int)
    clean_expired()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM history WHERE workflow=? AND session=? ORDER BY created_at ASC LIMIT ?",
            (workflow, session, limit)
        ).fetchall()
    return jsonify([{"role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in rows])


@app.delete("/context/<workflow>/<session>/history")
def clear_history(workflow, session):
    with get_db() as conn:
        n = conn.execute(
            "DELETE FROM history WHERE workflow=? AND session=?", (workflow, session)
        ).rowcount
    return jsonify({"deleted": n})


# ---------------------------------------------------------------------------
# Manual clean
# ---------------------------------------------------------------------------

@app.post("/clean")
def manual_clean():
    ctx, hist = clean_expired()
    return jsonify({"context_deleted": ctx, "history_deleted": hist})


# ---------------------------------------------------------------------------
# Routes — master prompt (client digital identity)
# ---------------------------------------------------------------------------

# Master prompt template structure (Dan Martell's framework)
MASTER_PROMPT_TEMPLATE = {
    "business": {
        "model": "",
        "revenue_range": "",
        "pricing": [],
        "stage": ""
    },
    "customer": {
        "target": "",
        "problems_solved": [],
        "icp": "",
        "decision_maker": ""
    },
    "products": {
        "offerings": [],
        "pricing_model": "",
        "delivery_method": ""
    },
    "priorities": {
        "current": [],
        "constraints": [],
        "timeline": ""
    },
    "brand": {
        "voice": "",
        "decision_style": "",
        "values": []
    },
    "tools": {
        "stack": [],
        "workflows": [],
        "integrations": []
    },
    "goals": {
        "short_term": [],
        "long_term": [],
        "kpis": []
    }
}


@app.get("/master-prompt")
def list_master_prompts():
    """List all clients with master prompts."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT client, created_at, updated_at FROM master_prompt ORDER BY updated_at DESC"
        ).fetchall()
    return jsonify([{
        "client": r["client"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"]
    } for r in rows])


@app.get("/master-prompt/<client>")
def get_master_prompt(client):
    """Get a client's master prompt."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT prompt_data, created_at, updated_at FROM master_prompt WHERE client=?",
            (client,)
        ).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "client": client,
        "prompt": json.loads(row["prompt_data"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    })


@app.post("/master-prompt/<client>")
def set_master_prompt(client):
    """Create or update a client's master prompt."""
    body = request.get_json(force=True) or {}
    prompt_data = body.get("prompt", body.get("data", {}))

    # Validate and merge with template
    validated = MASTER_PROMPT_TEMPLATE.copy()
    for section, fields in prompt_data.items():
        if section in validated:
            if isinstance(fields, dict):
                validated[section].update({k: v for k, v in fields.items() if v})
            else:
                validated[section] = fields

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")
    with get_db() as conn:
        conn.execute("""
            INSERT INTO master_prompt (client, prompt_data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(client) DO UPDATE SET
                prompt_data = excluded.prompt_data,
                updated_at = excluded.updated_at
        """, (client, json.dumps(validated), now, now))

    return jsonify({"ok": True, "client": client, "prompt": validated})


@app.delete("/master-prompt/<client>")
def delete_master_prompt(client):
    """Delete a client's master prompt."""
    with get_db() as conn:
        n = conn.execute(
            "DELETE FROM master_prompt WHERE client=?", (client,)
        ).rowcount
    return jsonify({"deleted": n})


@app.get("/master-prompt/<client>/format")
def format_master_prompt(client):
    """Get master prompt formatted for AI context injection.

    Returns a formatted string suitable for pasting into an AI conversation
    as system context, following Dan Martell's Master Prompt Architecture.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT prompt_data FROM master_prompt WHERE client=?",
            (client,)
        ).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404

    data = json.loads(row["prompt_data"])

    # Format as markdown-style context block
    lines = [f"# {client} - Master Prompt Context\n"]
    lines.append("This is the client's digital identity. Use this context for all AI interactions.\n")

    for section, fields in data.items():
        if isinstance(fields, dict) and any(fields.values()):
            lines.append(f"## {section.title()}")
            for key, value in fields.items():
                if value:
                    if isinstance(value, list):
                        lines.append(f"- **{key}**: {', '.join(str(v) for v in value)}")
                    else:
                        lines.append(f"- **{key}**: {value}")
            lines.append("")

    formatted = "\n".join(lines)
    return jsonify({
        "client": client,
        "formatted": formatted,
        "raw": data
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    # Start background cleaner thread
    t = threading.Thread(target=_auto_clean_loop, daemon=True)
    t.start()
    log.info("Context service starting on port 3456")
    app.run(host="127.0.0.1", port=3456, debug=False)
