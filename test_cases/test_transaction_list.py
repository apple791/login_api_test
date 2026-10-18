"""列表筛选和分页分别验证，失败时可以直接定位具体场景。"""
import pytest
import requests
from config import TRANSACTIONS_URL, TIMEOUT


@pytest.mark.parametrize("kind,indexes", [("income", [0]), ("expense", [2, 1])])
def test_list_filter_type(three_transactions, kind, indexes):
    context = three_transactions
    resp = requests.get(TRANSACTIONS_URL, params={"type": kind},
                        headers=context["headers"], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    result = resp.json()["data"]
    expected = [context["records"][i] for i in indexes]
    assert result["total"] == len(expected), resp.text
    assert result["items"] == expected, resp.text


@pytest.mark.parametrize("kind,category,indexes", [
    ("expense", "food", [1]),
    ("expense", "transport", [2]),
    ("income", "food", []),
])
def test_list_combined_filter(three_transactions, kind, category, indexes):
    context = three_transactions
    resp = requests.get(TRANSACTIONS_URL, params={"type": kind, "category": category},
                        headers=context["headers"], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    expected = [context["records"][i] for i in indexes]
    assert resp.json()["data"]["total"] == len(expected), resp.text
    assert resp.json()["data"]["items"] == expected, resp.text


@pytest.mark.parametrize("page,indexes", [(1, [2, 1]), (2, [0]), (3, [])])
def test_list_pagination(three_transactions, page, indexes):
    context = three_transactions
    resp = requests.get(TRANSACTIONS_URL, params={"page": page, "page_size": 2},
                        headers=context["headers"], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    result = resp.json()["data"]
    assert result["total"] == 3, resp.text
    assert result["page"] == page, resp.text
    assert result["page_size"] == 2, resp.text
    assert result["items"] == [context["records"][i] for i in indexes], resp.text


@pytest.mark.parametrize("params", [
    {"page": 0}, {"page": -1}, {"page": "abc"},
    {"page_size": 0}, {"page_size": 101}, {"page_size": "1.5"},
    {"type": "invalid"}, {"category": "invalid"},
])
def test_list_invalid_query(logged_in_user, params):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    resp = requests.get(TRANSACTIONS_URL, params=params, headers=headers, timeout=TIMEOUT)
    assert resp.status_code == 400, resp.text
    assert resp.json()["data"] is None, resp.text


def test_list_empty_account(logged_in_user):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    resp = requests.get(TRANSACTIONS_URL, headers=headers, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {"items": [], "total": 0, "page": 1, "page_size": 20}, resp.text
