"""Run material capture: explicit existing files, or a Python execution's own outputs.

Registration pins bytes and provenance; it never asserts scientific validity.
Execution is opt-in, uses the current Python, and is not an OS security sandbox.
Receipts retain both manifest versions so metadata registration can be undone
without deleting originals, outputs, or a previous execution's evidence.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import hashlib
import base64
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

import evidence
from memory import owners
from memory.errors import MemoryError


def timestamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def write_new(path, value):
    """Exclusive creation keeps receipts immutable across retries."""
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def run_path(root, run_id):
    view = owners.resolve_owner(root, run_id)
    if view['owner_type'] != 'run' or view.get('sensitivity') == 'restricted':
        raise ValueError('需要可访问的 Run ID')
    return owners.safe_path(root, view['native_ref']['path'])


def entry(root, name, role):
    """Only explicitly named permitted files are read; directory input is refused."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError('材料路径必须是非空字符串')
    path = evidence.reference_path(root, name)
    if not path.is_file():
        raise ValueError('登记需要实际文件：' + name)
    # Refuse restricted owning objects as well as disabled source aliases.
    for parent in [path.parent, *path.parents]:
        if not parent.is_relative_to(root):
            break  # External permission is per file, not permission to read sibling cards.
        # Generated run.json/research.json are raw output inside this reserved
        # container, never new business cards. Still check the enclosing Run.
        if parent.is_relative_to(root) and '.run-captures' in parent.relative_to(root).parts:
            continue
        for card in ('run.json', 'research.json', 'project.json', 'module.json'):
            owner_card = parent / card
            if owner_card.is_file() and evidence.read(owner_card).get('sensitivity') == 'restricted':
                raise ValueError('材料归属对象限制访问')
        if parent == root or not parent.is_relative_to(root):
            break
    return {'path': path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path),
            'sha256': evidence.sha256(path), 'role': role, 'registered_at': timestamp()}


def merge(raw, entries):
    result = deepcopy(raw)
    for group, items in entries.items():
        current = result.setdefault(group, [])
        if not isinstance(current, list):
            raise ValueError('损坏的 Run 材料登记：' + group)
        for item in items:
            old = [x for x in current if isinstance(x, dict) and x.get('path') == item['path']]
            if any(x.get('sha256') != item['sha256'] for x in old):
                raise ValueError('已登记文件版本变化；保留旧文件并为新版本使用新路径或新 Run：' + item['path'])
            if not old:
                current.append(item)
    return result


def commit(root, path, before_bytes, after, folder):
    """Save a recovery receipt before the single CAS-protected manifest mutation."""
    before = json.loads(before_bytes.decode('utf-8-sig'))
    receipt = folder / 'registration.json'
    expected = hashlib.sha256(before_bytes).hexdigest()
    write_new(receipt, {'schema_version': 1, 'run_path': path.relative_to(root).as_posix(),
                       'before': before, 'before_bytes': base64.b64encode(before_bytes).decode('ascii'),
                       'after': after, 'created_at': timestamp()})
    evidence.replace(path, after, expected)
    return {'status': 'registered', 'receipt': receipt.relative_to(root).as_posix(),
            'run_id': after['run_id'], 'scientific_review': 'unchanged'}


def register(root, run_id, inputs=(), artifacts=(), preview=False):
    root = Path(root).resolve()
    path = run_path(root, run_id)
    before = path.read_bytes()
    raw = json.loads(before.decode('utf-8-sig'))
    if not inputs and not artifacts:
        raise ValueError('至少指定一个 --input 或 --artifact 文件')
    entries = {'inputs': [entry(root, p, 'input') for p in inputs],
               'artifacts': [entry(root, p, 'artifact') for p in artifacts]}
    if any(evidence.reference_path(root, item['path']) == path for group in entries.values() for item in group):
        raise ValueError('Run 元数据由 L0 自动展示，不能把自身登记成固定文件')
    after = merge(raw, entries)
    if preview or after == raw:
        return {'status': 'preview' if preview else 'unchanged', 'entries': entries,
                'canonical_writes': 0}
    folder = owners.safe_path(root, (path.parent / '.run-captures' / uuid.uuid4().hex).relative_to(root).as_posix())
    folder.mkdir(parents=True)
    return commit(root, path, before, after, folder)


def rollback(root, receipt_name, preview=False):
    root = Path(root).resolve()
    receipt_path = owners.safe_path(root, receipt_name)
    receipt = evidence.read(receipt_path)
    path = run_path(root, receipt['after']['run_id'])
    if (receipt['run_path'] != path.relative_to(root).as_posix() or
            not receipt_path.is_relative_to(path.parent / '.run-captures')):
        raise ValueError('恢复回执不属于该 Run')
    current_bytes = path.read_bytes()
    current = json.loads(current_bytes.decode('utf-8-sig'))
    if current == receipt['before']:
        return {'status': 'already_restored', 'canonical_writes': 0}
    if current != receipt['after']:
        raise ValueError('登记后 Run 已有新修改，拒绝覆盖')
    if preview:
        return {'status': 'preview', 'canonical_writes': 0}
    original = base64.b64decode(receipt['before_bytes'], validate=True)
    if json.loads(original.decode('utf-8-sig')) != receipt['before']:
        raise ValueError('恢复回执的原始字节与元数据不一致')
    with evidence.locked(path):
        if path.read_bytes() != current_bytes:
            raise ValueError('恢复检查后 Run 已变化')
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.registration-restore-')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(original)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {'status': 'restored', 'files_deleted': 0, 'receipt': receipt_name}


