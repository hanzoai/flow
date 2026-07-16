import os

import requests

base = os.environ.get("FLOW_URL") or os.environ.get("FLOW_SERVER_URL", "")
flow_id = os.environ.get("FLOW_ID", "")
api_key = os.environ.get("FLOW_API_KEY", "")

headers = {
    "Content-Type": "application/json",
    "x-api-key": api_key,
    "X-FLOW-GLOBAL-VAR-USER_ID": "user123",
    "X-FLOW-GLOBAL-VAR-ENVIRONMENT": "production",
}

payload = {
    "input_value": "Tell me about something interesting!",
    "input_type": "chat",
    "output_type": "chat",
}

response = requests.post(f"{base}/api/v1/run/{flow_id}", headers=headers, json=payload, timeout=60)
response.raise_for_status()
print(response.text)
