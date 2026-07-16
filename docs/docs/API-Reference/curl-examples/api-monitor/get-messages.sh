curl -X GET \
  "$FLOW_URL/api/v1/monitor/messages" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
