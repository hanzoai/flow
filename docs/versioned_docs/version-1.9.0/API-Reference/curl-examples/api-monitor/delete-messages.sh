curl -v -X DELETE \
  "$FLOW_URL/v1/monitor/messages" \
  -H "accept: */*" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $FLOW_API_KEY" \
  -d '["MESSAGE_ID_1", "MESSAGE_ID_2"]'
