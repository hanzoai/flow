curl -X GET \
  "$FLOW_URL/api/v1/monitor/builds?flow_id=$FLOW_ID" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
