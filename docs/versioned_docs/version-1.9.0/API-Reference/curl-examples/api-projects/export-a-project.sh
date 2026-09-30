curl -X GET \
  "$FLOW_URL/v1/projects/download/$PROJECT_ID" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY" \
  --output flow-project.zip
