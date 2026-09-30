curl -X DELETE \
  "$FLOW_URL/v1/projects/$PROJECT_ID" \
  -H "accept: */*" \
  -H "x-api-key: $FLOW_API_KEY"
