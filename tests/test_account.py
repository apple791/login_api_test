"""账号升级：通过真实 HTTP 验证改密和退出后的状态变化。"""
import pytest


@pytest.fixture
def account(api):
    credentials = {'username': 'learner', 'password': 'abc12345'}
    assert api('POST', '/api/register', json=credentials).status_code == 201
    result = api('POST', '/api/login', json=credentials)
    assert result.status_code == 200
    return {'Authorization': 'Bearer ' + result.json()['data']['token']}


@pytest.mark.parametrize('length,expected', [(3,400),(5,400),(6,200),(7,200),
                                          (10,200),(15,200),(16,200),(17,400),(20,400)])
def test_new_password_length(api, account, length, expected):
    password = 'b' * length
    result = api('POST', '/api/change-password', headers=account,
                 json={'old_password': 'abc12345', 'new_password': password})
    assert result.status_code == expected
    # 不只核对状态码，还确认实际保存的是哪个密码。
    valid_password = password if expected == 200 else 'abc12345'
    assert api('POST', '/api/login', json={'username': 'learner', 'password': valid_password}).status_code == 200


@pytest.mark.parametrize('value', [None, '', 123456, True, [], {}, 'abc def', '中文密码测试', 'abc!123'])
def test_invalid_new_password(api, account, value):
    result = api('POST', '/api/change-password', headers=account,
                 json={'old_password': 'abc12345', 'new_password': value})
    assert result.status_code == 400
    assert api('GET', '/api/me', headers=account).status_code == 200
    assert api('POST', '/api/login', json={'username': 'learner', 'password': 'abc12345'}).status_code == 200


@pytest.mark.parametrize('body', [None, [], {}, {'old_password': 'abc12345'},
    {'new_password': 'new12345'}, {'old_password': None, 'new_password': 'new12345'},
    {'old_password': 123456, 'new_password': 'new12345'},
    {'old_password': '', 'new_password': 'new12345'}])
def test_invalid_change_body(api, account, body):
    assert api('POST', '/api/change-password', headers=account, json=body).status_code == 400
    assert api('GET', '/api/me', headers=account).status_code == 200


@pytest.mark.parametrize('old,new,expected', [('wrong123', 'new12345', 401),
                                           ('abc12345', 'abc12345', 400)])
def test_rejected_change_keeps_credentials(api, account, old, new, expected):
    assert api('POST', '/api/change-password', headers=account,
               json={'old_password': old, 'new_password': new}).status_code == expected
    assert api('GET', '/api/me', headers=account).status_code == 200
    assert api('POST', '/api/login', json={'username': 'learner', 'password': 'abc12345'}).status_code == 200


def test_change_revokes_all_sessions_only_for_current_user(api, account):
    second = api('POST', '/api/login', json={'username': 'learner', 'password': 'abc12345'})
    assert second.status_code == 200
    second_header = {'Authorization': 'Bearer ' + second.json()['data']['token']}
    other = {'username': 'another', 'password': 'abc12345'}
    assert api('POST', '/api/register', json=other).status_code == 201
    other_login = api('POST', '/api/login', json=other)
    assert other_login.status_code == 200
    other_header = {'Authorization': 'Bearer ' + other_login.json()['data']['token']}
    assert api('POST', '/api/change-password', headers=account,
               json={'old_password': 'abc12345', 'new_password': 'new12345'}).status_code == 200
    for header in [account, second_header]:
        assert api('GET', '/api/me', headers=header).status_code == 401
        assert api('POST', '/api/logout', headers=header).status_code == 401
        assert api('POST', '/api/change-password', headers=header,
                   json={'old_password': 'new12345', 'new_password': 'next1234'}).status_code == 401
    assert api('POST', '/api/login', json={'username': 'learner', 'password': 'abc12345'}).status_code == 401
    fresh = api('POST', '/api/login', json={'username': 'learner', 'password': 'new12345'})
    assert fresh.status_code == 200
    assert api('GET', '/api/me', headers={'Authorization': 'Bearer ' + fresh.json()['data']['token']}).status_code == 200
    assert api('GET', '/api/me', headers=other_header).status_code == 200


def test_logout_revokes_only_current_session(api, account):
    credentials = {'username': 'learner', 'password': 'abc12345'}
    second = api('POST', '/api/login', json=credentials)
    assert second.status_code == 200
    second_header = {'Authorization': 'Bearer ' + second.json()['data']['token']}
    assert second_header != account  # 连续登录也必须生成独立令牌。
    other = {'username': 'another', 'password': 'abc12345'}
    assert api('POST', '/api/register', json=other).status_code == 201
    other_login = api('POST', '/api/login', json=other)
    assert other_login.status_code == 200
    other_header = {'Authorization': 'Bearer ' + other_login.json()['data']['token']}
    result = api('POST', '/api/logout', headers=account)
    assert result.status_code == 200
    assert api('GET', '/api/me', headers=account).status_code == 401
    assert api('POST', '/api/logout', headers=account).status_code == 401
    assert api('POST', '/api/change-password', headers=account,
               json={'old_password': 'abc12345', 'new_password': 'new12345'}).status_code == 401
    assert api('GET', '/api/me', headers=second_header).status_code == 200
    assert api('GET', '/api/me', headers=other_header).status_code == 200
    assert api('POST', '/api/login', json=credentials).status_code == 200


@pytest.mark.parametrize('path', ['/api/change-password', '/api/logout'])
@pytest.mark.parametrize('headers', [{}, {'Authorization': 'Bearer invalid-token'},
                                   {'Authorization': 'Basic abc'}])
def test_account_requires_valid_token(api, path, headers):
    assert api('POST', path, headers=headers,
               json={'old_password': 'abc12345', 'new_password': 'new12345'}).status_code == 401
