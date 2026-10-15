"""本地教学服务：先读路由，再读校验和存储。"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import secrets
import sqlite3

from flask import Flask, jsonify, request
import jwt
from werkzeug.security import check_password_hash, generate_password_hash

MODES = ['correct', 'lower_bound', 'upper_bound', 'no_auth']


def valid_text(value, minimum, maximum):
    """只接受指定长度的 ASCII 字母数字字符串，不做隐式转换或去空格。"""
    return (isinstance(value, str) and minimum <= len(value) <= maximum
            and re.fullmatch(r'[A-Za-z0-9]+', value) is not None)


def create_app(db_path, bug_mode='correct'):
    if bug_mode not in MODES:
        raise ValueError('未知缺陷模式')
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secrets.token_hex(32)
    db_path = Path(db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    with connect() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS users ('
                     'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                     'username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)')
        # 每次登录保存一个独立会话；删除记录即可让对应 Token 失效。
        conn.execute('CREATE TABLE IF NOT EXISTS sessions ('
                     'token_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL)')

    def reply(code, message, data=None):
        return jsonify(code=code, message=message, data=data), code

    def body():
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    def current_session():
        """共同的登录校验：JWT 有效，并且会话记录仍然存在。"""
        parts = request.headers.get('Authorization', '').split()
        if len(parts) != 2 or parts[0] != 'Bearer':
            return None, None
        try:
            payload = jwt.decode(parts[1], app.config['SECRET_KEY'], algorithms=['HS256'],
                                 options={'require': ['sub', 'iat', 'exp', 'jti']})
        except jwt.InvalidTokenError:
            return None, None
        with connect() as conn:
            user = conn.execute(
                'SELECT users.* FROM users JOIN sessions ON users.id=sessions.user_id '
                'WHERE sessions.token_id=? AND users.id=?',
                (payload['jti'], payload['sub'])).fetchone()
        return user, payload['jti']

    @app.post('/api/register')
    def register():
        data = body()
        username, password = data.get('username'), data.get('password')
        if not valid_text(username, 3, 20):
            return reply(400, '用户名必须为3到20位英文字母或数字')

        minimum, maximum = 6, 16
        # 教学缺陷 B01：错误地把包含6位的下限改成7位。
        if bug_mode == 'lower_bound':
            minimum = 7
        # 教学缺陷 B02：遗漏16位上限；字符和类型规则仍保持不变。
        if bug_mode == 'upper_bound':
            maximum = len(password) if isinstance(password, str) else 16
        if not valid_text(password, minimum, maximum):
            return reply(400, '密码必须为6到16位英文字母或数字')
        password_hash = generate_password_hash(password)
        try:
            with connect() as conn:
                cursor = conn.execute('INSERT INTO users(username,password_hash) VALUES (?,?)',
                                      (username, password_hash))
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return reply(409, '用户名已存在')
        return reply(201, '注册成功', {'id': user_id, 'username': username})

    @app.post('/api/login')
    def login():
        data = body()
        username, password = data.get('username'), data.get('password')
        # 登录校验凭据，而不是重复套用注册长度规则。
        if not isinstance(username, str) or not isinstance(password, str) or not username or not password:
            return reply(400, '用户名和密码必须为非空字符串')
        with connect() as conn:
            user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if user is None or not check_password_hash(user['password_hash'], password):
            return reply(401, '用户名或密码错误')
        now = datetime.now(timezone.utc)
        token_id = secrets.token_hex(16)
        token = jwt.encode({'sub': str(user['id']), 'iat': now,
                            'exp': now + timedelta(hours=1), 'jti': token_id},
                           app.config['SECRET_KEY'], algorithm='HS256')
        with connect() as conn:
            conn.execute('INSERT INTO sessions(token_id,user_id) VALUES (?,?)',
                         (token_id, user['id']))
        return reply(200, '登录成功', {'token': token})

    @app.get('/api/me')
    def me():
        header = request.headers.get('Authorization', '')
        # 教学缺陷 B03：缺少Token时错误放行，返回虚拟访客，不暴露真实用户。
        if bug_mode == 'no_auth' and not header:
            return reply(200, '错误放行未登录请求', {'id': None, 'username': 'guest'})
        user, _ = current_session()
        if user is None:
            return reply(401, '缺少或无效的Token')
        return reply(200, '查询成功', {'id': user['id'], 'username': user['username']})

    @app.post('/api/change-password')
    def change_password():
        user, _ = current_session()
        if user is None:
            return reply(401, '缺少或无效的Token')
        data = body()
        old_password, new_password = data.get('old_password'), data.get('new_password')
        if not isinstance(old_password, str) or not old_password:
            return reply(400, '原密码必须为非空字符串')
        if not valid_text(new_password, 6, 16):
            return reply(400, '新密码必须为6到16位英文字母或数字')
        if not check_password_hash(user['password_hash'], old_password):
            return reply(401, '原密码错误')
        if new_password == old_password:
            return reply(400, '新密码不能与原密码相同')
        with connect() as conn:
            conn.execute('UPDATE users SET password_hash=? WHERE id=?',
                         (generate_password_hash(new_password), user['id']))
            # 修改密码与注销全部会话在同一个事务中完成。
            conn.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
        return reply(200, '密码修改成功，请重新登录')

    @app.post('/api/logout')
    def logout():
        user, token_id = current_session()
        if user is None:
            return reply(401, '缺少或无效的Token')
        with connect() as conn:
            conn.execute('DELETE FROM sessions WHERE token_id=?', (token_id,))
        return reply(200, '退出成功')

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='仅用于本地教学的登录接口服务')
    parser.add_argument('--bug-mode', choices=MODES, default='correct')
    parser.add_argument('--port', type=int, default=5001)
    args = parser.parse_args()
    # 各模式分开保存练习数据；重启后旧 Token 失效，需要重新登录。
    db = Path(__file__).parent / 'instance' / f'{args.bug_mode}.db'
    print(f'运行模式: {args.bug_mode}，地址: http://127.0.0.1:{args.port}')
    create_app(db, args.bug_mode).run(host='127.0.0.1', port=args.port, debug=False)
