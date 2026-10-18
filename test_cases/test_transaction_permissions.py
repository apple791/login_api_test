import pytest
import requests
import uuid

from config import BASE_URL, TIMEOUT, TRANSACTIONS_URL


def test_transaction_keeps_other_user_out(logged_in_user):
    headers = {
        "Authorization": f"Bearer {logged_in_user['token']}"
    }

    data = {
        "type": "expense",
        "amount": "20.00",
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

    payload = {
        "username": "u" + uuid.uuid4().hex[:12],
        "password": "abc12345"
    }

    response = requests.post(
        BASE_URL + "/api/register",
        json=payload,
        timeout=TIMEOUT
    )
    assert response.status_code == 201, response.text

    resp = requests.post(
        BASE_URL + "/api/login",
        json=payload,
        timeout= TIMEOUT
    )
    assert resp.status_code == 200, resp.text
    token_b = resp.json()["data"]["token"]
    headers_b = {
        "Authorization": f"Bearer {token_b}"
    }
    resp = requests.get(
        BASE_URL + f"/api/transactions/{record_id}",
            headers=headers_b,
            timeout=TIMEOUT
    )

    assert resp.status_code == 404, resp.text
    assert resp.json()["data"] is None, resp.text

    resp = requests.get(
        TRANSACTIONS_URL,
        headers=headers_b,
        timeout=TIMEOUT
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["total"] == 0, resp.text

    resp = requests.get(
        BASE_URL + f"/api/transactions/{record_id}",
        headers=headers,
        timeout=TIMEOUT
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {"id": record_id, **data}, resp.text


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer invalid-token"},
    {"Authorization": "Basic abc"},
    {"Authorization": "Bearer "},
])
@pytest.mark.parametrize("method, path", [
    ("POST", "/api/transactions"),
    ("GET", "/api/transactions"),
    ("GET", "/api/transactions/1"),
])
def test_authorization(headers, method, path, transaction_payload):
    kwargs = {"json": transaction_payload} if method == "POST" else {}
    resp = requests.request(
        method,
        BASE_URL + path,
        headers=headers,
        timeout=TIMEOUT,
        **kwargs
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["data"] is None, resp.text
