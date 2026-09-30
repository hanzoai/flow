curl -X GET \
  "$FLOW_URL/v1/users/whoami" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
