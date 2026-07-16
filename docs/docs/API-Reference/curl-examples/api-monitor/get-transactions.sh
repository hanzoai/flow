curl -X GET \
  "$FLOW_URL/api/v1/monitor/transactions?flow_id=$FLOW_ID&page=1&size=50" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
