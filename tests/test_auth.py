"""全部通过真实 HTTP 请求测试本地 Flask；每条用例有独立数据库。"""
import pytest


@pytest.mark.parametrize('length,expected', [(3,400),(5,400),(6,201),(7,201),
                                          (10,201),(15,201),(16,201),(17,400),(20,400)],
                         ids=lambda x: str(x))
def test_password_length(api, length, expected):
    result = api('POST', '/api/register', json={'username':'learner','password':'a' * length})
    assert result.status_code == expected, f'密码长度 {length}: {result.text}'


@pytest.mark.parametrize('password', [None, '', 123456, True, [], {}, 'abc def', '中文密码测试', 'abc!123'])
def test_invalid_password(api, password):
    assert api('POST','/api/register',json={'username':'learner','password':password}).status_code == 400


def test_missing_password(api):
    assert api('POST','/api/register',json={'username':'learner'}).status_code == 400


@pytest.mark.parametrize('length,expected', [(2,400),(3,201),(4,201),(19,201),(20,201),(21,400)])
def test_username_length(api, length, expected):
    assert api('POST','/api/register',json={'username':'u' * length,'password':'abc12345'}).status_code == expected


@pytest.mark.parametrize('body', [None, [], {'password':'abc12345'}, {'username':None,'password':'abc12345'},
                               {'username':123,'password':'abc12345'}, {'username':'abc def','password':'abc12345'}])
def test_invalid_register_body(api, body):
    assert api('POST','/api/register',json=body).status_code == 400


def test_duplicate_username(api):
    data = {'username':'learner','password':'abc12345'}
    assert api('POST','/api/register',json=data).status_code == 201
    assert api('POST','/api/register',json=data).status_code == 409


def test_register_login_me(api):
    data = {'username':'learner','password':'abc12345'}
    created = api('POST','/api/register',json=data)
    assert created.status_code == 201
    result = api('POST','/api/login',json=data)
    assert result.status_code == 200
    token = result.json()['data']['token']
    assert isinstance(token,str) and token
    me = api('GET','/api/me',headers={'Authorization':f'Bearer {token}'})
    assert me.status_code == 200
    assert me.json()['data'] == created.json()['data']
    assert set(me.json()['data']) == {'id','username'}


@pytest.mark.parametrize('credentials', [{'username':'unknown','password':'abc12345'},
                                       {'username':'learner','password':'wrong123'}])
def test_wrong_credentials(api, credentials):
    assert api('POST','/api/register',json={'username':'learner','password':'abc12345'}).status_code == 201
    result = api('POST','/api/login',json=credentials)
    assert result.status_code == 401
    assert result.json()['message'] == '用户名或密码错误'
    assert result.json()['data'] is None


@pytest.mark.parametrize('body', [{}, {'username':'learner'}, {'username':'learner','password':None},
                               {'username':'learner','password':123456}, []])
def test_invalid_login_body(api, body):
    assert api('POST','/api/login',json=body).status_code == 400


def test_missing_token(api):
    assert api('GET','/api/me').status_code == 401


@pytest.mark.parametrize('header', ['Bearer invalid-token','invalid','Basic abc','Bearer '])
def test_invalid_token(api, header):
    assert api('GET','/api/me',headers={'Authorization':header}).status_code == 401

