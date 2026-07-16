curl -X DELETE \
  "$FLOW_URL/api/v2/files/$FILE_ID" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
