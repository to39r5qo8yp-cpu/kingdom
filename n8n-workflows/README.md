# n8n Workflows

Production n8n workflows for the AI consulting business.

## Directory Structure

```
n8n-workflows/
├── README.md                    # This file
├── enforce-timezones.sh         # Timezone enforcement script
├── trigger-workflow.sh          # Manual workflow trigger
├── email-monitor.json           # Email triage + AI categorization
├── daily-news-brief.json        # Daily news aggregation
├── health-check.json            # System health monitoring
├── error-handler-global.json    # Global error handling
├── trading-signals.json         # Trading signal generation
├── trading-monitor.json         # Portfolio analysis
├── quant-analyst-core.json      # Quantitative analysis
├── quant-learning.json          # ML parameter optimization
├── job-search.json              # Job listing scraper
└── test-discord.json            # Discord testing
```

## Workflow Categories

### Production Workflows (Active)

| Workflow | Purpose | Status | Reusable For |
|----------|---------|--------|--------------|
| email-monitor.json | Email triage + AI categorization | Active | **High - Email Triage template** |
| daily-news-brief.json | Daily news aggregation | Active | Medium - Reporting template |
| health-check.json | System health monitoring | Active | Low - Internal use |
| error-handler-global.json | Global error handling | Active | **High - Every project needs this** |
| trading-signals.json | Trading signal generation | Active | Low - Niche |
| trading-monitor.json | Portfolio analysis | Active | Low - Niche |
| quant-analyst-core.json | Quantitative analysis | Active | Low - Niche |
| quant-learning.json | ML parameter optimization | Active | Low - Niche |

### Development/Test Workflows

| Workflow | Purpose | Status |
|----------|---------|--------|
| test-discord.json | Discord testing | Development |
| job-search.json | Job listing scraper | Inactive |

## Template Extraction

Production-ready templates are extracted to `ai-consulting/templates/workflows/`:

| Template | Source | Status |
|----------|--------|--------|
| email-triage-template.json | email-monitor.json | Ready |
| error-handler-template.json | error-handler-global.json | TODO |
| daily-brief-template.json | daily-news-brief.json | TODO |
| webhook-integration-template.json | trading-signals.json | TODO |

## Adding New Workflows

1. Design workflow in n8n interface
2. Test thoroughly
3. Export to JSON file:
   ```bash
   # Via n8n API
   curl -s "http://localhost:5678/api/v1/workflows/{id}" \
     -H "X-N8N-API-KEY: $N8N_API_KEY" > workflow-name.json
   ```
4. Add to this directory
5. Document in README
6. Consider extracting template for reuse

## Workflow Variables

When extracting templates, replace:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{CLIENT_NAME}}` | Client identifier | `acme-corp` |
| `{{CLIENT_GUILD_ID}}` | Discord server ID | `1234567890` |
| `{{CLIENT_CHANNEL_ID}}` | Discord channel ID | `1234567890` |
| `{{CLIENT_CREDENTIALS}}` | n8n credential ID | `abc123` |
| `{{AI_MODEL}}` | Ollama model name | `glm-5:cloud` |
| `{{CATEGORIES}}` | Email categories | `urgent,sales,support` |

## Credential Management

**NEVER commit credentials.** Store credentials in:
- n8n credential store (production)
- `ai-consulting/clients/{client}/credentials.md` (reference only, no secrets)
- Environment variables (development)

## Backup Strategy

Workflows are backed up automatically by n8n. Manual backups:
```bash
# Backup all workflows
cp ~/.n8n/workflows/*.json ~/n8n-workflows/backups/$(date +%Y-%m-%d)/
```

## Testing

Test workflows before deploying:
1. Use manual trigger
2. Test with sample data
3. Verify all destinations
4. Check error handling
5. Test with edge cases

---

*Last updated: April 2026*