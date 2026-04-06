# n8n Node Templates

Reusable node configurations for common n8n workflow patterns.

## Trigger Nodes

### Schedule Trigger (Daily at 6 AM)
```json
{
  "type": "n8n-nodes-base.schedule",
  "name": "Daily Trigger",
  "position": [250, 300],
  "parameters": {
    "rule": {
      "interval": [{"field": "hours", "hoursInterval": 24}],
      "timezone": "America/Los_Angeles"
    },
    "mode": "cron",
    "cronExpression": "0 6 * * *"
  }
}
```

### Webhook Trigger
```json
{
  "type": "n8n-nodes-base.webhook",
  "name": "Webhook",
  "position": [250, 300],
  "parameters": {
    "httpMethod": "POST",
    "path": "webhook-path",
    "responseMode": "onReceived",
    "responseData": "allEntries"
  },
  "webhookId": "unique-webhook-id"
}
```

### Gmail Trigger
```json
{
  "type": "n8n-nodes-base.gmailTrigger",
  "name": "Gmail Trigger",
  "position": [250, 300],
  "parameters": {
    "filters": {
      "q": "is:unread"
    },
    "options": {
      "markAsRead": true
    }
  },
  "credentials": {
    "gmailOAuth2Api": {
      "id": "credential_id",
      "name": "Gmail account"
    }
  }
}
```

## AI/LLM Nodes

### Ollama Chat (AI Agent)
```json
{
  "type": "@n8n/n8n-nodes-langchain.lmChatOllama",
  "name": "Ollama Chat",
  "position": [500, 300],
  "parameters": {
    "model": "glm-5:cloud",
    "baseUrl": "http://localhost:11434",
    "options": {
      "temperature": 0.7,
      "numPredict": 2048
    }
  }
}
```

### AI Agent Node
```json
{
  "type": "@n8n/n8n-nodes-langchain.agent",
  "name": "AI Agent",
  "position": [500, 300],
  "parameters": {
    "promptType": "define",
    "text": "={{ $json.prompt }}",
    "hasOutputParser": true,
    "outputSchema": {
      "type": "object",
      "properties": {
        "category": {"type": "string"},
        "priority": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}
```

## Notification Nodes

### Discord Message
```json
{
  "type": "n8n-nodes-base.discord",
  "name": "Discord Notification",
  "position": [750, 300],
  "parameters": {
    "resource": "message",
    "operation": "post",
    "channelId": "={{ $json.channelId }}",
    "content": "={{ $json.message }}"
  },
  "credentials": {
    "discordBotApi": {
      "id": "credential_id",
      "name": "Discord Bot"
    }
  }
}
```

### Slack Message
```json
{
  "type": "n8n-nodes-base.slack",
  "name": "Slack Notification",
  "position": [750, 300],
  "parameters": {
    "resource": "message",
    "operation": "post",
    "channel": "#notifications",
    "text": "={{ $json.message }}"
  },
  "credentials": {
    "slackApi": {
      "id": "credential_id",
      "name": "Slack account"
    }
  }
}
```

## Data Processing Nodes

### Set Node (Data Transformation)
```json
{
  "type": "n8n-nodes-base.set",
  "name": "Prepare Data",
  "position": [450, 300],
  "parameters": {
    "mode": "manual",
    "values": {
      "string": [
        {"name": "subject", "value": "={{ $json.subject }}"},
        {"name": "from", "value": "={{ $json.from.emailAddress }}"},
        {"name": "preview", "value": "={{ $json.bodyPreview }}"}
      ]
    },
    "options": {}
  }
}
```

### Code Node (JavaScript)
```json
{
  "type": "n8n-nodes-base.code",
  "name": "Process Data",
  "position": [500, 300],
  "parameters": {
    "mode": "runOnceForAllItems",
    "jsCode": "// Process all items\nconst results = items.map(item => {\n  return {\n    json: {\n      ...item.json,\n      processed: true,\n      timestamp: new Date().toISOString()\n    }\n  };\n});\nreturn results;"
  }
}
```

### If Node (Conditional)
```json
{
  "type": "n8n-nodes-base.if",
  "name": "Check Priority",
  "position": [550, 300],
  "parameters": {
    "conditions": {
      "string": [
        {
          "value1": "={{ $json.priority }}",
          "operation": "equals",
          "value2": "high"
        }
      ]
    }
  }
}
```

### Switch Node (Multi-way)
```json
{
  "type": "n8n-nodes-base.switch",
  "name": "Route by Category",
  "position": [550, 300],
  "parameters": {
    "rules": [
      {"output": 0, "conditions": {"string": [{"value1": "={{ $json.category }}", "value2": "urgent"}]}},
      {"output": 1, "conditions": {"string": [{"value1": "={{ $json.category }}", "value2": "sales"}]}},
      {"output": 2, "conditions": {"string": [{"value1": "={{ $json.category }}", "value2": "support"}]}}
    ],
    "fallbackOutput": 3
  }
}
```

## HTTP Request Node

### Generic HTTP Request
```json
{
  "type": "n8n-nodes-base.httpRequest",
  "name": "HTTP Request",
  "position": [500, 300],
  "parameters": {
    "method": "POST",
    "url": "={{ $json.webhookUrl }}",
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth",
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {"name": "data", "value": "={{ $json.payload }}"}
      ]
    }
  },
  "credentials": {
    "httpHeaderAuth": {
      "id": "credential_id",
      "name": "API Key"
    }
  }
}
```

## Merge Node

### Merge Multiple Inputs
```json
{
  "type": "n8n-nodes-base.merge",
  "name": "Combine Results",
  "position": [600, 300],
  "parameters": {
    "mode": "combine",
    "combineBy": "mergeByPosition"
  }
}
```

## Connection Patterns

### Linear Flow
```json
{
  "Trigger Node": {"main": [[{"node": "Process Node", "type": "main", "index": 0}]]},
  "Process Node": {"main": [[{"node": "Notification Node", "type": "main", "index": 0}]]}
}
```

### Branching Flow (If Node)
```json
{
  "If Node": {
    "main": [
      [{"node": "True Path", "type": "main", "index": 0}],
      [{"node": "False Path", "type": "main", "index": 0}]
    ]
  }
}
```

### Multi-way Flow (Switch Node)
```json
{
  "Switch Node": {
    "main": [
      [{"node": "Output 0", "type": "main", "index": 0}],
      [{"node": "Output 1", "type": "main", "index": 0}],
      [{"node": "Output 2", "type": "main", "index": 0}],
      [{"node": "Default", "type": "main", "index": 0}]
    ]
  }
}
```