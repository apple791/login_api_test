import pytest
import requests

from config import BASE_URL, TIMEOUT, TRANSACTIONS_URL


def test_create_and_get_transaction(logged_in_user):
    headers = {
        "Authorization": f"Bearer {logged_in_user['token']}"
    }
    data = {
        "type": "expense",
        "amount": "12.50",
        "category": "food",
        "date": "2026-10-18",
        "note": "午餐"
    }

    # 1. 新增收支
    resp = requests.post(
        TRANSACTIONS_URL,
        json=data,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 201, resp.text

    record_id = resp.json()["data"]["id"]

    # 2. 使用本次新增返回的 ID 查询详情
    resp = requests.get(
        BASE_URL + f"/api/transactions/{record_id}",
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text

    # 3. 核对 ID 和全部业务字段
    assert resp.json()["data"] == {"id": record_id, **data}, resp.text


def test_transaction_without_amount(logged_in_user):
    headers = {
        "Authorization": f"Bearer {logged_in_user['token']}"
    }

    # 请求体里完全没有 amount 字段
    data = {
        "type": "expense",
        "category": "food",
        "date": "2026-10-18",
        "note": "缺失金额测试"
    }

    resp = requests.get(
        TRANSACTIONS_URL,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    before_total = resp.json()["data"]["total"]

    resp = requests.post(
        TRANSACTIONS_URL,
        json=data,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["data"] is None, resp.text

    resp = requests.get(
        TRANSACTIONS_URL,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["total"] == before_total, resp.text


@pytest.mark.parametrize("field,value,expected_status", [
    ("type", "unknown", 400), ("category", "salary", 400),
    ("date", "2026-02-30", 400), ("date", "2026-1-1", 400),
    ("note", "a" * 200, 201), ("note", "a" * 201, 400),
    ("note", None, 400),
])
def test_transaction_fields(logged_in_user, transaction_payload, field, value, expected_status):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    transaction_payload[field] = value
    resp = requests.post(TRANSACTIONS_URL, json=transaction_payload, headers=headers, timeout=TIMEOUT)
    assert resp.status_code == expected_status, resp.text
    if expected_status == 201:
        record = resp.json()["data"]
        resp = requests.get(f"{TRANSACTIONS_URL}/{record['id']}", headers=headers, timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"] == record, resp.text
    else:
        assert resp.json()["data"] is None, resp.text
    resp = requests.get(TRANSACTIONS_URL, headers=headers, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["total"] == (1 if expected_status == 201 else 0), resp.text


def test_transaction_detail_not_found(logged_in_user):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    # 使用已新增的最大ID加1，不依赖固定的数据库记录。
    payload = {"type": "income", "amount": "100.00", "category": "salary", "date": "2026-10-18"}
    resp = requests.post(TRANSACTIONS_URL, json=payload, headers=headers, timeout=TIMEOUT)
    assert resp.status_code == 201, resp.text
    missing_id = resp.json()["data"]["id"] + 1
    resp = requests.get(f"{TRANSACTIONS_URL}/{missing_id}", headers=headers, timeout=TIMEOUT)
    assert resp.status_code == 404, resp.text
    assert resp.json()["data"] is None, resp.text
