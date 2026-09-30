curl -X DELETE \
  "$FLOW_URL/v1/monitor/builds?flow_id=$FLOW_ID" \
  -H "accept: */*" \
  -H "x-api-key: $FLOW_API_KEY"
