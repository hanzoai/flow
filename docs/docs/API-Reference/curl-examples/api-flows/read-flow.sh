curl -X GET \
  "$FLOW_URL/v1/flows/$FLOW_ID" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
