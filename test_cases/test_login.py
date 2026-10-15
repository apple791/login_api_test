"""按功能整理的接口测试用例。"""
import pytest
import requests

from config import (
    TIMEOUT,
    LOGIN_URL,
    ME_URL,
)


def test_login_and_get_me(registered_user):
    data = registered_user

    login_response = requests.post(
        LOGIN_URL,
        json=data,
        timeout=TIMEOUT
    )

    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["data"]["token"]

    resp = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["username"] == data["username"]


@pytest.mark.parametrize("password,expected_status", [
    ("wrong123", 401),
    ("WRONG123", 401),
    ("123456", 401),
    ("", 400),
    (None, 400),
    (123456, 400),
])
def test_login_with_invalid_password(registered_user,password,expected_status):
    # 补充请求及两个断言
    data = registered_user

    resp = requests.post(
        LOGIN_URL,
        json ={
            "username": data["username"],
            "password": password
        },
        timeout=TIMEOUT
    )

    assert resp.status_code == expected_status, resp.text
    assert resp.json()["data"] is None


def test_login_without_password():
    # 请求体只包含 username
    # 检查状态码为400
    # 检查响应 data 为 None
    resp = requests.post(
        LOGIN_URL,
        json={
            "username": "student08"
        },
        timeout=TIMEOUT
    )

    assert resp.status_code == 400, resp.text
    assert resp.json()["data"] is None
