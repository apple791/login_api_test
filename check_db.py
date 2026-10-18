import sqlite3
from pathlib import Path

# 使用正常模式的数据库
db_path = Path(__file__).resolve().parent / "instance" / "correct.db"

# 避免路径错误时，sqlite3 自动创建一个空数据库
if not db_path.is_file():
    raise FileNotFoundError(f"数据库不存在：{db_path}")

conn = sqlite3.connect(db_path)

conn.row_factory = sqlite3.Row

record_id = 195

try:
    cursor = conn.execute(
        """
        SELECT id, user_id, type, amount_cents, category, date, note
        FROM transactions
        WHERE id = ?
        """,
        (record_id,)
    )

    row = cursor.fetchone()

    assert row is not None, f"记录不存在：{record_id}"

    print(dict(row))
    assert row["amount_cents"] == 2500, dict(row)
    assert row["category"] == "food", dict(row)
finally:
    conn.close()