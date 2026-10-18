"""通过真实HTTP创建数据，再以SQL核对入库、筛选及分类汇总结果。"""
import uuid

import pytest
import requests

from config import (
    LOGIN_URL,
    ME_URL,
    REGISTER_URL,
    TIMEOUT,
    TRANSACTIONS_URL,
)


@pytest.fixture
def ledger_account(logged_in_user):
    """获取当前账号的身份，确保SQL限定到本条用例所属用户。"""
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    response = requests.get(ME_URL, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    user = response.json()["data"]
    assert user["username"] == logged_in_user["user"]["username"], response.text
    return {"headers": headers, "user_id": user["id"]}


def count_user_transactions(connection, user_id):
    """只统计当前用户，避免其他账号的并行请求影响断言。"""
    return connection.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0]


@pytest.mark.parametrize(
    "amount",
    [
        pytest.param("0.00", id="below-minimum"),
        pytest.param("1000000.00", id="above-maximum"),
        pytest.param("12.501", id="too-many-decimal-places"),
        pytest.param("", id="empty-string"),
        pytest.param(None, id="null"),
        pytest.param(100, id="number-instead-of-string"),
    ],
)
def test_invalid_amount_not_saved_in_db(
    amount, ledger_account, transaction_payload, db_connection
):
    user_id = ledger_account["user_id"]
    before_count = count_user_transactions(db_connection, user_id)
    transaction_payload.update(amount=amount, note="非法金额入库检查")

    response = requests.post(
        TRANSACTIONS_URL,
        json=transaction_payload,
        headers=ledger_account["headers"],
        timeout=TIMEOUT,
    )
    assert response.status_code == 400, response.text
    assert response.json()["data"] is None, response.text

    after_count = count_user_transactions(db_connection, user_id)
    assert after_count == before_count, (
        f"非法请求后用户{user_id}的记录数发生变化："
        f"请求前={before_count}，请求后={after_count}"
    )


@pytest.mark.parametrize(
    "amount, expected_cents",
    [
        pytest.param("0.01", 1, id="minimum-amount"),
        pytest.param("12.5", 1250, id="one-decimal-place"),
        pytest.param("100", 10000, id="integer-string"),
        pytest.param("999999.99", 99999999, id="maximum-amount"),
    ],
)
def test_amount_saved_as_integer_cents(
    amount, expected_cents, ledger_account, transaction_payload, db_connection
):
    user_id = ledger_account["user_id"]
    before_count = count_user_transactions(db_connection, user_id)
    transaction_payload.update(amount=amount, note="数据库核对")

    response = requests.post(
        TRANSACTIONS_URL,
        json=transaction_payload,
        headers=ledger_account["headers"],
        timeout=TIMEOUT,
    )
    assert response.status_code == 201, response.text
    record_id = response.json()["data"]["id"]

    row = db_connection.execute(
        """
        SELECT id, user_id, type, amount_cents, category, date, note
        FROM transactions
        WHERE id = ?
        """,
        (record_id,),
    ).fetchone()
    assert row is not None, f"新增返回201，但数据库未找到记录：{record_id}"
    assert dict(row) == {
        "id": record_id,
        "user_id": user_id,
        "type": transaction_payload["type"],
        "amount_cents": expected_cents,
        "category": transaction_payload["category"],
        "date": transaction_payload["date"],
        "note": transaction_payload["note"],
    }, dict(row)
    assert count_user_transactions(db_connection, user_id) == before_count + 1


def test_expense_list_matches_db(
    three_transactions, ledger_account, db_connection
):
    headers = three_transactions["headers"]
    response = requests.get(
        TRANSACTIONS_URL,
        params={"type": "expense", "page": 1, "page_size": 20},
        headers=headers,
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, response.text
    result = response.json()["data"]

    rows = db_connection.execute(
        """
        SELECT id, type, amount_cents, category, date, note
        FROM transactions
        WHERE user_id = ? AND type = ?
        ORDER BY id DESC
        """,
        (ledger_account["user_id"], "expense"),
    ).fetchall()
    # 夹具只创建三条记录，其中两条支出，小于本次请求的每页20条。
    assert len(rows) == 2, [dict(row) for row in rows]
    expected_ids = [record["id"] for record in reversed(three_transactions["records"])
                    if record["type"] == "expense"]
    assert [row["id"] for row in rows] == expected_ids
    expected_items = [
        {
            "id": row["id"],
            "type": row["type"],
            "amount": f"{row['amount_cents'] // 100}.{row['amount_cents'] % 100:02d}",
            "category": row["category"],
            "date": row["date"],
            "note": row["note"],
        }
        for row in rows
    ]
    assert result["total"] == len(rows), response.text
    assert result["items"] == expected_items, response.text


def test_category_totals_exclude_other_users(
    three_transactions, ledger_account, transaction_payload, db_connection
):
    # 用户A已有20元餐饮和10元交通，再增加5.50元餐饮。
    transaction_payload.update(amount="5.50", note="数据库核对")
    response = requests.post(
        TRANSACTIONS_URL,
        json=transaction_payload,
        headers=ledger_account["headers"],
        timeout=TIMEOUT,
    )
    assert response.status_code == 201, response.text

    credentials = {"username": "u" + uuid.uuid4().hex[:12], "password": "abc12345"}
    response = requests.post(REGISTER_URL, json=credentials, timeout=TIMEOUT)
    assert response.status_code == 201, response.text
    other_user_id = response.json()["data"]["id"]
    assert other_user_id != ledger_account["user_id"]

    response = requests.post(LOGIN_URL, json=credentials, timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    other_headers = {"Authorization": f"Bearer {response.json()['data']['token']}"}
    other_payload = {**transaction_payload, "amount": "100.00", "note": "其他用户的支出"}
    response = requests.post(
        TRANSACTIONS_URL, json=other_payload, headers=other_headers, timeout=TIMEOUT
    )
    assert response.status_code == 201, response.text
    other_record_id = response.json()["data"]["id"]

    # 确认干扰数据实际归属B，而非只根据接口返回201推断。
    other_record = db_connection.execute(
        "SELECT user_id, amount_cents FROM transactions WHERE id = ?",
        (other_record_id,),
    ).fetchone()
    assert other_record is not None, f"用户B的干扰数据未入库：{other_record_id}"
    assert dict(other_record) == {"user_id": other_user_id, "amount_cents": 10000}

    rows = db_connection.execute(
        """
        SELECT category, SUM(amount_cents) AS total_cents
        FROM transactions
        WHERE user_id = ? AND type = ?
        GROUP BY category
        """,
        (ledger_account["user_id"], "expense"),
    ).fetchall()
    actual = {row["category"]: row["total_cents"] for row in rows}
    assert actual == {"food": 2550, "transport": 1000}, actual
