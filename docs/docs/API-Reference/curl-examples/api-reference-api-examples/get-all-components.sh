curl -X GET \
  "$FLOW_SERVER_URL/api/v1/all" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
