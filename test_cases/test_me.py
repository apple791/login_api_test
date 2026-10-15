"""按功能整理的接口测试用例。"""
import requests

from config import (
    TIMEOUT,
    ME_URL,
)


def test_get_me_without_token():
    resp = requests.get(
        ME_URL,
        timeout=TIMEOUT
    )

    assert resp.status_code == 401, resp.text
