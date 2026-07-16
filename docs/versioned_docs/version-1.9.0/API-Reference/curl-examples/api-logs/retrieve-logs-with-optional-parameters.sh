curl -X GET \
  "$FLOW_URL/logs?lines_before=0&lines_after=0&timestamp=0" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
