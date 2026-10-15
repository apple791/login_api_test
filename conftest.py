"""共享夹具：按需注册、登录；每条用例使用独立账号。"""
import pytest
import requests
import uuid

from config import (
    TIMEOUT,
    REGISTER_URL,
    LOGIN_URL,
)


@pytest.fixture
def registered_user():
    data = {
        "username": "u" + uuid.uuid4().hex[:12],
        "password": "abc12345"
    }

    response = requests.post(
        REGISTER_URL,
        json=data,
        timeout=TIMEOUT
    )
    assert response.status_code == 201, response.text

    return data


@pytest.fixture
def logged_in_user(registered_user):
    response = requests.post(
        LOGIN_URL,
        json=registered_user,
        timeout=TIMEOUT
    )
    assert response.status_code == 200, response.text

    return {
        "user": registered_user,
        "token": response.json()["data"]["token"]
    }
