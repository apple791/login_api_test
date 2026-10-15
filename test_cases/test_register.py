"""按功能整理的接口测试用例。"""
import pytest
import requests
import uuid

from config import (
    TIMEOUT,
    REGISTER_URL,
    LOGIN_URL,
)


@pytest.mark.parametrize("length, expected_status", [
    (5, 400),
    (6, 201),
    (7, 201),
    (15, 201),
    (16, 201),
    (17, 400),
])
def test_register_password_length(length, expected_status):
    username = "u" + uuid.uuid4().hex[:12]
    resp = requests.post(
        REGISTER_URL,
        json = {
                "username": username,
                "password": "a"*length
            },
        timeout=TIMEOUT
    )

    assert resp.status_code == expected_status, resp.text

    if expected_status == 201:
        login_response = requests.post(
            LOGIN_URL,
            json={
                "username": username,
                "password": "a" * length
            },
            timeout=TIMEOUT
        )

        assert login_response.status_code == 200, login_response.text
        assert login_response.json()["data"]["token"]


def test_register_duplicate_username(registered_user):
    resp = requests.post(
        REGISTER_URL,
        json=registered_user,
        timeout=TIMEOUT
    )

    assert resp.status_code == 409, resp.text
    assert resp.json()["data"] is None
