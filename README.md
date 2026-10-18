# 账号与收支账本接口自动化测试

用于初级接口测试学习的本地Flask项目。账号功能包含注册、登录、个人信息、改密与退出；账本第一阶段包含新增收支、列表筛选、分页和详情查询。采用Requests、Pytest、SQLite；账本金额以整数分保存，查询按用户隔离。

## 安装与启动

```powershell
python -m pip install -r requirements.txt
python app.py
```

默认地址 http://127.0.0.1:5001；重启后旧Token失效。数据库保存在instance/correct.db。

## 运行测试

```powershell
# 先启动服务，默认运行你练习编写并整理的HTTP用例
python -m pytest -v
# 单独运行金额用例
python -m pytest test_cases/test_transaction_amount.py -v
# 单独运行接口与数据库核对
python -m pytest test_cases/test_transaction_db.py -v
# 查看参数化展开后的实际数量（不执行用例）
python -m pytest test_cases --collect-only -q
# 生成HTML报告
python -m pytest --html=reports/http.html --self-contained-html
# 独立服务验收：自动启动临时服务/数据库，不依赖上面的手工服务
python -m pytest tests -q
```

BASE_URL、DB_PATH和超时集中在config.py。可通过LOGIN_API_BASE_URL环境变量更换目标服务；DB_PATH目前在config.py中配置，不会随服务地址自动变化。运行SQL核对时，必须连接目标服务实际使用的数据库。本项目默认是本地correct模式与instance/correct.db配套，远程服务不能直接使用本地数据库核对。根conftest.py负责共享账号、登录、请求体和列表数据夹具。账号每条用例独立创建，避免改密、退出等状态互相干扰。

## 目录

```text
app.py                 账号服务及应用入口
ledger.py              账本参数校验与三个业务接口
config.py              HTTP地址、数据库路径与超时
conftest.py            共享测试夹具
test_cases/            真实HTTP练习与验收用例
  test_register.py / test_login.py / test_me.py
  test_auth.py / test_logout.py / test_change_password.py
  test_transaction_create.py
  test_transaction_amount.py
  test_transaction_permissions.py
  test_transaction_sessions.py
  test_transaction_list.py
  test_transaction_db.py             SQL入库、筛选与分类汇总核对
check_db.py            手工SQL查询示例（固定ID，非自动化入口）
tests/                 独立账号回归与账本服务验收
docs/                  接口、缺陷与学习说明
instance/              本地练习数据库（不提交）
reports/               执行报告
```

## 教学缺陷模式

```powershell
python app.py --bug-mode lower_bound
python app.py --bug-mode upper_bound
python app.py --bug-mode no_auth
```

correct为正常模式；lower_bound错误拒绝6位注册密码，upper_bound遗漏注册密码上限，no_auth错误放行未登录的个人信息查询。每种模式使用独立数据库，缺陷模式中的预期测试失败不应修改断言来迎合。账本接口不主动植入缺陷，始终验证身份。verify_modes.py用于原账号教学模式回归。

## 用例与成果说明

截至2026-10-18，Pytest参数化展开后的数量如下：

| 入口 | 覆盖范围 | 用例数 | 最近验证 |
|---|---|---:|---|
| test_cases 账号六个文件 | 注册、登录、个人信息、鉴权、退出、改密 | 39 | 通过 |
| test_cases 账本接口五个文件 | 新增、金额、权限、会话、列表 | 56 | 通过 |
| test_cases/test_transaction_db.py | 入库、拒绝后不入库、列表一致性、分类汇总 | 12 | 通过 |
| test_cases 总计 | 默认主测试入口 | 107 | 107通过 |
| tests 账号服务验收 | 自动启动临时HTTP服务 | 81 | 通过 |
| tests/test_ledger.py | 临时数据库与Flask测试客户端 | 38 | 通过 |
| tests 总计 | 独立服务验收入口 | 119 | 119通过 |

两套用例存在覆盖重叠，不相加宣传为独立业务场景。数量来自实际收集，并非测试函数数量。107条主测试最近在单独临时服务及其对应数据库上通过；119条服务验收结果来自本阶段此前运行。四种教学模式未在此次文档整理中重新执行。历史报告中的39、81、95、106等数字仅表示当时范围；106条不含曾因嵌套缩进而漏收集的列表SQL测试，当前已修正。

SQL测试核对记录归属、整数分金额、完整入库字段、失败请求不新增记录、列表与数据库一致及分类汇总。分类汇总属于测试中的SQL检查，不代表项目提供了统计接口；修改、删除与统计接口尚未实现。

账号与账本服务由AI辅助实现；test_cases以个人练习为基础整理，需理解、运行并能解释后再作为个人能力介绍。

## 文档导航

- [测试用例](docs/测试用例.md)：当前逐文件数量及覆盖。
- [账本接口第一阶段](docs/账本接口第一阶段.md)：接口规则和请求示例。
- [学习顺序](docs/学习顺序.md)：账号、账本、SQL阅读路径。
- [用例整理说明](docs/用例整理说明.md)：当前结构、夹具与数据管理。
- [账号功能说明](docs/账号功能说明.md)、[教学缺陷记录](docs/缺陷记录.md)：账号规则与主动植入缺陷。
- [历史验证结果](docs/验证结果.md)、[历史目录整理验证](docs/目录整理验证.md)：保留当时数据，不作为当前全量报告。

reports内HTML/XML保留各自生成时间和范围，文件名不能作为最新结果依据；重新执行会覆盖同名报告。根目录check_db.py只是手工查询练习，其固定记录ID和预期金额需按本机数据修改，不纳入Pytest用例数。
