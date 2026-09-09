"""L0 read-only projection of declared originals; never a second source store.

List metadata first. Read a selected original only after fresh registration,
permission and fixed-byte checks. Run status/reviews and immutable MEM revisions
remain untouched; a matching file hash is not scientific validation.
"""
from collections import deque
from copy import deepcopy
import base64
import hashlib
from pathlib import Path
import re

import evidence
from . import contracts, owners
from .document import Reader
from .evidence_adapter import iter_refs
from .errors import MemoryError

HASH = re.compile(r'^[0-9a-f]{64}$')
MAX_FILE_BYTES = 64 * 1024 * 1024


def _path(service, locator):
    """Honor explicit source revocation even for a native Run path reference."""
    if not isinstance(locator, str) or '..' in locator.replace('\\', '/').split('/'):
        raise MemoryError('UNSAFE_PATH', '原始材料路径含越界片段')
    try:
        path = evidence.reference_path(service.root, locator)
        if path.is_relative_to(service.root):
            path = owners.safe_path(service.root, path.relative_to(service.root).as_posix())
        return path
    except ValueError as exc:
        raise MemoryError('ACCESS_DENIED', '原始材料路径未获授权或已被撤销') from exc


def _collect(service, owner_id):
    reader = Reader(service)
    root = reader.owner(owner_id)
    items, bindings, missing = {}, {}, []
    pending = deque()
    seen_records, seen_runs = set(), set()

    def gap(target, code):
        issue = {'target_id': target, 'code': code}
        if issue not in missing:
            missing.append(issue)

    def add(locator, digest, origin, source_ref=None):
        try:
            if source_ref:
                actual, _ = service._file(source_ref)
                # A denied alias of this same file also applies to native paths.
                path = _path(service, str(actual))
            else:
                path = _path(service, locator)
            # Native path declarations cannot bypass a restricted owning object.
            for view in reader.views.values():
                if view['native_data'].get('sensitivity') == 'restricted':
                    native = owners.safe_path(service.root, view['native_ref']['path'])
                    directory_owner = native.name in {'run.json', 'research.json', 'module.json', 'project.json'}
                    if path == native or (directory_owner and path.is_relative_to(native.parent)):
                        raise MemoryError('ACCESS_DENIED', '原始材料所属对象已限制访问')
            pinned = digest if isinstance(digest, str) and HASH.fullmatch(digest) else None
            identity = 'RAW-' + contracts.canonical_hash({'path': str(path), 'sha256': pinned})
            display = path.relative_to(service.root).as_posix() if path.is_relative_to(service.root) else str(path)
            row = items.setdefault(identity, {'material_id': identity, 'title': path.name,
                'path': display, 'sha256': pinned, 'level': 'L0', 'origins': [], 'source_refs': [],
                'status': 'missing' if not path.is_file() else 'registered' if pinned else 'unversioned'})
            if origin not in row['origins']:
                row['origins'].append(origin)
            if source_ref and source_ref not in row['source_refs']:
                row['source_refs'].append(deepcopy(source_ref))
            bindings[identity] = path
        except MemoryError as exc:
            gap(origin['owner_id'], exc.code)

    def enqueue_records(oid):
        for record in reader.state(oid)['records'].values():
            if record['sensitivity'] != 'restricted':
                pending.append({'target_kind': 'record', 'target_id': record['record_id'],
                    'revision': record['revision'], 'sha256': record['record_hash']})

    def run(oid, fixed=None):
        try:
            view = reader.owner(oid)
            if view['owner_type'] != 'run':
                return
            # An explicit old Run reference must not silently bind current metadata.
            if fixed and fixed.get('sha256') and fixed['sha256'] != evidence.fingerprint(view['native_data']):
                raise MemoryError('STALE_BASIS', '引用 Run 的固定版本已变化')
            if oid in seen_runs:
                return
            seen_runs.add(oid)
            raw = view['native_data']
            def origin(role):
                return {'owner_id': oid, 'run_id': oid, 'role': role,
                        'native_fingerprint': view['fingerprint']}
            for key in ('inputs', 'artifacts'):
                for entry in raw.get(key, []):
                    if isinstance(entry, dict) and entry.get('path'):
                        add(entry['path'], entry.get('sha256'), origin(key))
            code = raw.get('code') or {}
            if code.get('source_path'):
                add(code['source_path'], code.get('source_snapshot_sha256'), origin('code'))
            # The native card contains declared environment/parameters. Its hash
            # is explicitly a current metadata snapshot, not execution-time bytes.
            add(view['native_ref']['path'], view['fingerprint'], origin('current_run_metadata'))
            for entry in raw.get('dependencies', []):
                if isinstance(entry, dict) and entry.get('target') and entry['target'] not in reader.views:
                    add(entry['target'], entry.get('sha256'), origin('dependency'))
            enqueue_records(oid)
        except MemoryError as exc:
            gap(oid, exc.code)

    enqueue_records(owner_id)
    if root['owner_type'] == 'run':
        run(owner_id)
    else:
        # Explicit ownership/link fields cover both old root Runs and nested Runs.
        # Directory proximity, free text and broad registry membership grant no scope.
        for view in reader.views.values():
            raw = view['native_data']
            if view['owner_type'] == 'run' and (raw.get('owner_id') == owner_id or
                    raw.get('project_id') == owner_id or any(owner_id in raw.get(key, []) for key in
                    ('related_research_ids', 'related_project_ids', 'related_module_ids', 'related_dataset_ids'))):
                run(view['owner_id'])
    for entry in root['native_data'].get('dependencies', []):
        if isinstance(entry, dict) and entry.get('target'):
            if entry['target'] in reader.views:
                run(entry['target'], entry)
            else:
                add(entry['target'], entry.get('sha256'), {'owner_id': owner_id, 'role': 'dependency'})
    while pending:
        ref = pending.popleft()
        key = (ref['target_id'], ref.get('revision'), ref.get('sha256'))
        if key in seen_records:
            continue
        if len(seen_records) >= 2000:
            gap(owner_id, 'REFERENCE_LIMIT')
            break
        seen_records.add(key)
        try:
            record = reader.record(ref)
            origin = {'owner_id': record['owner_id'], 'record_id': record['record_id'],
                      'revision': record['revision'], 'role': record['kind'], 'title': record['title']}
            for child in iter_refs({'sources': record['sources'], 'payload': record['payload']}):
                if child['target_kind'] == 'file':
                    add(None, child.get('sha256'), origin, child)
                elif child['target_kind'] == 'record':
                    pending.append(child)
                elif child['target_kind'] == 'owner':
                    run(child['target_id'], child)
        except MemoryError as exc:
            gap(ref['target_id'], exc.code)
    reader.recheck()
    rows = sorted(items.values(), key=lambda row: (row['path'], row['sha256'] or ''))
    result = {'schema_version': 1, 'owner_id': owner_id, 'items': rows, 'total': len(rows),
              'missing': missing, 'basis_heads': {oid: state['head'] for oid, state in reader.states.items()},
              'canonical_writes': 0, 'content_loaded': False}
    return result, bindings, reader


