#!/bin/bash
# Enforce America/Los_Angeles timezone on all n8n schedule triggers.
# Runs as ExecStartPost in systemd and can be called manually.
# Waits for n8n to be healthy, then validates and fixes all schedule triggers.

N8N_URL="http://localhost:5678"
N8N_API_KEY="${N8N_API_KEY:-n8n_api_381366c32d1f1b6787c0e8ce917ffd817bb32c6e4687a2ba37a7a6c2ebbe2d2a}"
EXPECTED_TZ="America/Los_Angeles"
LOG="/home/ubuntu/.n8n/timezone-enforce.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

# Wait for n8n to be healthy (up to 90s)
for i in $(seq 1 18); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$N8N_URL/healthz" 2>/dev/null)
    [ "$STATUS" = "200" ] && break
    sleep 5
done

if [ "$STATUS" != "200" ]; then
    log "ERROR: n8n not healthy after 90s, skipping timezone enforcement"
    exit 1
fi

log "Starting timezone enforcement check..."

# Get all workflow IDs
WORKFLOW_IDS=$(curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_URL/api/v1/workflows?limit=100" 2>/dev/null \
    | python3 -c "import sys,json; [print(w['id']) for w in json.load(sys.stdin).get('data',[])]" 2>/dev/null)

FIXED=0
CHECKED=0

for WF_ID in $WORKFLOW_IDS; do
    # Fetch workflow and check/fix timezone on schedule triggers
    RESULT=$(python3 << PYEOF
import json, sys, subprocess

wf_id = "$WF_ID"
api_key = "$N8N_API_KEY"
expected_tz = "$EXPECTED_TZ"

resp = subprocess.run(
    ['curl', '-s', '-H', f'X-N8N-API-KEY: {api_key}',
     f'$N8N_URL/api/v1/workflows/{wf_id}'],
    capture_output=True, text=True
)

try:
    wf = json.loads(resp.stdout)
except:
    print(f"SKIP:{wf_id}:could not parse")
    sys.exit(0)

if 'nodes' not in wf:
    print(f"SKIP:{wf_id}:no nodes (API error)")
    sys.exit(0)

needs_fix = False
wf_name = wf.get('name', wf_id)

for node in wf['nodes']:
    if 'scheduleTrigger' not in node.get('type', ''):
        continue

    params = node.get('parameters', {})
    intervals = params.get('rule', {}).get('interval', [])

    # Only check nodes with cron expressions (not interval-based)
    has_cron = any(i.get('field') == 'cronExpression' for i in intervals)
    if not has_cron:
        continue

    current_tz = params.get('options', {}).get('timezone', '')
    if current_tz != expected_tz:
        if 'options' not in params:
            params['options'] = {}
        params['options']['timezone'] = expected_tz
        needs_fix = True
        print(f"FIX:{wf_id}:{wf_name}:{node['name']}:{current_tz or 'NONE'}->{expected_tz}")

if needs_fix:
    payload = {
        'name': wf['name'],
        'nodes': wf['nodes'],
        'connections': wf['connections'],
        'settings': wf.get('settings', {}),
    }
    update = subprocess.run(
        ['curl', '-s', '-X', 'PUT',
         '-H', f'X-N8N-API-KEY: {api_key}',
         '-H', 'Content-Type: application/json',
         '-d', json.dumps(payload),
         f'$N8N_URL/api/v1/workflows/{wf_id}'],
        capture_output=True, text=True
    )
    try:
        result = json.loads(update.stdout)
        if result.get('id'):
            print(f"FIXED:{wf_id}")
        else:
            print(f"FAIL:{wf_id}:{update.stdout[:100]}")
    except:
        print(f"FAIL:{wf_id}:bad response")
else:
    print(f"OK:{wf_id}")
PYEOF
    )

    while IFS= read -r line; do
        case "$line" in
            FIX:*)  log "$line"; FIXED=$((FIXED + 1)) ;;
            FIXED:*) log "$line" ;;
            FAIL:*) log "ERROR: $line" ;;
            OK:*) ;;
            SKIP:*) ;;
        esac
        CHECKED=$((CHECKED + 1))
    done <<< "$RESULT"
done

if [ "$FIXED" -gt 0 ]; then
    log "Enforcement complete: fixed $FIXED schedule trigger(s) across $CHECKED workflow(s)"
else
    log "All schedule triggers OK ($CHECKED workflow(s) checked)"
fi
