curl -X DELETE \
  "$FLOW_URL/v1/monitor/messages/session/different_session_id_2" \
  -H "accept: */*" \
  -H "x-api-key: $FLOW_API_KEY"
