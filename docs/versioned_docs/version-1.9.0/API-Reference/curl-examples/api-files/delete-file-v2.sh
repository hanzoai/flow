curl -X DELETE \
  "$FLOW_URL/v1/files/$FILE_ID" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
