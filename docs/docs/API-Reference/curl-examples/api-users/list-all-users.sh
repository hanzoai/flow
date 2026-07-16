curl -X GET \
  "$FLOW_URL/api/v1/users/?skip=0&limit=10" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
