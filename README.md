# 账号接口自动化测试实践

个人学习项目：Flask 提供注册、登录、个人信息、改密和退出接口；Requests 发送真实 HTTP 请求，Pytest 组织测试。服务使用 SQLite 保存用户和会话。教学缺陷主动植入，不能描述为企业生产缺陷。

## 从哪里开始阅读

```text
login_api_test/
├── app.py                         # Flask 接口服务与教学缺陷模式
├── config.py                      # 服务地址、接口路径、完整URL、超时
├── conftest.py                    # registered_user、logged_in_user共享夹具
├── pytest.ini                     # 默认只收集 test_cases
├── test_cases/                     # 你在练习中编写的用例：17个函数、39条参数化用例
│   ├── test_register.py            # 注册密码边界、重复注册
│   ├── test_login.py               # 登录关联、异常密码、缺少密码
│   ├── test_me.py                  # 未携带Token查询
│   ├── test_change_password.py     # 改密、密码边界、多会话、跨账号影响
│   ├── test_logout.py              # 注销、重复退出、其他会话保持有效
│   └── test_auth.py                # 两个受保护接口的无效认证组合
├── tests/                         # 原有81条独立服务回归测试，显式运行
│   └── conftest.py                # 自动启动临时服务与独立数据库的夹具
├── practice/practice_login.py      # 最初的普通Python请求示例，不是测试入口
├── verify_modes.py                # 检查原有81条回归在四种模式下的预期结果
├── docs/                          # 规则、学习说明、缺陷与验证记录
├── reports/                       # HTML与JUnit报告
└── instance/                      # 手工启动服务时保存的数据库
```

先读 config.py → conftest.py → test_cases/test_register.py → test_login.py → 其他功能文件。无需先研究临时服务或线程。

## 启动和执行你的39条用例

在项目根目录打开终端，启动服务并保持运行：

```powershell
.\.venv\Scripts\python.exe app.py
```

另开一个终端执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -v --html=reports/practice.html --self-contained-html
```

pytest 默认执行 test_cases，不再使用旧的 practice/test_login.py。也可以只执行一类：

```powershell
.\.venv\Scripts\python.exe -m pytest test_cases/test_register.py -v
.\.venv\Scripts\python.exe -m pytest test_cases/test_change_password.py -v
```

默认地址 http://127.0.0.1:5001。更换服务地址时修改 config.py 的默认值，或设置环境变量：

```powershell
$env:LOGIN_API_BASE_URL = 'http://127.0.0.1:5002'
.\.venv\Scripts\python.exe -m pytest test_cases -v
```

环境变量只指定测试目标，服务也必须在对应端口运行。config.py 的 TIMEOUT 控制请求等待，路径常量控制各接口地址。需要JSON的请求使用 json=，认证信息使用 headers=。

## 夹具和数据

registered_user：每条使用它的用例注册一个随机用户名，固定合法密码为 abc12345，并检查201后返回账号字典。

logged_in_user：依赖 registered_user，登录并检查200，然后返回 user 和 token。默认函数作用域；参数化每组独立准备数据。

新用户名避免重复注册或改密互相干扰，但不会自动删除数据库数据。test_cases 请求的是手工启动的服务，练习数据保存在 instance/对应模式.db。不要用真实账号运行。

## 接口规则

| 请求 | 数据或认证 | 主要响应 |
|---|---|---|
| POST /api/register | JSON username、password | 201；400参数错误；409用户名重复 |
| POST /api/login | JSON username、password | 200返回data.token；400参数错误；401凭据不匹配 |
| GET /api/me | Bearer Token | 200返回id、username；401认证无效 |
| POST /api/change-password | Bearer Token；old_password、new_password | 200；400新密码不合法或与原密码相同；401认证无效或原密码错误 |
| POST /api/logout | Bearer Token，无需请求体 | 200；401认证无效或已退出 |

用户名：3～20位ASCII英文字母或数字，区分大小写，不重复。注册及新密码：6～16位ASCII英文字母或数字，包含上下限。允许纯字母、纯数字；不接受数字类型、null、空格、中文或符号。登录验证非空字符串及凭据，不重复应用注册长度规则。

修改密码成功后，该账号全部旧会话失效；失败时密码和会话保持有效。退出只注销当前Token，不改变密码及其他会话。JWT有效期1小时，每次登录有独立jti，与sessions表会话关联；重启服务后旧Token失效。

## 教学缺陷练习

停止现有服务，再选择一种模式启动，测试断言保持正确规则：

```powershell
.\.venv\Scripts\python.exe app.py --bug-mode lower_bound
```

| 模式 | 故意植入问题 | test_cases完整运行预期 |
|---|---|---|
| correct | 无主动缺陷 | 39通过 |
| lower_bound | 注册拒绝6位密码 | 38通过、1失败 |
| upper_bound | 注册遗漏16位上限 | 38通过、1失败（当前只测17位超长） |
| no_auth | 无Token查询被放行，返回guest | 38通过、1失败 |

改密接口不额外植入密码边界缺陷。切换correct是与正确实现对照，不代表亲自修复了错误代码。保留错误模式用于重复练习。

## 原有回归测试

tests目录为原有81条回归，与你的39条用例有覆盖重叠，不能合并宣传为120条独立场景。它自动为每条用例准备临时数据库和随机本机端口，不需要手工启动服务，也不读取config.py中的目标地址。

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe verify_modes.py
```

verify_modes.py显式运行tests，维持其81条及预期失败数量。历史docs/测试用例.md和docs/验证结果.md描述这套回归；docs/目录整理验证.md记录本次39条迁移验证。

## 安装与项目性质

本机解释器为 .venv/Scripts/python.exe。复制到其他电脑：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Flask服务在AI辅助下搭建。test_cases保存你在指导中逐步设计、编写和执行的练习。简历可如实描述个人接口测试实训、用例设计、参数化、fixture、接口关联、缺陷复现与回归；SQL数据核对、自然过期和并发场景尚需继续学习。