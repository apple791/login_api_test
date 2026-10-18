"""接口测试配置；更换服务地址只需修改这里或设置环境变量。"""
import os

from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "instance" / "correct.db"

BASE_URL = os.environ.get("LOGIN_API_BASE_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT = 5
REGISTER_PATH = "/api/register"
LOGIN_PATH = "/api/login"
ME_PATH = "/api/me"
CHANGE_PASSWORD_PATH = "/api/change-password"
LOGOUT_PATH = "/api/logout"

REGISTER_URL = BASE_URL + REGISTER_PATH
LOGIN_URL = BASE_URL + LOGIN_PATH
ME_URL = BASE_URL + ME_PATH
CHANGE_PASSWORD_URL = BASE_URL + CHANGE_PASSWORD_PATH
LOGOUT_URL = BASE_URL + LOGOUT_PATH

TRANSACTIONS_PATH = "/api/transactions"
TRANSACTIONS_URL = BASE_URL + TRANSACTIONS_PATH
