import importlib.util
from threading import Thread

import pytest
import requests


def pytest_addoption(parser):
    parser.addoption('--bug-mode', default='correct',
                     choices=['correct', 'lower_bound', 'upper_bound', 'no_auth'])


@pytest.fixture
def api(tmp_path, request):
    assert importlib.util.find_spec('app') is not None, '尚未实现 Flask 应用'
    from app import create_app
    from werkzeug.serving import make_server
    app = create_app(tmp_path / 'users.db', request.config.getoption('--bug-mode'))
    server = make_server('127.0.0.1', 0, app)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    session = requests.Session()
    base = f'http://127.0.0.1:{server.server_port}'

    def call(method, path, **kwargs):
        return session.request(method, base + path, timeout=5, **kwargs)

    yield call
    session.close()
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()
