curl -X POST \
  "$FLOW_SERVER_URL/v1/webhook/$FLOW_ID" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $FLOW_API_KEY" \
  -d '{"data": "example-data"}'
