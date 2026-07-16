curl -X DELETE \
  "$FLOW_URL/api/v1/projects/$PROJECT_ID" \
  -H "accept: */*" \
  -H "x-api-key: $FLOW_API_KEY"
