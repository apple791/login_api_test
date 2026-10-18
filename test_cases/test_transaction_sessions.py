import requests

from config import BASE_URL, TIMEOUT, TRANSACTIONS_URL


def test_logout_invalidates_ledger_access(logged_in_user):
    headers = {
        "Authorization": f"Bearer {logged_in_user['token']}"
    }

    # 1. 新增合法收支，断言201，提取 record_id
    data = {
        "type": "expense",
        "amount": "25.00",
        "category": "food",
        "date": "2026-10-18",
        "note": "新增合法收支"
    }

    resp = requests.post(
        TRANSACTIONS_URL,
        json=data,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 201, resp.text
    record_id = resp.json()["data"]["id"]

    # 2. 用当前 Token 查询该记录，断言200
    resp = requests.get(
        BASE_URL + f"/api/transactions/{record_id}",
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    # 证明这个 Token 在退出前确实有效
    # 3. POST /api/logout，携带相同 headers，断言200
    resp = requests.post(
        BASE_URL + "/api/logout",
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    # 4. 用旧 Token 查询原记录，断言401、data为None
    resp = requests.get(
        BASE_URL + f"/api/transactions/{record_id}",
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["data"] is None, resp.text
    # 5. 用旧 Token 查询收支列表，断言401、data为None
    resp = requests.get(
        TRANSACTIONS_URL,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["data"] is None, resp.text
    # 6. 用旧 Token 新增合法收支，断言401、data为None
    data_b = {
        "type": "expense",
        "amount": "26.00",
        "category": "food",
        "date": "2026-10-18",
        "note": "新增合法收支"
    }
    resp = requests.post(
        TRANSACTIONS_URL,
        json=data_b,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["data"] is None, resp.text

    # 7. 使用原账号重新登录
    resp = requests.post(
        BASE_URL + "/api/login",
        json=logged_in_user["user"],
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    new_headers = {
        "Authorization": f"Bearer {resp.json()['data']['token']}"
    }

    # 8. 原记录仍然存在，内容不变
    resp = requests.get(
        BASE_URL + f"/api/transactions/{record_id}",
        headers=new_headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {"id": record_id, **data}, resp.text

    # 9. 当前独立账号只有退出前创建的那一条记录
    resp = requests.get(
        TRANSACTIONS_URL,
        headers=new_headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["total"] == 1, resp.text
