#!/bin/bash
# Trigger n8n workflow execution manually
# Usage: ./trigger-workflow.sh <workflow-id>

WORKFLOW_ID="${1:-trading-signals-001}"
N8N_API_KEY="n8n_api_381366c32d1f1b6787c0e8ce917ffd817bb32c6e4687a2ba37a7a6c2ebbe2d2a"
N8N_URL="http://localhost:5678"

echo "Triggering workflow: $WORKFLOW_ID"

# Try to execute via API
RESPONSE=$(curl -s -X POST "$N8N_URL/api/v1/workflows/$WORKFLOW_ID/execute" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}')

echo "$RESPONSE" | jq -r '.executionId // .message // "Triggered"'
