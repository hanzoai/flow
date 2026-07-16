curl -X POST \
  "$FLOW_SERVER_URL/api/v1/run/$FLOW_ID" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $FLOW_API_KEY" \
  -H "X-FLOW-GLOBAL-VAR-OPENAI_API_KEY: sk-..." \
  -H "X-FLOW-GLOBAL-VAR-USER_ID: user123" \
  -H "X-FLOW-GLOBAL-VAR-ENVIRONMENT: production" \
  -d '{
    "input_value": "Tell me about something interesting!",
    "input_type": "chat",
    "output_type": "chat"
  }'
