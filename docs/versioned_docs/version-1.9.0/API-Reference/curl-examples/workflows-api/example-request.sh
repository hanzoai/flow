curl -X GET \
  "$FLOW_SERVER_URL/v1/workflows?job_id=job_id_1234567890" \
  -H "accept: application/json" \
  -H "x-api-key: $FLOW_API_KEY"
