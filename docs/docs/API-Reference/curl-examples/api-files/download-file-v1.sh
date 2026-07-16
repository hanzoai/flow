curl -X GET \
  "$FLOW_URL/api/v1/files/download/$FLOW_ID/2024-12-30_15-19-43_your_file.txt" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY" \
  --output downloaded_file.txt
