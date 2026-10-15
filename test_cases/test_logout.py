"""按功能整理的接口测试用例。"""
import requests

from config import (
    TIMEOUT,
    LOGIN_URL,
    ME_URL,
    LOGOUT_URL,
)


def test_logout_with_invalidates_token(registered_user):
    resp = requests.post(
        LOGIN_URL,
        json=registered_user,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    old_token = resp.json()["data"]["token"]

    old_headers = {"Authorization": f"Bearer {old_token}"}

    resp = requests.get(
        ME_URL,
        headers=old_headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    resp = requests.post(
        LOGOUT_URL,
        headers=old_headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    resp = requests.get(
        ME_URL,
        headers=old_headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text

    resp = requests.post(
        LOGIN_URL,
        json=registered_user,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    new_token = resp.json()["data"]["token"]

    resp = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {new_token}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["username"] == registered_user["username"]


def test_logout_keeps_other_session(registered_user):
    resp = requests.post(
        LOGIN_URL,
        json=registered_user,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    token_a = resp.json()["data"]["token"]

    resp = requests.post(
        LOGIN_URL,
        json=registered_user,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    token_b = resp.json()["data"]["token"]
    assert token_a != token_b, "两次独立登录应生成不同的 Token"

    resp = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token_a}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    resp = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    resp = requests.post(
        LOGOUT_URL,
        headers={"Authorization": f"Bearer {token_a}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    resp = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token_a}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text

    resp = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    assert resp.json()["data"]["username"] == registered_user["username"]


def test_logout_again(logged_in_user):
    token = logged_in_user["token"]

    resp = requests.post(
        LOGOUT_URL,
        headers={"Authorization":f"Bearer {token}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    resp = requests.post(
        LOGOUT_URL,
        headers={"Authorization":f"Bearer {token}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text
