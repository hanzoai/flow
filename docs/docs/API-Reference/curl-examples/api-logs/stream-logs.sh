curl -X GET \
  "$FLOW_URL/logs-stream" \
  -H "accept: text/event-stream" \
  -H "x-api-key: $FLOW_API_KEY"
