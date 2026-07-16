curl -X POST \
  "$FLOW_SERVER_URL/api/v1/responses" \
  -H "x-api-key: $FLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-FLOW-GLOBAL-VAR-OPENAI_API_KEY: sk-..." \
  -H "X-FLOW-GLOBAL-VAR-USER_ID: user123" \
  -H "X-FLOW-GLOBAL-VAR-ENVIRONMENT: production" \
  -d '{
    "model": "your-flow-id",
    "input": "Hello"
  }'
