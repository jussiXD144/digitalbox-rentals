from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

response = client.post("/register", data={"email": "test@test.com", "password": "password"})
print("Status:", response.status_code)
print("Response:", response.text)
