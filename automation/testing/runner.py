"""Versioned task selections and a shell-free tiered test runner.

Run ``python automation/testing/runner.py --help`` for public commands. All
artifacts stay under a fresh local test directory or an existing Run; neither
selection updates nor execution retries overwrite earlier attempts.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog as registry
from atomic_io import replace_with_retry

AUTHORIZATIONS = {'vector', 'ocr', 'dependency-release', 'scale'}

def now():
    return datetime.now(timezone.utc).isoformat()

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def safe_path(root, value, *, output=False):
    """Reject escapes and reparse redirects before creating output parents."""
    root = Path(root).resolve()
    path = Path(value)
    path = path if path.is_absolute() else root / path
    raw = path.absolute()
    if not raw.is_relative_to(root):
        raise ValueError('路径必须位于当前工作区')
    cursor = raw
    while cursor != root:
        if cursor.exists() or cursor.is_symlink():
            info = cursor.lstat()
            if cursor.is_symlink() or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024):
                raise ValueError('测试产物路径不能经过链接或重解析点')
        cursor = cursor.parent
    path = raw.resolve()
    if not path.is_relative_to(root):
        raise ValueError('路径不能逃逸工作区')
    if output:
        local = path.is_relative_to(root / '.local')
        run = any((parent / 'run.json').is_file() for parent in [path.parent, *path.parents] if parent.is_relative_to(root) and parent != root)
        if not local and not run:
            raise ValueError('输出只允许写入 .local 或既有 Run，不能写业务原件目录')
    return path

def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

def save_progress(path, value):
    # Only an already-created execution directory uses atomic replace. Earlier
    # selection versions and previous execution attempts remain immutable.
    temporary = path.with_name(path.name + '.pending-' + uuid.uuid4().hex)
    write_new(temporary, value)
    replace_with_retry(temporary, path)

def fingerprints(root):
    result = {}
    for folder, suffixes in [('automation/scripts', {'.py'}), ('automation/testing', {'.py', '.json'}), ('automation/tests', {'.py'}), ('automation/schemas', {'.json'})]:
        for path in sorted((root / folder).rglob('*')):
            if path.is_file() and path.suffix in suffixes and '__pycache__' not in path.parts:
                result[path.relative_to(root).as_posix()] = file_hash(path)
    manifest = root / 'automation/ui/workbench-assets/asset-manifest.json'
    if manifest.is_file():
        result[manifest.relative_to(root).as_posix()] = file_hash(manifest)
    return result

def parse_exclusions(values):
    result = {}
    for value in values:
        identity, separator, reason = value.partition('=')
        if not separator or not identity or not reason.strip():
            raise ValueError('排除必须为 TEST_ID=具体原因')
        result[identity] = reason.strip()
    return result

def prepare(root, args, previous=None):
    catalog = registry.load(root)
    checked = registry.audit(root, catalog)
    if checked['status'] != 'passed':
        raise ValueError('目录覆盖审计失败，请先运行 audit 并登记新增/修正失效测试: ' + json.dumps(checked, ensure_ascii=False))
    tier = args.tier or (previous or {}).get('tier', 'quick')
    goal = args.goal or (previous or {}).get('goal')
    if not goal or not goal.strip():
        raise ValueError('任务目标不能为空')
    capabilities = args.capability if args.capability is not None else (previous or {}).get('affected_capabilities', [])
    additional = args.add_test if args.add_test is not None else (previous or {}).get('additional_tests', [])
    excluded = parse_exclusions(args.exclude) if args.exclude is not None else (previous or {}).get('exclusions', {})
    selected = registry.select(catalog, tier, capabilities, additional)
    selected_ids = {row['id'] for row in selected}
    if set(excluded) - selected_ids:
        raise ValueError('排除项必须原本在本次选择内')
    # Core gates may be explicitly deferred, but remain selected and make the
    # overall result incomplete. Exclusions can never manufacture a green run.
    authorizations = args.allow_capability if args.allow_capability is not None else (previous or {}).get('authorized_capabilities', [])
    if set(authorizations) - AUTHORIZATIONS:
        raise ValueError('未知运行授权')
    bundle = args.bundle or (previous or {}).get('dependency_bundle')
    plan = {'schema_version': 1, 'selection_version': (previous or {}).get('selection_version', 0) + 1,
            'created_at': now(), 'goal': goal, 'tier': tier, 'affected_capabilities': sorted(set(capabilities)),
            'additional_tests': sorted(set(additional)), 'selected_tests': [row['id'] for row in selected],
            'exclusions': excluded, 'authorized_capabilities': sorted(set(authorizations)),
            'dependency_bundle': bundle, 'actual_ai_scenarios': args.actual_ai if args.actual_ai is not None else (previous or {}).get('actual_ai_scenarios', []),
            'new_acceptance': args.acceptance if args.acceptance is not None else (previous or {}).get('new_acceptance', []),
            'reused_evidence': args.reuse_evidence if args.reuse_evidence is not None else (previous or {}).get('reused_evidence', []),
            'reason': args.reason or '开发前冻结测试选择', 'catalog_revision': catalog['revision'],
            'catalog_fingerprint': checked['catalog_fingerprint'], 'discovery_fingerprint': checked['discovery_fingerprint'],
            'program_fingerprints_at_selection': fingerprints(root),
            'known_limits': ['软件测试不等于实际AI执行、人工批准或科学结论复核', '真实检索质量与另一物理机验收独立记录', '万条规模未明确授权时不执行'],
            'previous_selection_fingerprint': registry.digest(previous) if previous else None}
    if plan['actual_ai_scenarios'] and any(not re.fullmatch(r'A\d{2}', value) for value in plan['actual_ai_scenarios']):
        raise ValueError('实际AI场景ID必须形如 A01')
    plan['selection_fingerprint'] = registry.digest(plan)
    output = safe_path(root, args.out, output=True)
    write_new(output, plan)
    return {'status': 'prepared', 'path': str(output), 'selection_version': plan['selection_version'], 'selected_count': len(selected), 'selection_fingerprint': plan['selection_fingerprint']}

def validate(root, plan):
    errors = []
    if plan.get('schema_version') != 1:
        errors.append('不支持的选择版本')
    unsigned = {key: value for key, value in plan.items() if key != 'selection_fingerprint'}
    if registry.digest(unsigned) != plan.get('selection_fingerprint'):
        errors.append('选择内容指纹不匹配；请创建新版而非直接编辑')
    catalog = registry.load(root)
    checked = registry.audit(root, catalog)
    if checked['status'] != 'passed':
        errors.append('测试目录存在未分类/失效项')
    for key in ('catalog_fingerprint', 'discovery_fingerprint'):
        if plan.get(key) != checked[key]:
            errors.append(key + ' 已变化；请 update 选择清单')
    try:
        expected = [row['id'] for row in registry.select(catalog, plan.get('tier'), plan.get('affected_capabilities', []), plan.get('additional_tests', []))]
        if expected != plan.get('selected_tests'):
            errors.append('选择未覆盖当前必跑项')
    except (ValueError, KeyError) as exc:
        errors.append(str(exc))
    if not plan.get('selected_tests'):
        errors.append('零测试不能通过')
    return {'status': 'passed' if not errors else 'failed', 'errors': errors, 'audit': checked}

def available(root, requirement, node, bundle):
    if requirement == 'windows':
        return os.name == 'nt'
    if requirement == 'frontend-dev':
        return bool(node) and all((root / 'automation/frontend/node_modules' / name).is_file() for name in ['vitest/vitest.mjs', '@playwright/test/cli.js', 'typescript/bin/tsc'])
    if requirement == 'vector':
        return (root / 'services/qdrant/models/multilingual-minilm/model_optimized.onnx').is_file()
    if requirement == 'ocr':
        # RapidOCR ships its ONNX files inside the locked Python package, not
        # a services/qdrant/models/ocr directory. This is availability only;
        # the full offline OCR tests still determine whether it actually works.
        spec = importlib.util.find_spec('rapidocr_onnxruntime')
        return bool(spec and spec.submodule_search_locations and any(Path(folder).joinpath('models').is_dir() for folder in spec.submodule_search_locations))
    if requirement == 'dependency-bundle':
        return bool(bundle) and Path(bundle).is_file()
    return False

def run_process(command, cwd, log, timeout, env=None):
    started = time.monotonic()
    options = {'cwd': str(cwd), 'shell': False, 'env': {**os.environ, **(env or {}), 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options['start_new_session'] = True
    with Path(log).open('xb') as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, **options)
        try:
            code = process.wait(timeout=timeout)
            status = 'completed'
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            # Stop only this owned process tree; otherwise test servers could
            # outlive a timeout and hold a shared fixture/database lock.
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False, timeout=15)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=15)
            code = process.returncode
            status = 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'timed-out'
    return {'process_status': status, 'exit_code': code, 'elapsed_seconds': round(time.monotonic() - started, 3)}

def interpret(kind, raw, expected, process, selected=None):
    """No green result from exit zero, missing reports, or zero selected tests."""
    if process['process_status'] != 'completed':
        return {'status': process['process_status'], 'total': 0}
    if not isinstance(raw, dict):
        return {'status': 'failed', 'reason': '缺少可核验机器结果', 'total': 0}
    if kind == 'python':
        total, failed, skipped = raw.get('total', 0), raw.get('failures', 0) + raw.get('errors', 0), raw.get('skipped', 0)
    elif kind == 'component':
        if selected is None:
            return {'status': 'failed', 'total': 0, 'reason': '组件结果必须按冻结ID核对'}
        wanted = {row['id'] for row in selected}
        matched, filtered, unexpected = {}, [], []
        for file in raw.get('testResults', []):
            # Vitest reports absolute slash-normalized paths and retains tests
            # rejected by testNamePattern as skipped. They are outside selection.
            name = file.get('name', '').replace('\\', '/')
            relative = name.split('/automation/frontend/')[-1]
            for assertion in file.get('assertionResults', []):
                identity = f"component:{relative}::{assertion.get('title', '')}"
                status = assertion.get('status')
                if identity in wanted:
                    if identity in matched:
                        return {'status': 'failed', 'total': len(matched), 'reason': '重复组件结果: ' + identity}
                    matched[identity] = status
                elif status in {'skipped', 'pending', 'todo', 'disabled'}:
                    filtered.append(identity)
                else:
                    unexpected.append(identity)
        missing = sorted(wanted - set(matched))
        if missing or unexpected:
            return {'status': 'failed', 'total': len(matched), 'missing': missing,
                    'unexpected_executed': unexpected, 'filtered_out': filtered,
                    'reason': '组件实际执行身份与冻结选择不符'}
        total = len(matched)
        skipped = sum(status in {'skipped', 'pending', 'todo', 'disabled'} for status in matched.values())
        failed = sum(status not in {'passed', 'skipped', 'pending', 'todo', 'disabled'} for status in matched.values())
        if process['exit_code'] != 0 or failed or total != expected or total == 0:
            status = 'failed'
        else:
            status = 'incomplete' if skipped else 'passed'
        return {'status': status, 'total': total, 'expected': expected, 'failures': failed,
                'skipped': skipped, 'selected_results': matched, 'filtered_out': filtered}
    elif kind == 'browser':
        stats = raw.get('stats', {})
        total = sum(stats.get(key, 0) for key in ('expected', 'unexpected', 'flaky', 'skipped'))
        failed, skipped = stats.get('unexpected', 0) + stats.get('flaky', 0), stats.get('skipped', 0)
    else:
        total, failed, skipped = raw.get('total', 0), raw.get('failures', 0), raw.get('skipped', 0)
    if process['exit_code'] != 0 or failed or total != expected or total == 0:
        return {'status': 'failed', 'total': total, 'expected': expected, 'failures': failed, 'skipped': skipped, 'reason': '失败、零测试或实际数量与冻结选择不符'}
    return {'status': 'incomplete' if skipped else 'passed', 'total': total, 'expected': expected, 'failures': failed, 'skipped': skipped}

def markdown_result(result):
    lines = ['# 分级测试执行结果', '', f"状态：{result['status']}；任务：{result['goal']}；层级：{result['tier']}", '',
             '软件测试、实际AI执行、人工审核和科学复核分别记录。下表未执行、跳过或失败均不计为通过。', '',
             '| 阶段 | 状态 | 实际/选择 | 秒 |', '|---|---|---|---|']
    for step in result['steps']:
        lines.append(f"| {step['kind']} | {step['status']} | {step.get('total', 0)}/{len(step['test_ids'])} | {step.get('elapsed_seconds', '')} |")
    for row in result['not_run']:
        lines.append(f"\n- 未执行 `{row['id']}`：{row['reason']}")
    if result.get('error'):
        lines.append('\n异常：' + result['error'])
    lines.append('\n命令数组、程序指纹、选择版本及逐项日志见 results.json 和本目录的阶段日志。')
    return '\n'.join(lines) + '\n'

def coverage(root, plan=None):
    catalog = registry.load(root)
    audit = registry.audit(root, catalog)
    selected = set(plan['selected_tests']) if plan else set()
    rows = []
    for capability in catalog['capabilities']:
        tests = [row for row in catalog['tests'] if row['capability'] == capability['id']]
        rows.append({'capability': capability['id'], 'goal': capability['title'], 'acceptance': capability['acceptance'],
                     'registered': len(tests), 'quick': sum(bool(row.get('quick')) for row in tests),
                     'full': sum(bool(row.get('full', True)) for row in tests),
                     'selected': sum(row['id'] in selected for row in tests),
                     'actual_ai_scenarios': capability.get('actual_ai_scenarios', [])})
    return {'status': audit['status'], 'capabilities': rows, 'audit': audit,
            'note': '登记与选择覆盖不是执行通过；实际结果另读每次results.json'}

def run(root, args):
    plan_path = safe_path(root, args.plan)
    plan = registry.read_json(plan_path)
    checked = validate(root, plan)
    if checked['status'] != 'passed':
        raise ValueError('选择校验失败: ' + json.dumps(checked, ensure_ascii=False))
    output = safe_path(root, args.out, output=True)
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / 'selection.json', plan)
    catalog = registry.load(root)
    entries = {row['id']: row for row in catalog['tests']}
    node = shutil.which(args.node or 'node')
    bundle = plan.get('dependency_bundle')
    if bundle:
        bundle = str(safe_path(root, bundle))
    result = {'schema_version': 1, 'status': 'running', 'started_at': now(), 'goal': plan['goal'], 'tier': plan['tier'],
              'selection_version': plan['selection_version'], 'selection_fingerprint': plan['selection_fingerprint'],
              'program_fingerprints': fingerprints(root), 'runtime': {'python': sys.executable, 'python_version': sys.version, 'node': node, 'platform': sys.platform},
              'steps': [], 'not_run': [], 'actual_ai_scenarios': plan.get('actual_ai_scenarios', []),
              'actual_ai_status': 'not-evaluated', 'human_review': 'not-reviewed', 'scientific_review': 'not-evaluated'}
    result['deferred_capabilities'] = catalog.get('deferred', [])
    def persist():
        save_progress(output / 'results.json', result)
        (output / 'README.md').write_text(markdown_result(result), encoding='utf-8')
    persist()
    groups = {}
    for identity in plan['selected_tests']:
        row = entries[identity]
        reason = plan['exclusions'].get(identity)
        denied = set(row.get('authorization', [])) - set(plan['authorized_capabilities'])
        missing = [need for need in row.get('requires', []) if not available(root, need, node, bundle)]
        if reason or denied or missing:
            result['not_run'].append({'id': identity, 'reason': reason or ('未授权: ' + ', '.join(sorted(denied)) if denied else '缺能力: ' + ', '.join(missing))})
        else:
            groups.setdefault(row['kind'], []).append(row)
    try:
        for kind in ('python', 'check', 'component', 'browser', 'integration'):
            rows = groups.get(kind, [])
            if not rows:
                continue
            position = len(result['steps']) + 1
            prefix = output / f'{position:02d}-{kind}'
            machine = prefix.with_suffix('.json')
            log = prefix.with_suffix('.log')
            cwd, env = root, {}
            if kind == 'python':
                ids = prefix.with_suffix('.ids.json')
                write_new(ids, [row['selector'] for row in rows])
                command = [sys.executable, str(root / 'automation/testing/worker.py'), '--root', str(root), '--ids', str(ids), '--out', str(machine)]
                if plan['tier'] == 'full':
                    all_ids = prefix.with_suffix('.all-ids.json')
                    write_new(all_ids, sorted(row['selector'] for row in entries.values() if row['kind'] == 'python'))
                    command.extend(['--discover', '--all-ids', str(all_ids)])
            elif kind in {'component', 'browser'}:
                cwd = root / 'automation/frontend'
                files = sorted({row['path'].removeprefix('automation/frontend/') for row in rows})
                pattern = '(?:' + '|'.join(re.escape(row['selector']) for row in rows) + ')$'
                if kind == 'component':
                    command = [node, 'node_modules/vitest/vitest.mjs', 'run', *files, '--testNamePattern', pattern, '--reporter=json', '--outputFile', str(machine)]
                else:
                    command = [node, 'node_modules/@playwright/test/cli.js', 'test', *files, '--grep', pattern, '--reporter=json', '--output', str(output / 'browser-artifacts')]
                    env['PLAYWRIGHT_JSON_OUTPUT_FILE'] = str(machine)
            elif kind == 'check':
                command = [node, str(root / 'automation/frontend/node_modules/typescript/bin/tsc'), '--noEmit']
                cwd = root / 'automation/frontend'
            elif kind == 'integration':
                command = [sys.executable, str(root / 'automation/tests/verify_dependency_release.py'), '--bundle', bundle]
            else:
                raise ValueError('不支持的阶段')
            step = {'kind': kind, 'status': 'running', 'test_ids': [row['id'] for row in rows], 'command': command, 'cwd': str(cwd), 'log': log.name, 'machine_result': machine.name}
            result['steps'].append(step)
            persist()
            process = run_process(command, cwd, log, args.timeout, env)
            if kind in {'check', 'integration'} and process['process_status'] == 'completed':
                write_new(machine, {'total': len(rows), 'failures': int(process['exit_code'] != 0), 'skipped': 0})
            raw = registry.read_json(machine) if machine.is_file() else None
            step.update(process)
            step.update(interpret(kind, raw, len(rows), process, rows))
            persist()
            if process['process_status'] == 'interrupted':
                break
        statuses = [step['status'] for step in result['steps']]
        completed_ids = {identity for step in result['steps'] for identity in step['test_ids']}
        for identity in plan['selected_tests']:
            if identity not in completed_ids and not any(row['id'] == identity for row in result['not_run']):
                result['not_run'].append({'id': identity, 'reason': '执行提前结束'})
        result['status'] = 'failed' if any(value in {'failed', 'timed-out', 'interrupted', 'running'} for value in statuses) else 'incomplete' if result['not_run'] or 'incomplete' in statuses or not statuses else 'passed'
    except (Exception, KeyboardInterrupt) as exc:
        result['status'], result['error'] = 'failed', str(exc) or '执行被中断'
        for step in result['steps']:
            if step['status'] == 'running':
                step.update(status='failed', reason=result['error'])
    finally:
        executed = {identity for step in result['steps'] if 'process_status' in step for identity in step['test_ids']}
        for identity in plan['selected_tests']:
            if identity not in executed and not any(row['id'] == identity for row in result['not_run']):
                result['not_run'].append({'id': identity, 'reason': '阶段未启动或执行提前终止'})
        result['finished_at'] = now()
        try:
            persist()
        except OSError as exc:
            # If the main receipt remains held after bounded retries, preserve
            # a final immutable failure receipt rather than leave only running.
            result['status'] = 'failed'
            result['final_persist_error'] = str(exc)
            fallback = output / ('results-failed-' + uuid.uuid4().hex + '.json')
            write_new(fallback, result)
            result['fallback_receipt'] = str(fallback)
    return {'status': result['status'], 'path': str(output), 'steps': len(result['steps']), 'not_run': len(result['not_run']), 'fallback_receipt': result.get('fallback_receipt')}

def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default=str(Path(__file__).resolve().parents[2]), help='工作区根目录')
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('audit', help='审计新增未分类/已失效测试；不执行测试')
    sub.add_parser('catalog', help='显示能力与固定quick门槛')
    item = sub.add_parser('coverage', help='按用户能力查看登记与任务选择覆盖；不伪装执行结果')
    item.add_argument('--plan')
    for name in ('prepare', 'update'):
        item = sub.add_parser(name, help='新建不可覆盖的任务选择版本')
        if name == 'update':
            item.add_argument('--plan', required=True)
        item.add_argument('--out', required=True)
        item.add_argument('--goal')
        item.add_argument('--tier', choices=['quick', 'full'])
        item.add_argument('--capability', action='append', help='本次影响能力，追加该能力全部已分类测试')
        item.add_argument('--add-test', action='append')
        item.add_argument('--exclude', action='append', help='TEST_ID=具体原因；排除仍使结果incomplete')
        item.add_argument('--allow-capability', action='append', choices=sorted(AUTHORIZATIONS))
        item.add_argument('--actual-ai', action='append', help='例如A01；只登记场景，不代替实际AI执行')
        item.add_argument('--acceptance', action='append', help='本任务新增验收ID/标准；原文留存')
        item.add_argument('--reuse-evidence', action='append', help='复用历史Run/回执及适用范围；不自动标为当前通过')
        item.add_argument('--bundle', help='已验证本地依赖ZIP；不联网下载')
        item.add_argument('--reason', required=name == 'update')
    item = sub.add_parser('validate', help='核对选择版本和当前catalog/discovery')
    item.add_argument('--plan', required=True)
    item = sub.add_parser('run', help='执行冻结选择，失败/跳过/超时/零测试不报告passed')
    item.add_argument('--plan', required=True)
    item.add_argument('--out', required=True, help='必须为尚不存在的.local目录或Run下子目录')
    item.add_argument('--timeout', type=float, default=1800, help='每阶段超时秒数，默认1800')
    item.add_argument('--node', help='本地Node可执行文件；不安装依赖')
    item = sub.add_parser('register', help='明确分类当前新增测试；后续新增方法仍须再审计')
    item.add_argument('--module', required=True, help='Python模块名或前端相对路径')
    item.add_argument('--capability', required=True)
    item.add_argument('--reason', required=True)
    item.add_argument('--requires', action='append', choices=['windows', 'frontend-dev', 'vector', 'ocr', 'dependency-bundle'])
    item.add_argument('--authorization', action='append', choices=sorted(AUTHORIZATIONS))
    return p

def execute(root, argv):
    args = parser().parse_args(['--root', str(root), *argv])
    root = Path(args.root).resolve()
    try:
        if args.action == 'audit':
            value = registry.audit(root)
        elif args.action == 'catalog':
            cat = registry.load(root)
            value = {'status': 'listed', 'revision': cat['revision'], 'capabilities': cat['capabilities'], 'quick': [row['id'] for row in cat['tests'] if row.get('quick')]}
        elif args.action == 'coverage':
            plan = registry.read_json(safe_path(root, args.plan)) if args.plan else None
            value = coverage(root, plan)
        elif args.action in {'prepare', 'update'}:
            previous = registry.read_json(safe_path(root, args.plan)) if args.action == 'update' else None
            value = prepare(root, args, previous)
        elif args.action == 'validate':
            value = validate(root, registry.read_json(safe_path(root, args.plan)))
        elif args.action == 'run':
            if args.timeout <= 0:
                raise ValueError('超时必须为正数')
            value = run(root, args)
        else:
            cat = registry.load(root)
            if args.capability not in {row['id'] for row in cat['capabilities']}:
                raise ValueError('未知能力')
            found = registry.discover(root)
            known = {row['id'] for row in cat['tests']}
            added = [row for row in found.values() if row['id'] not in known and (row['selector'].startswith(args.module + '.') or row['path'].removeprefix('automation/frontend/') == args.module)]
            if not added:
                raise ValueError('没有符合模块选择的新测试')
            for row in added:
                cat['tests'].append({**row, 'capability': args.capability, 'quick': False, 'full': True,
                                     'requires': args.requires or (['frontend-dev'] if row['kind'] != 'python' else []),
                                     'authorization': args.authorization or []})
            cat['revision'] += 1
            cat.setdefault('history', []).append({'at': now(), 'reason': args.reason, 'added': [row['id'] for row in added]})
            # This explicit development command updates the controlled catalog,
            # never run output or business data. Preserve the prior revision.
            backup = root / '.local/testing/catalog-history' / f"revision-{cat['revision']-1}-{uuid.uuid4().hex}.json"
            write_new(backup, registry.load(root))
            save_progress(root / registry.CATALOG, cat)
            value = {'status': 'registered', 'added': [row['id'] for row in added], 'catalog_revision': cat['revision'], 'previous_catalog': str(backup)}
        return value, 0 if value['status'] in {'passed', 'prepared', 'listed', 'registered'} else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {'status': 'failed', 'error': str(exc)}, 2

def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    # parse once to resolve --root; execute accepts the same public argument list.
    parsed = parser().parse_args(args)
    result, code = execute(parsed.root, args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code

if __name__ == '__main__':
    raise SystemExit(main())
