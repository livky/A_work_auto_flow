"""Bind each inheritance assertion to actual execution records and source IDs.

Run from any directory with the workspace Python entry point. This report
builder never runs tests and never converts a running suite into a passing one.
It only refreshes two audit artifacts and the map's separate execution_audit
field; every original design-time field is preserved. Re-run after final test
receipts arrive so the snapshot reports their actual state.
"""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
INPUT = RUN / 'inheritance-audit-input.json'
MAP = ROOT / 'docs/design/representation-query-v0.2/inheritance-map.json'
ALIASES = {
    'F': 'test_material_foundation.MaterialFoundationTests',
    'Q': 'test_material_queries.MaterialQueryTests',
    'E': 'test_material_evidence.MaterialEvidenceTests',
    'S': 'test_material_scope.MaterialScopeTests',
    'A': 'test_material_api.MaterialApiTests',
    'X': 'test_material_query_fixture.MaterialQueryFixtureTests',
    'D': 'test_material_deepening.MaterialDeepeningTests',
    'M': 'test_material_maintenance.MaterialMaintenanceTests',
    'MS': 'test_material_maintenance_status.MaterialMaintenanceStatusTests',
    'B': 'test_material_budget.MaterialBudgetReservationTests',
    'L': 'test_representation_contracts.BudgetLedgerTests',
    'C': 'test_representation_contracts.RepresentationContractTests',
    'R': 'test_material_recall.MaterialRecallTests',
    'V': 'test_material_facets.MaterialFacetTests',
    'RV': 'test_material_review_inheritance.MaterialReviewInheritanceTests',
    'DS': 'test_material_domain_scope.MaterialDomainScopeTests',
}

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def relative(path):
    return path.relative_to(ROOT).as_posix()

