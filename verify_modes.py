from pathlib import Path
import subprocess,sys,xml.etree.ElementTree as E
root=Path(__file__).resolve().parent
expected={'correct':0,'lower_bound':1,'upper_bound':2,'no_auth':1}
rows=[]
for mode,failures in expected.items():
    report=root/'reports'/f'{mode}.xml'
    cmd=[sys.executable,'-m','pytest','tests','-q','--bug-mode',mode,'--tb=short',f'--junitxml={report}',f'--html=reports/{mode}.html','--self-contained-html']
    run=subprocess.run(cmd,cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace')
    suite=E.parse(report).find('testsuite')
    actual={k:int(suite.get(k,0)) for k in ['tests','failures','errors','skipped']}
    print(mode,actual,'exit',run.returncode,flush=True)
    if actual!={'tests':81,'failures':failures,'errors':0,'skipped':0} or run.returncode!=(1 if failures else 0):
        print(run.stdout);print(run.stderr);raise SystemExit('Unexpected verification result')
    failed=[t.get('name') for t in suite.findall('testcase') if t.find('failure') is not None]
    rows.append(f'| {mode} | {81-failures} | {failures} | '+(', '.join(failed) or '无')+' |')
(root/'docs'/'验证结果.md').write_text('# 实际验证结果\n\n2026-10-11，本地 Requests 真实 HTTP 测试，每种模式运行同一组81项用例。\n\n| 模式 | 通过 | 失败 | 失败用例 |\n|---|---:|---:|---|\n'+'\n'.join(rows)+'\n\n全部模式均无执行错误或跳过。正确模式退出码0，缺陷模式退出码1，这是预期的缺陷暴露结果；没有使用xfail隐藏失败。\n\nHTML和JUnit结果保存在 reports/对应模式.html 与 .xml。验证覆盖注册、登录、个人信息、修改密码和退出登录。\n\n账号升级新增36项测试，先对旧实现运行观察失败，再实现两个接口并执行完整回归。\n\n验证顺序：先编写边界测试观察未实现应用导致的失败；实现正确服务后验证通过；开启缺陷验证失败；优化非边界用例的基准密码为8位后，重新执行全部模式。当前没有声称已手工修复三个教学缺陷，correct模式是正确实现的基准。\n',encoding='utf-8')
