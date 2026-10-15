"""按功能整理的接口测试用例。"""
import pytest
import requests
import uuid

from config import (
    TIMEOUT,
    REGISTER_URL,
    LOGIN_URL,
    ME_URL,
    CHANGE_PASSWORD_URL,
)


def test_change_password_success(logged_in_user):
    user = logged_in_user["user"]
    old_token = logged_in_user["token"]

    resp = requests.post(
        CHANGE_PASSWORD_URL,
        json={
            "old_password": user["password"],
            "new_password": "new12345"
        },
        headers={"Authorization": f"Bearer {old_token}"},
        timeout=TIMEOUT
    )

    assert resp.status_code == 200, resp.text

    resp = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {old_token}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text

    resp = requests.post(
        LOGIN_URL,
        json=user,
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text

    resp = requests.post(
        LOGIN_URL,
        json={
            "username":user["username"],
            "password": "new12345"
        },
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
    assert resp.json()["data"]["username"] == user["username"]


def test_change_password_with_wrong_old_password(registered_user):
    resp = requests.post(
        LOGIN_URL,
        json=registered_user,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    old_token = resp.json()["data"]["token"]

    resp = requests.post(
        CHANGE_PASSWORD_URL,
        json={
            "old_password": "wrong123",
            "new_password": "new12345"
        },
        headers={"Authorization": f"Bearer {old_token}"},
        timeout=TIMEOUT
    )

    assert resp.status_code == 401, resp.text

    resp = requests.post(
        LOGIN_URL,
        json=registered_user,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    resp = requests.post(
        LOGIN_URL,
        json={
            "username": registered_user["username"],
            "password": "new12345"
        },
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text

    resp = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {old_token}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["username"] == registered_user["username"]


def test_change_password_revokes_all_sessions(registered_user):
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

    assert token_a != token_b, "两次登录应生成不同的 Token"

    for token in [token_a, token_b]:
        resp = requests.get(
            ME_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["username"] == registered_user["username"]

    resp = requests.post(
        CHANGE_PASSWORD_URL,
        json={
            "old_password": registered_user["password"],
            "new_password": "new12345"
        },
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
    assert resp.status_code == 401, resp.text

    resp = requests.post(
        LOGIN_URL,
        json={
            "username": registered_user["username"],
            "password": "new12345"
        },
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


def test_change_password_keeps_other_user_session(registered_user):
    resp = requests.post(
        LOGIN_URL,
        json=registered_user,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    token_a = resp.json()["data"]["token"]

    data_b = {
        "username": "u" + uuid.uuid4().hex[:12],
        "password": "abc12345"
    }

    resp = requests.post(
        REGISTER_URL,
        json=data_b,
        timeout=TIMEOUT
    )
    assert resp.status_code == 201, resp.text
    assert data_b["username"] != registered_user["username"]

    resp = requests.post(
        LOGIN_URL,
        json=data_b,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    token_b = resp.json()["data"]["token"]

    resp = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["username"] == data_b["username"]

    resp = requests.post(
        CHANGE_PASSWORD_URL,
        json={
            "old_password": registered_user["password"],
            "new_password": "new12345"
        },
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
    assert resp.json()["data"]["username"] == data_b["username"]


@pytest.mark.parametrize("length, expected_status", [
    (5, 400),
    (6, 200),
    (7, 200),
    (15, 200),
    (16, 200),
    (17, 400),
])
def test_change_password_length(logged_in_user, length, expected_status):
    # 获取账号和 Token
    user = logged_in_user["user"]
    old_token = logged_in_user["token"]

    # 新密码使用 "b" * length
    data={
        "old_password": user["password"],
        "new_password": "b"*length
    }

    # 发送改密请求，检查状态码
    resp = requests.post(
        CHANGE_PASSWORD_URL,
        json=data,
        headers={"Authorization": f"Bearer {old_token}"},
        timeout=TIMEOUT
    )

    assert resp.status_code == expected_status, resp.text

    if expected_status == 200:
        # 检查成功后的三个结果
        resp = requests.get(
            ME_URL,
            headers={"Authorization": f"Bearer {old_token}"},
            timeout=TIMEOUT
        )
        assert resp.status_code == 401, resp.text

        resp = requests.post(
            LOGIN_URL,
            json=user,
            timeout=TIMEOUT
        )
        assert resp.status_code == 401, resp.text

        resp = requests.post(
            LOGIN_URL,
            json={
                "username": user["username"],
                "password": "b"*length
            },
            timeout=TIMEOUT
        )
        assert resp.status_code == 200, resp.text


    else:
        # 检查失败后的三个结果
        resp = requests.get(
            ME_URL,
            headers={"Authorization": f"Bearer {old_token}"},
            timeout=TIMEOUT
        )
        assert resp.status_code == 200, resp.text

        resp = requests.post(
            LOGIN_URL,
            json=user,
            timeout=TIMEOUT
        )
        assert resp.status_code == 200, resp.text

        resp = requests.post(
            LOGIN_URL,
            json={
                "username": user["username"],
                "password": "b"*length
            },
            timeout=TIMEOUT
        )
        assert resp.status_code == 401, resp.text


def test_change_same_password(logged_in_user):
    token = logged_in_user["token"]
    user = logged_in_user["user"]
    password = user["password"]
    data = {
        "old_password":password,
        "new_password":password
    }
    headers = {
        "Authorization":f"Bearer {token}"
    }
    resp = requests.post(
        CHANGE_PASSWORD_URL,
        json=data,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 400, resp.text

    resp = requests.post(
        LOGIN_URL,
        json=user,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    resp = requests.get(
        ME_URL,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text


def test_change_password_without_token():
    resp = requests.post(
        CHANGE_PASSWORD_URL,
        json = {
            "old_password": "abc12345",
            "new_password": "new12345"
        },
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["data"] is None
