"""只读核对登记与索引；仅在本Run写新回执，不修复或重新认可历史哈希。

用法：automation/python.ps1 <本脚本>。成功完成扫描返回0；扫描异常返回非零。
报告中的missing/mismatch仍是实际缺口，不能把脚本完成解释为全部通过。
"""
import collections
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'automation/scripts'))
import retrieval
import evidence
from memory import index

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check_file(path, expected=None):
    # 只处理已有显式位置；旧路径只允许产品已验证的固定搬迁映射。
    resolved = evidence.reference_path(ROOT, path)
    if resolved is None or not resolved.is_file():
        return {'path': path, 'status': 'missing'}
    actual = digest(resolved)
    return {'path': path, 'resolved': str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved),
            'status': 'match' if expected == actual else 'mismatch' if expected else 'exists_unpinned',
            'expected': expected, 'actual': actual}

report = {'created_at': datetime.now(timezone.utc).isoformat(), 'owners': [], 'sources': [], 'run_files': [], 'errors': []}
catalog = index.Catalog(ROOT)
db = sqlite3.connect((ROOT / 'retrieval/generated/search.sqlite3').as_uri() + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
report['sqlite_integrity'] = db.execute('PRAGMA quick_check').fetchone()[0]
report['tables'] = {r[0]: db.execute('SELECT COUNT(*) FROM "'+r[0]+'"').fetchone()[0]
                    for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
registry = retrieval.read_json(ROOT / 'retrieval/sources.json')['sources']
for source in registry:
    report['sources'].append({'source_id': source['source_id'], 'enabled': source.get('enabled', True),
                              **check_file(source['path'], source.get('sha256'))})
for oid, owner in catalog.owners.items():
    print('Auditing', oid, flush=True)
    try:
        snapshot = catalog.snapshot(oid)
        history = catalog.store.read_history(owner, snapshot)
        projection = index.project_owner(catalog, oid)
        actual = {r['entry_id']: r['signature'] for r in db.execute('SELECT entry_id,signature FROM memory_entries WHERE owner_id=?', (oid,))}
        wanted = {r['entry_id']: r['signature'] for r in projection['entries']}
        records = list(snapshot['records'].values())
        report['owners'].append({'owner_id': oid, 'type': owner['owner_type'], 'title': owner['title'],
            'native_path': owner['native_ref']['path'], 'head': snapshot['head'], 'history_count': len(history),
            'record_kinds': dict(collections.Counter(r['kind'] for r in records)),
            'records': [{k:r.get(k) for k in ('record_id','revision','kind','title')} for r in records],
            'index': index.status(ROOT, oid), 'expected_entries': len(wanted), 'actual_entries': len(actual),
            'missing_entries': sorted(wanted.keys()-actual.keys()), 'extra_entries': sorted(actual.keys()-wanted.keys()),
            'changed_entries': sorted(k for k in wanted.keys() & actual.keys() if wanted[k]!=actual[k]),
            'projection_missing': projection['missing']})
        if owner['owner_type'] == 'run':
            for field in ('inputs', 'artifacts'):
                for item in owner['native_data'].get(field, []):
                    if isinstance(item, dict) and item.get('path'):
                        report['run_files'].append({'owner_id': oid, 'field': field, **check_file(item['path'], item.get('sha256'))})
    except Exception as exc:
        report['errors'].append({'owner_id': oid, 'error': str(exc)})
# 旧材料全文索引与规范记忆是不同投影，不能用后者水位证明前者覆盖。
discovered = retrieval.discover(ROOT, retrieval.config(ROOT))
report['legacy_columns'] = [r['name'] for r in db.execute('PRAGMA table_info(docs)')]
report['legacy_index_rows'] = [dict(r) for r in db.execute('SELECT * FROM docs')]
report['legacy_discovered'] = [{'path': s['path'], 'sha256': digest(Path(s['path'])) if Path(s['path']).is_file() else None} for s in discovered]
db.close()
report['summary'] = {'owner_count': len(report['owners']), 'types': dict(collections.Counter(x['type'] for x in report['owners'])),
    'sources': dict(collections.Counter(x['status'] for x in report['sources'])),
    'run_files': dict(collections.Counter(x['status'] for x in report['run_files'])),
    'index_states': dict(collections.Counter(x['index']['index_status'] for x in report['owners'])),
    'projection_missing': sum(len(x['projection_missing']) for x in report['owners']),
    'expected_entries': sum(x['expected_entries'] for x in report['owners']),
    'actual_entries': sum(x['actual_entries'] for x in report['owners']),
    'errors': len(report['errors']), 'legacy_discovered': len(discovered)}
# 每次重跑创建新文件，基线不会被后续补偿结果覆盖。
out = HERE / ('audit-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'report': str(out), **report['summary']}, ensure_ascii=False, indent=2))
sys.exit(1 if report['errors'] else 0)
