import requests

from config import BASE_URL as base_url

# 使用你当前可以正常登录的练习账号和密码
data = {
    "username": "student08",
    "password": "new12345"
}

response = requests.post(
    base_url + "/api/login",
    json=data,
    timeout=5
)

assert response.status_code == 200

token = response.json()["data"]["token"]

headers = {"Authorization": f"Bearer {token}"}

resp = requests.get(
    base_url + "/api/me",
    headers=headers,
    timeout=5
)

assert resp.status_code == 200
user = resp.json()["data"]
assert user["username"] == data["username"]