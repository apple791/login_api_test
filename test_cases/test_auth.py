"""按功能整理的接口测试用例。"""
import pytest
import requests

from config import (
    BASE_URL as base_url,
    TIMEOUT,
    LOGOUT_PATH,
    CHANGE_PASSWORD_PATH,
)


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer invalid-token"},
    {"Authorization": "Basic abc"},
    {"Authorization": "Bearer "},
])
@pytest.mark.parametrize("path", [
    LOGOUT_PATH,
    CHANGE_PASSWORD_PATH,
])
def test_account_with_invalid_token(headers, path):
    resp = requests.post(
        base_url + path,
        headers=headers,
        json={
            "old_password": "abc12345",
            "new_password": "new12345"
        },
        timeout=TIMEOUT
    )
    assert resp.status_code==401, resp.text
    assert resp.json()["data"] is None
