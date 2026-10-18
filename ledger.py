"""账本业务：金额以整数分保存，所有查询限定当前用户。"""
from datetime import date
from decimal import Decimal
import re
from flask import request

CATEGORIES = {
    'income': ['salary', 'bonus', 'other_income'],
    'expense': ['food', 'transport', 'shopping', 'other_expense'],
}


def parse_amount(value):
    # 字符串协议：不接受空格、符号、科学计数法或超过两位的小数。
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,6}(?:\.[0-9]{1,2})?', value):
        return None
    cents = int(Decimal(value) * 100)
    return cents if 1 <= cents <= 99999999 else None


def register_ledger_routes(app, connect, current_session, reply, body):
    with connect() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id))''')

    def record_data(row):
        cents = row['amount_cents']
        return {'id': row['id'], 'type': row['type'],
                'amount': f'{cents // 100}.{cents % 100:02d}',
                'category': row['category'], 'date': row['date'], 'note': row['note']}

    @app.post('/api/transactions')
    def create_transaction():
        user, _ = current_session()
        if user is None:
            return reply(401, '缺少或无效的Token')
        data = body()
        kind, category = data.get('type'), data.get('category')
        if not isinstance(kind, str) or kind not in CATEGORIES:
            return reply(400, 'type必须为income或expense')
        cents = parse_amount(data.get('amount'))
        if cents is None:
            return reply(400, 'amount必须为0.01到999999.99的金额字符串，最多两位小数')
        if not isinstance(category, str) or category not in CATEGORIES[kind]:
            return reply(400, 'category必须属于对应的收支类型')
        observed_date = data.get('date')
        if not isinstance(observed_date, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', observed_date):
            return reply(400, 'date必须为YYYY-MM-DD格式的有效日期')
        try:
            date.fromisoformat(observed_date)
        except ValueError:
            return reply(400, 'date必须为真实有效的日期')
        note = data.get('note', '')
        if not isinstance(note, str) or len(note) > 200:
            return reply(400, 'note必须为不超过200个字符的字符串')
        # 所有校验完成后才写入，用户归属只从Token读取。
        with connect() as conn:
            cursor = conn.execute(
                'INSERT INTO transactions(user_id,type,amount_cents,category,date,note) VALUES (?,?,?,?,?,?)',
                (user['id'], kind, cents, category, observed_date, note))
            row = conn.execute('SELECT * FROM transactions WHERE id=?', (cursor.lastrowid,)).fetchone()
        return reply(201, '新增成功', record_data(row))

    @app.get('/api/transactions')
    def list_transactions():
        user, _ = current_session()
        if user is None:
            return reply(401, '缺少或无效的Token')
        page_text, size_text = request.args.get('page', '1'), request.args.get('page_size', '20')
        if not re.fullmatch(r'[0-9]{1,9}', page_text) or not re.fullmatch(r'[0-9]{1,3}', size_text):
            return reply(400, '分页参数必须为正整数')
        page, size = int(page_text), int(size_text)
        if page < 1 or not 1 <= size <= 100:
            return reply(400, 'page必须大于0，page_size必须为1到100')
        clauses, values = ['user_id=?'], [user['id']]
        for field, allowed in [('type', CATEGORIES), ('category', sum(CATEGORIES.values(), []))]:
            value = request.args.get(field)
            if value is not None:
                if value not in allowed:
                    return reply(400, f'{field}筛选值无效')
                clauses.append(f'{field}=?')
                values.append(value)
        where = ' AND '.join(clauses)
        with connect() as conn:
            total = conn.execute('SELECT COUNT(*) FROM transactions WHERE ' + where, values).fetchone()[0]
            rows = conn.execute('SELECT * FROM transactions WHERE ' + where + ' ORDER BY id DESC LIMIT ? OFFSET ?',
                                values + [size, (page - 1) * size]).fetchall()
        return reply(200, '查询成功', {'items': [record_data(row) for row in rows],
                                   'total': total, 'page': page, 'page_size': size})

    @app.get('/api/transactions/<int:record_id>')
    def get_transaction(record_id):
        user, _ = current_session()
        if user is None:
            return reply(401, '缺少或无效的Token')
        with connect() as conn:
            row = conn.execute('SELECT * FROM transactions WHERE id=? AND user_id=?',
                               (record_id, user['id'])).fetchone()
        if row is None:
            return reply(404, '记录不存在')
        return reply(200, '查询成功', record_data(row))
