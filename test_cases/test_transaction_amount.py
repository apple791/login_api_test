import pytest
import requests

from config import BASE_URL, TIMEOUT, TRANSACTIONS_URL


@pytest.mark.parametrize("amount, expected_status", [
    ("0.00", 400),
    ("0.01", 201),
    ("0.02", 201),
    ("999999.98", 201),
    ("999999.99", 201),
    ("1000000.00", 400),
])
def test_transaction_amount_boundary(
    logged_in_user, amount, expected_status
):
    headers = {
        "Authorization": f"Bearer {logged_in_user['token']}"
    }
    data = {
        "type": "expense",
        "amount": amount,
        "category": "food",
        "date": "2026-10-18",
        "note": "金额边界测试"
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
    assert resp.status_code == expected_status, resp.text

    if expected_status == 201:
        record_id = resp.json()["data"]["id"]

        resp = requests.get(
            BASE_URL + f"/api/transactions/{record_id}",
            headers=headers,
            timeout=TIMEOUT
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["amount"] == amount, resp.text
    else:
        assert resp.json()["data"] is None, resp.text

    resp = requests.get(
        TRANSACTIONS_URL,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    after_total = resp.json()["data"]["total"]

    if expected_status == 201:
        assert after_total == before_total + 1, resp.text
    else:
        assert after_total == before_total, resp.text


@pytest.mark.parametrize("amount, expected_status, expected_amount", [
    ("100", 201, "100.00"),
    ("12.5", 201, "12.50"),
    ("12.501", 400, None),
    (100, 400, None),
    (None, 400, None),
    ("", 400, None),
    (" ", 400, None),
    ("中文", 400, None),
    ("@#$", 400, None),
])
def test_transaction_amount_equivalence(
        logged_in_user, amount, expected_status, expected_amount
):
    headers = {
        "Authorization": f"Bearer {logged_in_user['token']}"
    }
    data = {
        "type": "expense",
        "amount": amount,
        "category": "food",
        "date": "2026-10-18",
        "note": "金额等价类测试"
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
    assert resp.status_code == expected_status, resp.text

    if expected_status == 201:
        record_id = resp.json()["data"]["id"]

        resp = requests.get(
            BASE_URL + f"/api/transactions/{record_id}",
            headers=headers,
            timeout=TIMEOUT
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["amount"] == expected_amount, resp.text
    else:
        assert resp.json()["data"] is None, resp.text

    resp = requests.get(
        TRANSACTIONS_URL,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    after_total = resp.json()["data"]["total"]

    if expected_status == 201:
        assert after_total == before_total + 1, resp.text
    else:
        assert after_total == before_total, resp.text
