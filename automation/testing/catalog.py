"""Static test discovery and auditable capability selection; no test imports.

Catalog entries name concrete tests, not wildcard module rules. A newly added
method therefore appears as unclassified until a developer explicitly registers
its user capability. Reading a catalog never executes repository test code.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import re

CATALOG = Path('automation/testing/catalog.json')

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def discover(root):
    root = Path(root)
    found = {}
    for path in sorted((root / 'automation/tests').glob('test_*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            for node in cls.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                    name = f'{path.stem}.{cls.name}.{node.name}'
                    found['python:' + name] = {'id': 'python:' + name, 'kind': 'python', 'selector': name, 'path': path.relative_to(root).as_posix()}
    # Test declarations are deliberately static. Dynamic generated tests should
    # register a provider rather than silently escaping coverage discovery.
    pattern = re.compile(r'(?m)^\s*(?:test|it)(?:\.(?:skip|only|todo))?\s*\(\s*([\x22\x27])((?:\\.|(?!\1).)*)\1', re.S)
    for kind, folder, glob in [('component', 'src', '*.test.*'), ('browser', 'e2e', '*.spec.ts')]:
        for path in sorted((root / 'automation/frontend' / folder).rglob(glob)):
            relative = path.relative_to(root / 'automation/frontend').as_posix()
            source = path.read_text(encoding='utf-8-sig')
            if re.search(r'\b(?:test|it)\.(?:each|for)\s*\(', source):
                raise ValueError('动态测试需先增加显式发现适配，不能漏记: ' + relative)
            for match in pattern.finditer(source):
                title = match.group(2)
                identity = f'{kind}:{relative}::{title}'
                if identity in found:
                    raise ValueError(f'重复测试标题无法稳定选择: {identity}')
                found[identity] = {'id': identity, 'kind': kind, 'selector': title, 'path': 'automation/frontend/' + relative}
    return found

def load(root):
    data = read_json(Path(root) / CATALOG)
    if data.get('schema_version') != 1 or not isinstance(data.get('revision'), int):
        raise ValueError('不支持的测试目录版本')
    return data

def audit(root, catalog=None):
    catalog = catalog or load(root)
    found = discover(root)
    entries = catalog.get('tests', [])
    ids = [row.get('id') for row in entries]
    capabilities = {row['id'] for row in catalog.get('capabilities', [])}
    errors = []
    if len(ids) != len(set(ids)):
        errors.append('测试目录存在重复ID')
    for row in entries:
        if row.get('capability') not in capabilities:
            errors.append('未知能力: ' + str(row.get('id')))
        if row.get('kind') not in {'python', 'component', 'browser', 'check', 'integration'}:
            errors.append('未知测试类型: ' + str(row.get('id')))
        if row.get('kind') in {'python', 'component', 'browser'} and row['id'] in found:
            if any(row.get(key) != found[row['id']][key] for key in ('kind', 'path', 'selector')):
                errors.append('测试定位已变化: ' + row['id'])
    registered = {row['id'] for row in entries if row.get('kind') in {'python', 'component', 'browser'}}
    unknown = sorted(set(found) - registered)
    missing = sorted(registered - set(found))
    return {'status': 'passed' if not (errors or unknown or missing) else 'failed',
            'discovered_count': len(found), 'catalog_count': len(entries),
            'unclassified': unknown, 'missing': missing, 'errors': errors,
            'discovery_fingerprint': digest(found), 'catalog_fingerprint': digest(catalog)}

def select(catalog, tier, capabilities=(), additional=()):
    if tier not in {'quick', 'full'}:
        raise ValueError('测试层级必须是quick/full')
    known = {row['id'] for row in catalog['capabilities']}
    if set(capabilities) - known:
        raise ValueError('未知影响能力: ' + ', '.join(sorted(set(capabilities) - known)))
    entries = {row['id']: row for row in catalog['tests']}
    if set(additional) - set(entries):
        raise ValueError('新增选择尚未登记: ' + ', '.join(sorted(set(additional) - set(entries))))
    selected = {row['id'] for row in entries.values()
                if (tier == 'full' and row.get('full', True)) or
                (tier == 'quick' and row.get('quick')) or
                (row['capability'] in capabilities and row.get('on_impact', row.get('full', True)))}
    selected.update(additional)
    if not selected:
        raise ValueError('测试选择为空')
    return [entries[identity] for identity in sorted(selected)]
