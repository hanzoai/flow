curl -X GET \
  "$FLOW_SERVER_URL/v1/config" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
