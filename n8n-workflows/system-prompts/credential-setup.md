# n8n Credential Setup Guide

Step-by-step instructions for setting up credentials in n8n for common integrations.

## Discord Bot

### Prerequisites
1. Create a Discord application at https://discord.com/developers/applications
2. Create a bot user and copy the token
3. Enable MESSAGE CONTENT INTENT in Bot settings
4. Invite bot to server with appropriate permissions

### n8n Setup
1. Go to Settings → Credentials
2. Click "Add Credential"
3. Select "Discord API"
4. Enter:
   - **Name**: `Discord Bot`
   - **Bot Token**: `your-bot-token-here`
5. Save

### Channel IDs Required
- Format: `channel:1234567890123456789` for channels
- Format: `user:123456789012345678` for DMs

### Testing
```
Send test message to #test channel:
POST /api/v1/executions/{workflowId}/run
- Use manual trigger node
- Verify message appears in Discord
```

---

## Gmail

### Prerequisites
1. Google Cloud Console → Create OAuth 2.0 credentials
2. Enable Gmail API
3. Add authorized redirect URI: `https://your-n8n-instance/rest/oauth2-credential/callback`

### n8n Setup
1. Add Credential → "Gmail OAuth2 API"
2. Click "Sign in with Google"
3. Authorize access
4. Save

### Testing
```
Test with Gmail Trigger node:
- Manual trigger
- Send test email to account
- Verify trigger fires
```

---

## Ollama (Local LLM)

### Prerequisites
1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull model: `ollama pull glm-5:cloud`
3. Verify running: `curl http://localhost:11434/api/tags`

### n8n Setup
1. Add Credential → "Ollama API"
2. Enter:
   - **Base URL**: `http://localhost:11434` (or your server IP)
   - **No API key required** for local instances

### Testing
```
Test with AI Agent node:
- Set model to `glm-5:cloud`
- Simple prompt: "Say hello"
- Verify response
```

---

## Google Calendar

### Prerequisites
1. Google Cloud Console → Enable Google Calendar API
2. Create OAuth 2.0 credentials
3. Add redirect URI

### n8n Setup
1. Add Credential → "Google Calendar OAuth2 API"
2. Authorize with Google account
3. Save

### Testing
```
Test with Calendar node:
- List calendars
- Create test event
- Delete test event
```

---

## HTTP Request (Custom API)

### API Key Authentication
1. Add Credential → "Header Auth"
2. Enter:
   - **Name**: `API Key`
   - **Header Name**: `Authorization` or `X-API-Key`
   - **Header Value**: `Bearer your-api-key` or just `your-api-key`

### Basic Authentication
1. Add Credential → "Basic Auth"
2. Enter username and password

### Testing
```
Test with HTTP Request node:
- Use test endpoint
- Verify authentication headers sent correctly
```

---

## Credential Security Checklist

- [ ] Never commit credentials to version control
- [ ] Use environment variables for sensitive values
- [ ] Rotate API keys regularly
- [ ] Limit credential scope to minimum required permissions
- [ ] Use separate credentials for development/production
- [ ] Document credential IDs in `~/n8n-workflows/README.md`

## Credential Reference in Workflows

```json
{
  "credentials": {
    "discordBotApi": {
      "id": "ZDMFOE75AzwAAVO3",
      "name": "Discord Bot"
    }
  }
}
```

## Environment-Specific Credentials

| Environment | Credential Naming | Scope |
|-------------|-------------------|-------|
| Development | `{Service} Dev` | Read-only or test data |
| Staging | `{Service} Staging` | Limited production data |
| Production | `{Service} Prod` | Full permissions |

## Recovery

If credentials are lost:
1. Regenerate API key/token in service dashboard
2. Update credential in n8n
3. Re-authorize OAuth credentials
4. Test all affected workflows