def main():
    inputs = read_json(INPUT)
    rows = inputs['rows']
    expected = [f'INH{i:02}' for i in range(1, 13)] + [f'C{i:02}' for i in range(1, 27)]
    assert [row['id'] for row in rows] == expected, 'Missing, duplicated, or reordered audit obligation.'
    definitions = {}
    for module in sorted({prefix.split('.')[0] for prefix in ALIASES.values()}):
        path = ROOT / 'automation/tests' / (module + '.py')
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        for cls in tree.body:
            if not isinstance(cls, ast.ClassDef):
                continue
            for method in cls.body:
                if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'):
                    name = f'{module}.{cls.name}.{method.name}'
                    assert name not in definitions
                    definitions[name] = {'source': relative(path), 'line': method.lineno,
                                         'current_test_source_sha256': digest(path)}

    evidence = defaultdict(list)
    receipts = []

    def add_receipt(path, data):
        """Read test entries, including nested observed groups/attempts.

        Passing test rows in an unfinished suite remain individual observations;
        the containing suite's running/failing status is recorded separately.
        """
        receipt = relative(path)
        receipts.append({'path': receipt, 'sha256': digest(path),
                         'suite_status': data.get('status', 'individual_test_receipt')})
        def walk(value):
            if not isinstance(value, dict):
                return
            tests = value.get('tests')
            if isinstance(tests, list):
                for test in tests:
                    if isinstance(test, dict) and 'id' in test and 'status' in test:
                        evidence[test['id']].append({'receipt': receipt, 'status': test['status'],
                            'reason': test.get('reason', ''),
                            'recorded_test_source_sha256': value.get('test_source_sha256')})
            # Only explicit successful execution attempts can bind bare IDs.
            if value.get('exit_code') == 0 and isinstance(value.get('test_ids'), list):
                for test_id in value['test_ids']:
                    evidence[test_id].append({'receipt': receipt, 'status': 'passed',
                                              'recorded_test_source_sha256': None})
            for key in ('groups', 'attempts'):
                for child in value.get(key, []):
                    walk(child)
        walk(data)

    # Enumerate only known Run outputs, not unrelated historical or business logs.
    json_paths = [RUN / name for name in (
        'inheritance-closure-p3.json', 'inheritance-closure-foundation-budget.json',
        'inheritance-closure-final.json', 'facets-acceptance.json',
        'review-inheritance-acceptance.json', 'material-recall-final-tests.json',
        'material-recall-acceptance.json')]
    json_paths.extend(sorted((RUN / 'testing').glob('*-attempt-*/01-python.json')))
    for path in json_paths:
        if path.is_file():
            add_receipt(path, read_json(path))
    log_paths = [RUN / 'material-domain-scope-tests.txt', RUN / 'material-recall-tests.txt',
                 RUN / 'material-recall-final-tests.txt', RUN / 'testing/facets-final-20260910.log',
                 RUN / 'testing/review-inheritance-final-20260910.log',
                 RUN / 'testing/contracts-final-20260910.log']
    pattern = re.compile(r'^test_\S+ \(([^)]+)\) \.\.\. (ok|FAIL|ERROR|skipped.*)$', re.MULTILINE)
    for path in log_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8-sig')
        receipt = relative(path)
        receipts.append({'path': receipt, 'sha256': digest(path), 'suite_status': 'raw_unittest_log'})
        for name, status in pattern.findall(text):
            evidence[name].append({'receipt': receipt, 'status': 'passed' if status == 'ok' else status.lower(),
                                   'recorded_test_source_sha256': None})

    test_names = sorted({ALIASES[short.split('.', 1)[0]] + '.' + short.split('.', 1)[1]
                         for row in rows for short in row['tests']})
    assert all(name in definitions for name in test_names), 'Audit refers to a missing test.'
    tests = []
    for number, name in enumerate(test_names, 1):
        observations = evidence.get(name, [])
        passed = any(item['status'] == 'passed' for item in observations)
        tests.append({'key': f'T{number:03}', 'id': name, **definitions[name],
            'observed_status': 'has_passed_execution' if passed else 'no_passed_receipt_bound',
            'execution_evidence': observations})
    lookup = {test['id']: test for test in tests}
    for row in rows:
        row['test_ids'] = [ALIASES[short.split('.', 1)[0]] + '.' + short.split('.', 1)[1] for short in row.pop('tests')]
        row['test_keys'] = [lookup[name]['key'] for name in row['test_ids']]
        missing = [name for name in row['test_ids'] if lookup[name]['observed_status'] != 'has_passed_execution']
        row['receipt_coverage'] = 'all_listed_tests_have_a_passed_execution' if not missing else 'some_receipts_not_yet_bound'
        row['tests_without_passed_receipt'] = missing
        row['source_fingerprints'] = [{'path': path, 'sha256': digest(ROOT / path)} for path in row['code']]

    suite_snapshots = []
    for path in sorted((RUN / 'testing').glob('*-attempt-*/results.json')):
        data = read_json(path)
        suite_snapshots.append({'path': relative(path), 'sha256': digest(path), 'status': data.get('status'),
            'tier': data.get('tier'), 'selection_version': data.get('selection_version'),
            'started_at': data.get('started_at'), 'finished_at': data.get('finished_at')})

    ai = {}
    for label, pattern in [('A07', 'A07/attempt-*/assessments/assessment-*.json'),
                           ('A08', 'A08/attempt-*/assessments/assessment-*.json'),
                           ('A09', 'A09/attempt-*/assessments/assessment-*.json')]:
        paths = sorted((RUN / 'actual-ai').glob(pattern))
        ai[label] = [{'path': relative(path), 'sha256': digest(path), 'actor': read_json(path).get('actor')} for path in paths]

    findings = [
        ('H01', '旧 attempts/confidence 与独立分类筛选缺映射', 'closed_in_scope', '规范可选 knowledge_facets、公开提交与逐 claim 交叉筛选；完整旧适用请求 DTO 仍保留限制。', ['INH02', 'C03']),
        ('H02', '多表示命中被折叠、原分数/片段不足', 'closed_in_scope', '保留各表示固定身份、原 BM25、matched_text/投影版本；RRF 每通道单票。', ['INH03', 'C05', 'C15']),
        ('H03', '小 result_limit 先读取大量候选', 'closed_in_scope', '按候选准入和最终 K 增量读取，resume 共用账本与固定身份。', ['C13', 'C16', 'C20']),
        ('H04', '真实通道故障丢失已完成部分', 'closed_in_scope', 'SQLite/OSError 与迭代失败保留已完成结果，诊断贯穿 assemble。', ['INH03', 'C14']),
        ('H05', '结构化 Issue/Basis 字段缺失', 'closed_in_scope', '补 code/message/affected_refs/retry 与稳定 basis_id/observed_at；不宣称所有旧 Outcome 无损桥接。', ['INH10']),
        ('H06', '旧关系被改名/遗漏及错误连接信息不足', 'closed_in_scope', '注册旧关系并保留平行边；未知关系报缺口；差异/拒绝诊断受权限约束且不导航。', ['INH11', 'C17']),
        ('H07', '四项模型预算边界缺直接验收', 'closed_in_scope', '输入/输出/调用/总 tokens 分别先耗尽及零额度已测；model_providers/tokenizers 明确为空。', ['INH09']),
        ('S01', 'owner 水位行缺失可伪装 current', 'closed_in_scope', '水位缺失即 partial，FTS 行存在也不等价于完整。', ['C12']),
    ]
    built_at = datetime.now(timezone.utc).isoformat()
    report = {'schema_version': 1, 'run_id': inputs['run_id'], 'audited_at': built_at,
        'status': 'partial_runtime_verified_obligations_open',
        'meaning': '逐项实际代码/测试/AI回执审计；入口存在、单项执行通过、旧协议全部验收三者分离。',
        'rows': rows, 'tests': tests, 'receipt_snapshots': receipts, 'suite_snapshots': suite_snapshots,
        'actual_ai': ai,
        'closed_findings': [{'id': key, 'original': title, 'status': status, 'closure': closure, 'rows': row_ids}
                            for key, title, status, closure, row_ids in findings],
        'original_audit_snapshot': inputs['original_audit_rows'],
        'counts': {'rows': len(rows), 'unique_tests': len(tests),
                   'tests_with_passed_receipt': sum(t['observed_status'] == 'has_passed_execution' for t in tests),
                   'verdicts': dict(Counter(row['verdict'] for row in rows))},
        'limitations': ['每行仅证明所列测试的软件范围，不推断真实模型有效性、人工或第二台物理机验收。',
                        '旧完整 DTO 与未支持后端、模型、ReadView、全部 fallback/索引中断矩阵仍按行保留。',
                        'has_passed_execution 表示真实单项记录；不是当前完整套件全通过。完整回执及其运行状态单独保存。',
                        '源指纹为本审计时快照；没有执行时指纹的旧日志保留 null，不推断历史文件与当前版本一致。',
                        '补充 C17 定向通过不覆盖原 full 的旧夹具错误；原失败和后续关闭分别记录。']}
    out = RUN / 'inheritance-acceptance.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    lines = ['# 表示查询继承逐项验收', '',
        f'固定 Run：`{inputs["run_id"]}`。审计快照：`{built_at}`。', '',
        '38 项均列出当前代码和真实测试 ID，并区分已绑定与尚待绑定的执行回执；没有把 43 个方法入口存在当作完整旧协议验收。具体修复 H01–H07 与 S01 已在其支持范围内闭合，旧 DTO/后端及未执行矩阵仍逐项保留。', '',
        '“范围内通过”只对应本机合成材料的所列软件行为；“部分验证”表示所列子集有实际依据、原义务仍有明确剩余。表内 T 编号链接到后文真实测试与执行回执；AI 阅读/审查和单元测试分开列出。', '',
        '## 完整测试与补充回归', '',
        '以下为生成本文时的真实套件状态。运行中或失败不计作完整通过；单项已执行结果只作为相应断言的局部证据。', '']
    for snapshot in suite_snapshots:
        short = Path(snapshot['path']).relative_to(Path(relative(RUN))).as_posix()
        detail = (f'，tier=`{snapshot["tier"]}`，selection={snapshot["selection_version"]}'
                  if snapshot['tier'] is not None else '，构建步骤回执')
        lines.append(f'- [{short}]({short})：`{snapshot["status"]}`{detail}。')
    lines += ['', '最终 P3 20/20（81.543 秒），C17 夹具修正后定向 1/1（35.792 秒）；Foundation 之前两次 25 项执行各有一个测试错误，原失败保留，未重写为全通过。[补充回执](inheritance-closure-final.json)。分类 8/8、新 review 1/1、domain 撤权 1/1 与召回独立回执见对应测试。', '',
              '## INH01–INH12 与 C01–C26', '',
              '| 项 | 判定 | 实际已验证范围 | 测试 | 剩余限制 |', '| --- | --- | --- | --- | --- |']
    for row in rows:
        verdict = '范围内通过' if row['verdict'] == 'verified_in_scope' else '部分验证'
        refs = ' '.join(f'[{key}](#{key.lower()})' for key in row['test_keys'])
        lines.append(f'| {row["id"]} | {verdict} | {row["verified_scope"]} | {refs} | {row["unresolved"]} |')
    lines += ['', '## 修复前问题与当前处置', '', '| 编号 | 原问题 | 当前处置 |', '| --- | --- | --- |']
    lines += [f'| {key} | {title} | {closure} |' for key, title, status, closure, row_ids in findings]
    lines += ['', '修复前逐项原始判定保存在机器回执的 `original_audit_snapshot`，现行表不会抹去原缺口。`inheritance-map.json` 仅增加独立 `execution_audit`，保留原设计覆盖与验收状态。', '',
              '## 真实测试与来源', '',
              f'共 {len(tests)} 个唯一测试 ID；{report["counts"]["tests_with_passed_receipt"]} 个绑定过实际通过回执。源码行号与指纹是当前快照，历史执行指纹未知时留空。']
    for test in tests:
        path = '../../../../' + test['source']
        receipt_paths = list(dict.fromkeys(item['receipt'] for item in test['execution_evidence']))
        receipt_links = []
        for source in receipt_paths:
            short = Path(source).relative_to(Path(relative(RUN))).as_posix()
            receipt_links.append(f'[{short}]({short})')
        status = '有真实通过记录' if test['observed_status'] == 'has_passed_execution' else '尚未绑定通过回执'
        lines += ['', f'### {test["key"]}', '',
                  f'`{test["id"]}` — {status}。源码：[第 {test["line"]} 行]({path}#L{test["line"]})。',
                  '执行依据：' + ('；'.join(receipt_links) if receipt_links else '无；不能据测试名判定执行通过。')]
    lines += ['', '## 实际 AI 记录及边界', '',
              'A07 覆盖摘要/正文、固定来源、完整块与预算缺口；其历史小预算包 stop_reason=null 仍是原回执事实。A08 实际比较固定两端并保存有条件导航判断。A09 由外部 AI 提交维护草案，经不可变 review 计划、apply 和固定读回产生规范新修订；自动 representation builder 仍只组合既有字段。A09 没有应撤回的已复核 claim，C24 另用公开 API 正向集成补足。三者均不是人工验收、盲测或现实模型验证。', '']
    for label, entries in ai.items():
        for entry in entries:
            short = Path(entry['path']).relative_to(Path(relative(RUN))).as_posix()
            lines.append(f'- [{label} 实际评估]({short})，执行者 `{entry["actor"]}`。')
    lines += ['', '本审计未增加依赖/模型或修改业务原件；README 已核对现有材料查询导航，详细分类说明由 MATERIAL_QUERY 指向 KNOWLEDGE_FACETS。完整清单、预构建资源、真实 setup 升级/恢复、刷新索引及校验由主集成回执证明，不用本表替代。', '',
              '机器回执：[inheritance-acceptance.json](inheritance-acceptance.json)。刷新本文：', '', '```powershell',
              '.\\automation\\python.ps1 projects/architecture-evolution/runs/run-20260909t194710z-3cf36b2fdd60/build_inheritance_acceptance.py', '```', '']
    (RUN / 'INHERITANCE_ACCEPTANCE.md').write_text('\n'.join(lines), encoding='utf-8')
    mapping = read_json(MAP)
    original = {key: value for key, value in mapping.items() if key != 'execution_audit'}
    mapping['execution_audit'] = {'run_id': inputs['run_id'], 'audited_at': built_at,
        'status': report['status'], 'document': relative(RUN / 'INHERITANCE_ACCEPTANCE.md'),
        'receipt': relative(out), 'receipt_sha256': digest(out),
        'rows': [{'id': row['id'], 'verdict': row['verdict'], 'test_ids': row['test_ids'],
                  'receipt_coverage': row['receipt_coverage']} for row in rows],
        'meaning': '独立执行审计；不覆盖或改写设计时期 coverage/status/test_status。'}
    assert original == {key: value for key, value in mapping.items() if key != 'execution_audit'}
    MAP.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], **report['counts'], 'suites': suite_snapshots}, ensure_ascii=False))

if __name__ == '__main__':
    main()
