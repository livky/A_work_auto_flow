"""Record A05 public CLI use in a new isolated copy; never author AI judgements.

The source is the already-mutated A09 synthetic workspace. Copy fingerprints and
canonical snapshots make the reuse explicit. Source-unavailability injection is
limited to one registered file in the copy and always restores exact bytes in
finally. This helper performs mechanics only; the agent reads results and writes
the later review/assessment independently.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
STATE = RUN / 'a05-supplement-state.json'
ORIGIN = ROOT / '.local/testing/material-query-f3-20260910-actual/workspace'
A09 = RUN / 'actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7'
sys.path.insert(0, str(ROOT / 'automation/testing'))
import ai_review

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, data):
    ai_review.write_new(path, data)

def snapshot(path):
    """Fingerprint this explicitly selected synthetic tree, rejecting links."""
    rows = {}
    for item in sorted(path.rglob('*')):
        if item.is_symlink():
            raise ValueError('Synthetic fixture unexpectedly contains a link: ' + str(item))
        if item.is_file():
            rows[item.relative_to(path).as_posix()] = sha(item)
    return rows

def canonical(path):
    return {name: value for name, value in snapshot(path).items()
            if name.startswith('research/') or name == 'retrieval/sources.json'}

def require_state():
    state = read(STATE)
    target, attempt = Path(state['workspace']), Path(state['attempt'])
    if not target.resolve().is_relative_to(ROOT / '.local/testing') or target == ORIGIN:
        raise ValueError('A05 target must be a distinct isolated workspace.')
    if not (target / 'SYNTHETIC_ONLY.txt').is_file():
        raise ValueError('Synthetic marker missing.')
    return state, target, attempt

def call(label, argv, request=None):
    state, target, attempt = require_state()
    request_path = None
    if request is not None:
        request_path = attempt / 'authored-requests' / (label + '.json')
        save(request_path, request)
        argv = [*argv, '--request', str(request_path)]
    # memory has the legacy explicit-root pre-parser; material-query resolves
    # its public root from cwd. Both forms remain confined to this same copy.
    root_args = ['--root', str(target)] if argv[0] == 'memory' else []
    command = [sys.executable, str(ROOT / 'automation/scripts/workspace_cli.py'), *root_args, *argv]
    directory, receipt = ai_review.capture_call(attempt, command, request_path, target, 90)
    text = (directory / 'stdout.txt').read_text(encoding='utf-8-sig')
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {'non_json_stdout': text}
    outcome = {'call': str(directory), 'exit_code': receipt['exit_code'], 'result': result}
    save(attempt / 'outcomes' / (label + '.json'), outcome)
    print(json.dumps({'label': label, 'outcome': str(attempt / 'outcomes' / (label + '.json')),
                      'exit_code': receipt['exit_code'], 'status': result.get('status')}, ensure_ascii=False))
    return outcome

def initialize():
    if STATE.exists():
        raise ValueError('A05 was already initialized; use its saved attempt.')
    if not ORIGIN.resolve().is_relative_to(ROOT / '.local/testing') or not (ORIGIN / 'SYNTHETIC_ONLY.txt').is_file():
        raise ValueError('Unrecognized synthetic A09 origin.')
    before = snapshot(ORIGIN)
    target = ROOT / '.local/testing' / ('a05-followup-' + uuid.uuid4().hex) / 'workspace'
    shutil.copytree(ORIGIN, target)
    after, copied = snapshot(ORIGIN), snapshot(target)
    if before != after or before != copied:
        raise ValueError('A09 changed during copy or the copied bytes differ.')
    task = RUN / 'a05-supplement-task.txt'
    task.write_text('A05补充实际AI使用：继承A09已完成的局部修订、双文稿及旧版回读事实，不伪装重演；在其最终状态的新隔离副本重新形成计划，实际阅读并决定是否需要新内容；临时使一个已登记原件不可用，通过公开入口核对明确缺口，恢复原字节并核验。逐项自查A05-E1/E2交叉引用原A09，E3区分此次新执行；不改产品、测试、原F3、真实Project或已登记报告。', encoding='utf-8')
    metadata = RUN / 'a05-supplement-environment.json'
    save(metadata, {'origin_workspace': str(ORIGIN), 'workspace': str(target), 'copied_from_A09_final_state': True,
        'copy_time': datetime.now(timezone.utc).isoformat(), 'origin_manifest': str(A09 / 'manifest.json'),
        'origin_manifest_sha256': sha(A09 / 'manifest.json'), 'origin_files': before,
        'initial_canonical_files': canonical(target), 'all_copied_bytes_match': before == copied,
        'actor': 'Codex /root/frontier_review actual AI', 'context_mode': 'continuous',
        'limitations': ['A09事实为明确交叉引用，本尝试不重演其规范内容修订。', '本地合成材料；不是盲测、人工或科学验收。'],
        'program_fingerprints': {name: sha(ROOT / name) for name in (
            'automation/testing/ai_review.py', 'automation/scripts/workspace_cli.py',
            'automation/scripts/material_query/maintenance.py', 'automation/scripts/material_query/reader.py')}})
    attempt = ai_review.initialize(RUN / 'actual-ai', 'A05', task_file=task,
        actor='Codex /root/frontier_review actual AI', context_mode='continuous',
        parent_attempt=str(A09), metadata_file=metadata)
    save(STATE, {'workspace': str(target), 'attempt': str(attempt), 'origin': str(ORIGIN), 'metadata': str(metadata)})
    print(json.dumps(read(STATE), ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('init', 'call', 'snapshot', 'missing'))
    parser.add_argument('--label')
    parser.add_argument('--request-file')
    parser.add_argument('argv', nargs='*')
    args = parser.parse_args()
    if args.phase == 'init':
        initialize()
    elif args.phase == 'call':
        call(args.label, args.argv, read(args.request_file) if args.request_file else None)
    elif args.phase == 'snapshot':
        _, target, attempt = require_state()
        save(attempt / 'snapshots' / (args.label + '.json'), {'canonical': canonical(target), 'original': snapshot(ORIGIN)})
        print('Snapshot recorded: ' + args.label)
    else:
        _, target, attempt = require_state()
        registered = read(target / 'retrieval/sources.json')['sources']
        source = next(item for item in registered if item['source_id'] == 'SRC-F3-SATURATION')
        path = (target / source['path']).resolve()
        if not path.is_relative_to(target.resolve()) or not path.is_file():
            raise ValueError('Expected local registered synthetic original missing before injection.')
        backup = attempt / 'injection-backup' / path.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists():
            raise ValueError('Source injection already has a backup; do not overwrite.')
        content = path.read_bytes()
        expected = sha(path)
        # Rename only this verified file; keep the original registration and all
        # canonical records unchanged so the product observes true unavailability.
        path.rename(backup)
        try:
            call(args.label, args.argv, read(args.request_file) if args.request_file else None)
        finally:
            if path.exists() or backup.read_bytes() != content:
                raise ValueError('Unexpected source change; refusing to overwrite it during restore.')
            backup.rename(path)
            save(attempt / 'outcomes' / (args.label + '-restoration.json'),
                {'source_id': source['source_id'], 'relative_path': source['path'],
                 'missing_while_call': True, 'before_sha256': expected,
                 'restored_sha256': sha(path), 'bytes_restored': path.read_bytes() == content})

if __name__ == '__main__':
    main()