def execute(root, run_id, request, preview=False):
    """Run a foreground Python script, pin its inputs, then capture its own folder.

    A fresh output folder on every attempt prevents overwriting earlier results.
    Failed processes still have logs and outputs captured; input mutation or a
    collection failure is reported separately and cannot become execution success.
    Script arguments accept {input0}, {input1}, ... and {output_dir}; no shell is used.
    """
    root = Path(root).resolve()
    if not isinstance(request, dict) or set(request) - {'script', 'inputs', 'args', 'timeout_seconds'}:
        raise ValueError('执行请求仅支持 script、inputs、args、timeout_seconds')
    inputs, args = request.get('inputs', []), request.get('args', [])
    timeout = request.get('timeout_seconds', 3600)
    if (not isinstance(inputs, list) or not all(isinstance(x, str) for x in inputs) or
            not isinstance(args, list) or not all(isinstance(x, str) for x in args) or
            isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 0 < timeout <= 86400):
        raise ValueError('inputs/args 必须是字符串数组；超时范围为 (0,86400] 秒')
    path = run_path(root, run_id)
    before = path.read_bytes()
    raw = json.loads(before.decode('utf-8-sig'))
    script = entry(root, request.get('script'), 'script')
    if Path(script['path']).suffix.lower() != '.py':
        raise ValueError('run-execute 当前支持 Python .py 脚本')
    pinned = [script, *[entry(root, p, 'input') for p in inputs]]
    if any(evidence.reference_path(root, item['path']) == path for item in pinned):
        raise ValueError('不能将待修改的 Run 元数据用作固定输入；先保存独立快照')
    after = merge(raw, {'inputs': pinned})
    folder = owners.safe_path(root, (path.parent / '.run-captures' / uuid.uuid4().hex).relative_to(root).as_posix())
    output = folder / 'outputs'
    replacements = {'output_dir': str(output), **{f'input{i}': str(evidence.reference_path(root, p)) for i, p in enumerate(inputs)}}
    def substitute(value):
        for key, replacement in replacements.items():
            value = value.replace('{' + key + '}', replacement)
        return value
    command = [sys.executable, str(evidence.reference_path(root, script['path'])), *map(substitute, args)]
    if preview:
        return {'status': 'preview', 'command': command, 'cwd': str(output), 'inputs': pinned, 'canonical_writes': 0}
    output.mkdir(parents=True)
    execution = {'command': command, 'cwd': str(output), 'started_at': timestamp(),
                 'python': sys.version, 'inputs': pinned, 'exit_code': None,
                 'status': 'failed', 'errors': [], 'scientific_review': 'not-reviewed'}
    try:
        with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
            process = subprocess.run(command, cwd=output, stdout=stdout, stderr=stderr, timeout=timeout, shell=False)
        execution['exit_code'] = process.returncode
        execution['status'] = 'succeeded' if process.returncode == 0 else 'failed'
    except (OSError, subprocess.TimeoutExpired) as exc:
        execution['errors'].append(type(exc).__name__ + ': ' + str(exc))
    execution['ended_at'] = timestamp()
    artifacts = []
    try:
        # Walk only the new attempt directory. Reject links instead of following
        # them into another Run or an external data store; do not prune bad data.
        for directory, dirs, files in os.walk(output, followlinks=False):
            for name in dirs + files:
                candidate = Path(directory) / name
                evidence.reference_path(root, str(candidate))
            for name in files:
                artifacts.append(entry(root, str(Path(directory) / name), 'output'))
        for item in pinned:
            if entry(root, item['path'], item['role'])['sha256'] != item['sha256']:
                raise ValueError('执行期间输入版本变化：' + item['path'])
    except (OSError, ValueError) as exc:
        execution['errors'].append(str(exc))
        execution['status'] = 'failed'
    write_new(folder / 'execution.json', execution)
    for name in ('stdout.txt', 'stderr.txt', 'execution.json'):
        if (folder / name).is_file():
            artifacts.append(entry(root, str(folder / name), 'execution_log'))
    after = merge(after, {'artifacts': artifacts})
    # Latest execution determines operational status; old attempt receipts and
    # scientific review history remain unchanged. New bytes invalidate old bases.
    after.update(status=execution['status'], started_at=raw.get('started_at') or execution['started_at'],
                 ended_at=execution['ended_at'])
    result = commit(root, path, before, after, folder)
    return {**result, 'execution_status': execution['status'], 'exit_code': execution['exit_code'],
            'errors': execution['errors'], 'output_dir': output.relative_to(root).as_posix()}


def add_commands(parsers):
    registration = parsers.add_parser('run-register', help='登记已有材料到 L0；固定当前指纹，不追认历史执行版本')
    registration.add_argument('run_id')
    registration.add_argument('--input', action='append', default=[])
    registration.add_argument('--artifact', action='append', default=[])
    registration.add_argument('--preview', action='store_true')
    execution = parsers.add_parser('run-execute', help='运行 Python 脚本，自动登记输入、输出及失败日志到 L0')
    execution.add_argument('run_id')
    execution.add_argument('--request', type=Path, required=True, help='JSON: script, inputs, args, timeout_seconds')
    execution.add_argument('--preview', action='store_true')
    restore = parsers.add_parser('run-registration-rollback', help='按回执恢复材料登记；保留所有原始文件')
    restore.add_argument('--receipt', required=True)
    restore.add_argument('--preview', action='store_true')


def dispatch(root, args):
    try:
        if args.command == 'run-register':
            return register(root, args.run_id, args.input, args.artifact, args.preview)
        if args.command == 'run-registration-rollback':
            return rollback(root, args.receipt, args.preview)
        return execute(root, args.run_id, evidence.read(args.request), args.preview)
    except MemoryError as exc:
        # This legacy CLI reports ordinary input/access failures with code 2.
        raise ValueError(f'{exc.code}: {exc}') from exc
