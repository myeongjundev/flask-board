import requests


url = "http://localhost:5678/webhook-test/dbf71751-63bc-4cdd-ab0f-52b729f353bd"
payload = {
    "ip": "1.2.3.4",
    "level": 10,
    "rule": "5712",
}

response = requests.post(url, json=payload, timeout=10)

print(f"status: {response.status_code}")
print(response.text)
response.raise_for_status()
