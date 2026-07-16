curl -X GET \
  "$FLOW_URL/api/v1/build/123e4567-e89b-12d3-a456-426614174000/events" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
