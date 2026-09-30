curl -X POST \
  "$FLOW_SERVER_URL/v1/workflows/stop" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $FLOW_API_KEY" \
  -d '{
    "job_id": "job_id_1234567890"
  }'
