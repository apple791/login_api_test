"""共享夹具：按需注册、登录；每条用例使用独立账号。"""
import uuid
import sqlite3

import pytest
import requests


from config import (
    DB_PATH,
    TIMEOUT,
    REGISTER_URL,
    LOGIN_URL,
    TRANSACTIONS_URL,
)


@pytest.fixture
def db_connection():
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"数据库不存在：{DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()



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


@pytest.fixture
def transaction_payload():
    """每条用例获得独立字典，允许修改字段而不污染其他测试。"""
    return {"type": "expense", "amount": "12.50", "category": "food",
            "date": "2026-10-18", "note": "账本接口测试"}


@pytest.fixture
def three_transactions(logged_in_user):
    """只为列表用例创建三条记录；函数作用域，账号相互独立。"""
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    records = []
    for kind, amount, category in [
        ("income", "100.00", "salary"),
        ("expense", "20.00", "food"),
        ("expense", "10.00", "transport"),
    ]:
        payload = {"type": kind, "amount": amount, "category": category,
                   "date": "2026-10-18", "note": "列表筛选"}
        response = requests.post(TRANSACTIONS_URL, json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 201, response.text
        records.append({"id": response.json()["data"]["id"], **payload})
    return {"headers": headers, "records": records}