def listing(service, request):
    """List existing registrations without reading their original file bodies."""
    return _collect(service, request['owner_id'])[0]


def read(service, request):
    """Re-resolve the opaque identity; never accept an arbitrary client file path."""
    limit = request.get('max_chars', 20000)
    if type(limit) is not int or not 1 <= limit <= 64000:
        raise MemoryError('INVALID_ARGUMENT', 'max_chars 范围为 1..64000')
    listing, bindings, reader = _collect(service, request['owner_id'])
    row = next((item for item in listing['items'] if item['material_id'] == request.get('material_id')), None)
    if row is None:
        raise MemoryError('NOT_FOUND', '材料不在当前归属的可读登记中，请刷新清单')
    if row['status'] != 'registered':
        raise MemoryError('UNRESOLVED_REFERENCE', '原始材料缺失或没有固定指纹', {'status': row['status']})
    path = bindings[row['material_id']]
    if path.stat().st_size > MAX_FILE_BYTES:
        raise MemoryError('INVALID_ARGUMENT', '文件超过 64 MiB 预览上限；请使用获准的本地工具读取原件')
    with path.open('rb') as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise MemoryError('INVALID_ARGUMENT', '文件超过预览字节上限')
    if hashlib.sha256(data).hexdigest() != row['sha256']:
        raise MemoryError('STALE_BASIS', '原始材料与登记版本不一致，未返回变更后的正文')
    _path(service, str(path))
    reader.recheck()
    result = {'material': row, 'canonical_writes': 0, 'verified_sha256': row['sha256'], 'bytes': len(data)}
    # Inline images are local, fixed raster bytes only. SVG/HTML remain inert text.
    mime = 'image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if data.startswith(b'\xff\xd8\xff') else None
    if mime and len(data) <= 2 * 1024 * 1024:
        return {**result, 'media_type': mime, 'image_data': 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')}
    try:
        text = data.decode('utf-8-sig')
        if '\x00' in text:
            raise UnicodeError()
    except UnicodeError:
        return {**result, 'media_type': 'application/octet-stream', 'message': '二进制或非 UTF-8 材料，请使用对应本地工具查看。'}
    return {**result, 'media_type': 'text/plain', 'text': text[:limit], 'truncated': len(text) > limit, 'max_chars': limit}
