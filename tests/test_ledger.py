"""账本接口验收：使用独立临时数据库，不依赖正在运行的服务。"""
import sqlite3
import pytest
from app import create_app

@pytest.fixture
def ledger(tmp_path):
    db = tmp_path / "ledger.db"
    client = create_app(db).test_client()
    def account(name):
        data = {"username": name, "password": "abc12345"}
        assert client.post("/api/register", json=data).status_code == 201
        token = client.post("/api/login", json=data).json["data"]["token"]
        return {"Authorization": f"Bearer {token}"}
    return client, db, account("userA"), account("userB")

def payload(amount="12.50"):
    return dict(type="expense", amount=amount, category="food", date="2026-10-18", note="午餐")

@pytest.mark.parametrize("amount,status", [
    ("0.00",400),("0.01",201),("0.02",201),("999999.98",201),
    ("999999.99",201),("1000000.00",400),("100",201),("12.5",201),
    ("12.501",400),("",400),(" ",400),(None,400),(12,400),
    (12.5,400),(True,400),("中文",400),("@",400),("-1",400),
    ("1e2",400),("NaN",400),(" 12.50",400)])
def test_amount(ledger,amount,status):
    client,db,a,b=ledger
    response=client.post("/api/transactions",json=payload(amount),headers=a)
    assert response.status_code==status,response.text
    with sqlite3.connect(db) as conn:
        rows=conn.execute("SELECT amount_cents FROM transactions").fetchall()
    assert len(rows)==(1 if status==201 else 0)
    if status==201:
        assert rows[0][0]==int(__import__("decimal").Decimal(amount)*100)
    else:
        assert response.json["data"] is None

@pytest.mark.parametrize("field,value",[("amount",None),("type","other"),("category","salary"),
    ("date","2026-02-30"),("date","2026-1-1"),("note","a"*201),("note",None)])
def test_invalid_fields_do_not_insert(ledger,field,value):
    client,db,a,b=ledger
    data=payload();data[field]=value
    if field=="amount":data.pop(field)
    assert client.post("/api/transactions",json=data,headers=a).status_code==400
    with sqlite3.connect(db) as conn:assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0]==0

def test_lifecycle_and_isolation(ledger):
    client,db,a,b=ledger
    response=client.post("/api/transactions",json=payload(),headers=a)
    assert response.status_code==201
    record=response.json["data"];id=record["id"]
    assert record["amount"]=="12.50"
    assert client.get(f"/api/transactions/{id}",headers=a).json["data"]==record
    assert client.get(f"/api/transactions/{id}",headers=b).status_code==404
    assert client.get("/api/transactions/999999",headers=a).status_code==404
    assert client.get("/api/transactions",headers=b).json["data"]["total"]==0
    assert client.get("/api/transactions?type=income",headers=a).json["data"]["total"]==0
    assert client.get("/api/transactions?category=food&page=1&page_size=1",headers=a).json["data"]["items"]==[record]
    assert client.get(f"/api/transactions/{id}",headers=a).json["data"]==record

@pytest.mark.parametrize("method,path",[("post","/api/transactions"),("get","/api/transactions"),("get","/api/transactions/1")])
def test_auth_required(ledger,method,path):
    client,*_=ledger
    assert getattr(client,method)(path,json=payload()).status_code==401

@pytest.mark.parametrize("query",["page=0","page=x","page_size=101","type=x","category=x"])
def test_invalid_list_query(ledger,query):
    client,db,a,b=ledger
    assert client.get("/api/transactions?"+query,headers=a).status_code==400

def test_income_and_note_limit(ledger):
    client,db,a,b=ledger
    data=payload("100");data.update(type="income",category="salary",note="a"*200)
    assert client.post("/api/transactions",json=data,headers=a).status_code==201
