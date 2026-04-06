# n8n Workflows

Production n8n workflows exported from the running instance.

## Export Command

```bash
curl -s "http://localhost:5678/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for w in data['data']:
    filename = w['name'].lower().replace(' ', '-').replace('/', '-') + '.json'
    with open(filename, 'w') as f:
        json.dump(w, f, indent=2)
"
```

## Workflows (17 total)

| Workflow | File | Status | Purpose |
|----------|------|--------|---------|
| Email Monitor AI | email-monitor-ai.json | Active | Email triage + AI categorization |
| News Daily Brief | news-daily-brief.json | Active | Daily news aggregation (RSS + AI) |
| News AI Brief | news-ai-brief.json | Active | News brief variant |
| News AI Brief v2 | news-ai-brief-v2.json | Active | News brief variant |
| Health System | health-system.json | Active | System health monitoring |
| Utility Error Handler | utility-error-handler.json | Active | Global error handling |
| Trading Quant Core | trading-quant-core.json | Active | Quantitative analysis |
| Trading Quant Learning | trading-quant-learning.json | Active | ML parameter optimization |
| Trading Monitor Portfolio | trading-monitor-portfolio.json | Active | Portfolio analysis |
| Trading Signals Enhanced | trading-signals-enhanced.json | Active | Trading signal generation |
| Job Search | job-search.json | Active | Job listing scraper |
| Memory Sync | memory-sync.json | Active | Memory synchronization |
| Memory Notify | memory-notify.json | Active | Memory notifications |
| Memory Notify v2 | memory-notify-v2.json | Active | Memory notifications v2 |
| Memory Consolidator | memory-consolidator.json | Active | Memory consolidation |
| Notification File DM | notification-file-dm.json | Active | File notifications via DM |
| Test Discord | test-discord.json | Dev | Discord testing |

## Categories

### Trading/Quant (4)
- trading-quant-core.json
- trading-quant-learning.json
- trading-monitor-portfolio.json
- trading-signals-enhanced.json

### News/Media (3)
- news-daily-brief.json
- news-ai-brief.json
- news-ai-brief-v2.json

### Memory/State (4)
- memory-sync.json
- memory-notify.json
- memory-notify-v2.json
- memory-consolidator.json

### Communication (2)
- email-monitor-ai.json
- notification-file-dm.json

### Infrastructure (2)
- health-system.json
- utility-error-handler.json

### Utility/Dev (2)
- job-search.json
- test-discord.json

## Re-importing

To re-import a workflow to n8n:

```bash
curl -X POST "http://localhost:5678/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @workflow-name.json
```

---

*Last updated: April 2026*