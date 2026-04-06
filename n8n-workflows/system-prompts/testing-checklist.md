# n8n Workflow Testing Checklist

Complete testing procedure for validating n8n workflows before deployment.

## Pre-Testing Setup

- [ ] Workflow imported successfully
- [ ] All credentials configured and connected
- [ ] Node names are descriptive (not "Set1", "If2")
- [ ] Position coordinates are reasonable (no overlaps)

## Unit Testing (Each Node)

### Trigger Nodes
- [ ] Trigger fires on expected event
- [ ] Trigger data structure matches expected format
- [ ] Schedule triggers run at correct times
- [ ] Webhook triggers accept correct HTTP methods

### Data Nodes
- [ ] Set nodes output expected fields
- [ ] Code nodes handle edge cases (null, empty, unexpected types)
- [ ] Merge nodes combine data correctly

### Conditional Nodes
- [ ] If nodes branch correctly for true/false cases
- [ ] Switch nodes route to correct outputs
- [ ] Fallback output works for unexpected values

### Integration Nodes
- [ ] HTTP requests succeed with valid responses
- [ ] Discord/Slack messages deliver to correct channels
- [ ] Gmail operations complete (send, label, archive)
- [ ] Calendar events create/update/delete correctly

### AI Nodes
- [ ] Ollama connection succeeds
- [ ] Model responds within timeout
- [ ] Response format matches expected schema
- [ ] Error handling works for invalid prompts

## Integration Testing (Full Flow)

### Happy Path
- [ ] Workflow completes end-to-end
- [ ] Final output matches expected format
- [ ] Data transformations are correct
- [ ] Notifications deliver to correct destinations

### Error Handling
- [ ] Workflow handles API errors gracefully
- [ ] Timeout errors don't hang workflow
- [ ] Invalid input data doesn't crash workflow
- [ ] Error nodes capture and report failures

### Edge Cases
- [ ] Empty input data handled correctly
- [ ] Large payloads processed without timeout
- [ ] Unicode characters preserved through flow
- [ ] Timezone conversions correct

## Performance Testing

- [ ] Workflow completes within expected time
- [ ] Memory usage reasonable for data volume
- [ ] No infinite loops or runaway executions
- [ ] Concurrency handling (multiple simultaneous triggers)

## Security Testing

- [ ] No credentials exposed in logs
- [ ] No sensitive data in workflow name/description
- [ ] Input validation prevents injection attacks
- [ ] API keys have minimum required permissions

## Deployment Checklist

### Staging
- [ ] Test with staging credentials
- [ ] Verify test data handling
- [ ] Check execution history for errors

### Production
- [ ] Update to production credentials
- [ ] Enable workflow
- [ ] Set production webhook URLs (if applicable)
- [ ] Schedule triggers set for correct timezone
- [ ] Monitor first few executions

## Testing Commands

### Trigger Manual Execution
```bash
curl -X POST "http://localhost:5678/api/v1/workflows/{workflowId}/execute" \
  -H "X-N8N-API-KEY: your-api-key"
```

### Get Execution History
```bash
curl "http://localhost:5678/api/v1/executions?workflowId={workflowId}&limit=10" \
  -H "X-N8N-API-KEY: your-api-key"
```

### Check Workflow Status
```bash
curl "http://localhost:5678/api/v1/workflows/{workflowId}" \
  -H "X-N8N-API-KEY: your-api-key"
```

## Common Issues and Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Trigger not firing | Webhook URL incorrect | Verify path and method |
| Timeout errors | Large data or slow API | Increase timeout, chunk data |
| Authentication failed | Expired/invalid credentials | Re-authorize OAuth |
| Empty output | Incorrect JSON path | Check `$json` references |
| Wrong branch | Condition mismatch | Debug with Set node |

## Test Data Templates

### Email Test Data
```json
{
  "subject": "Test Subject",
  "from": {"emailAddress": "test@example.com"},
  "bodyPreview": "Test email body content",
  "id": "test-email-id"
}
```

### Webhook Test Data
```json
{
  "event": "test",
  "data": {"key": "value"},
  "timestamp": "2026-01-01T00:00:00Z"
}
```

### AI Response Test
```json
{
  "category": "urgent",
  "priority": "high",
  "summary": "Test summary"
}
```

## Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | [ ] |
| Reviewer | | | [ ] |
| Deployer | | | [ ] |