curl -X PUT \
  "$FLOW_URL/v1/files/$FILE_ID?name=new_file_name" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
