"""验证原账号81条测试在四种教学模式下的预期结果。"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
EXPECTED_FAILURES = {'correct': 0, 'lower_bound': 1, 'upper_bound': 2, 'no_auth': 1}
ACCOUNT_TESTS = ['tests/test_auth.py', 'tests/test_account.py']


def main():
    (ROOT / 'reports').mkdir(exist_ok=True)
    rows = []
    for mode, failures in EXPECTED_FAILURES.items():
        report = ROOT / 'reports' / f'{mode}.xml'
        command = [
            sys.executable, '-m', 'pytest', *ACCOUNT_TESTS, '-q',
            '--bug-mode', mode, '--tb=short', f'--junitxml={report}',
            f'--html=reports/{mode}.html', '--self-contained-html',
        ]
        run = subprocess.run(command, cwd=ROOT, capture_output=True,
                             text=True, encoding='utf-8', errors='replace')
        if not report.is_file():
            print(run.stdout)
            print(run.stderr)
            raise SystemExit('未生成JUnit报告，不能确认测试结果')
        suite = ET.parse(report).find('testsuite')
        if suite is None:
            raise SystemExit('JUnit报告缺少testsuite')
        actual = {key: int(suite.get(key, 0))
                  for key in ['tests', 'failures', 'errors', 'skipped']}
        print(mode, actual, 'exit', run.returncode, flush=True)
        if actual != {'tests': 81, 'failures': failures, 'errors': 0, 'skipped': 0} or run.returncode != (1 if failures else 0):
            print(run.stdout)
            print(run.stderr)
            raise SystemExit('教学模式结果与预期不一致')
        failed = [case.get('name') for case in suite.findall('testcase')
                  if case.find('failure') is not None]
        rows.append(f'| {mode} | {81 - failures} | {failures} | '
                    + (', '.join(failed) or '无') + ' |')
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    text = (
        '# 账号教学模式验证结果\n\n'
        f'执行日期：{today}（北京时间）。仅覆盖原账号81条测试，不包含账本和SQL核对。'
        '项目当前全量范围见[当前测试用例](测试用例.md)。\n\n'
        '| 模式 | 通过 | 预期失败 | 失败用例 |\n'
        '|---|---:|---:|---|\n' + '\n'.join(rows)
        + '\n\n全部模式均无执行错误或跳过。正常模式退出码0，教学缺陷模式退出码1；'
        '没有使用xfail隐藏失败。HTML和JUnit结果保存在reports目录。'
        '这是主动植入缺陷的验证记录，不表示已手工修复这些缺陷。\n'
    )
    (ROOT / 'docs' / '验证结果.md').write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
