"""旧业务对象的只读适配与按需采用；身份来源始终是原登记文件。

扫描只进入八类业务区，并剪枝缓存、模板及记忆事务目录。新增入口不会
修改旧 manifest、CLM 或复核指纹。路径检查按 Windows 的更严格规则执行，
因此在其他平台准备的包也不会引入 Windows 名称冲突。
"""
from datetime import datetime, timezone
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import tempfile
import uuid

from .errors import MemoryError


ROOT_TYPES = {'research': 'research', 'runs': 'run', 'projects': 'project',
              'core-algorithms': 'core-algorithm', 'knowledge': 'knowledge',
              'reports': 'report', 'data': 'data', 'tools': 'tool'}
CARDS = {'research.json': ('research', 'research_id'), 'run.json': ('run', 'run_id'),
         'project.json': ('project', 'project_id'), 'module.json': ('core-algorithm', 'module_id'),
         'dataset.json': ('data', 'dataset_id'), 'tool.json': ('tool', 'tool_id')}
EXCLUDED = {'.run-captures', '.git', '.local', 'node_modules', '__pycache__', '_template', 'templates',
            'generated', '.venv', 'venv', '.pytest_cache', '.cache'}
_EXTENSIONS = {}


def _descriptor_schema(view=False):
    """固定基础字段契约，仅由可信登记扩充类型枚举。

    OwnerView 尚未采用时没有创建审计字段；这里移除的仅是这两个必需项。
    持久文件仍要求完整 Actor/时间，不能借自定义 schema 放宽基础契约。
    """
    from .contracts import SCHEMA
    schema = deepcopy(SCHEMA['$defs']['OwnerDescriptor'])
    schema['properties']['owner_type']['enum'] = [*ROOT_TYPES.values(), *_EXTENSIONS]
    if view:
        schema['required'] = [key for key in schema['required'] if key not in {'created_at', 'created_by'}]
    return schema


def _extension_view(root, spec, value):
    """先验证扩展输出，再回读获准原卡片，派生存储与展示信息。"""
    from .contracts import SCHEMA, validate_schema
    errors = validate_schema(value, spec['schema'], spec['schema'].get('$defs', {}))
    if errors:
        raise MemoryError('INVALID_SCHEMA', '扩展适配器输出违反登记契约', errors=errors)
    if not isinstance(value, dict):
        raise MemoryError('INVALID_SCHEMA', '扩展对象视图必须为对象')
    schema = _descriptor_schema(view=True)
    base = {key: value[key] for key in schema['properties'] if key in value}
    errors = validate_schema(base, schema, SCHEMA['$defs'])
    if errors or value.get('owner_type') != spec['owner_type'] or value.get('adapter_version') != spec['adapter_version']:
        raise MemoryError('INVALID_SCHEMA', '扩展对象基础契约或适配器版本不兼容', errors=errors)
    ref = value['native_ref']
    path = safe_path(root, ref['path'])
    safe_path(root, value['memory_home'])
    raw = _read(path)
    # 首版扩展仅支持有原身份字段的本地 JSON 卡；不允许计算路径散列后
    # 冒充跨移动稳定身份，其他原件类型须提供后续专用适配契约。
    if (not ref.get('id_field') or ref.get('id_value') != value['owner_id'] or
            raw.get(ref['id_field']) != value['owner_id']):
        raise MemoryError('INVALID_SCHEMA', '扩展身份与原对象字段不一致', {'path': ref['path']})
    return {**value, 'native_data': raw, 'fingerprint': _hash(path),
            'title': raw.get('title') or path.stem, 'temporary': False, 'persisted': False}


def safe_path(root, relative, *, _directory_cache=None):
    """返回安全的绝对路径；不创建文件，拒绝链接及跨平台歧义名称。

    不允许调用者指定绝对路径、父目录或 NTFS ADS。逐级检查现存组件，
    包括 junction/reparse point；并拒绝仅大小写不同的拼写或兄弟冲突。
    调用者应在实际写入前再次调用，进程锁不能代替文件系统访问控制。
    """
    input_root = Path(root)
    if _directory_cache is None:
        root = input_root.resolve()
        directories = None
    else:
        # This private cache is valid only until _recheck_directory_cache has
        # completed. The store owns it locally and never exposes it to callers.
        roots = _directory_cache.setdefault('roots', {})
        if input_root not in roots:
            roots[input_root] = input_root.resolve()
        root = roots[input_root]
        directories = _directory_cache.setdefault('directories', {})
    value = str(relative)
    windows = PureWindowsPath(value)
    parts = value.replace('\\', '/').split('/')
    if not value or windows.is_absolute() or windows.drive or any(
            p in {'', '.', '..'} or p.endswith((' ', '.')) or
            re.search(r'[<>:"|?*\x00-\x1f]', p) or
            re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', p)
            for p in parts):
        raise MemoryError('UNSAFE_PATH', '非法工作区相对路径', {'path': value})
    current = root
    for part in parts:
        cached = directories.get(current) if directories is not None else None
        try:
            metadata = cached['metadata'] if cached else current.lstat()
        except FileNotFoundError:
            metadata = None
        if metadata and (stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400):
            raise MemoryError('UNSAFE_PATH', '不允许符号链接或联接', {'path': value})
        if metadata and stat.S_ISDIR(metadata.st_mode):
            # 一次快照复用父链及目录枚举，返回结果前统一重新核对。每个
            # 叶文件仍独立 lstat，不能因为共享父目录而跳过链接检查。
            if cached is None:
                names = {}
                for path in current.iterdir():
                    names.setdefault(path.name.casefold(), []).append(path.name)
                cached = {'metadata': metadata, 'names': names, 'used': set()}
                if directories is not None:
                    directories[current] = cached
            matches = cached['names'].get(part.casefold(), [])
            if len(matches) > 1 or (matches and matches[0] != part):
                raise MemoryError('UNSAFE_PATH', '路径大小写冲突', {'path': value})
            cached['used'].add(part)
        current = current / part
        child = directories.get(current) if directories is not None else None
        try:
            metadata = child['metadata'] if child else current.lstat()
        except FileNotFoundError:
            metadata = None
        if metadata:
            flags = getattr(metadata, 'st_file_attributes', 0)
            if stat.S_ISLNK(metadata.st_mode) or flags & 0x400:
                raise MemoryError('UNSAFE_PATH', '不允许符号链接或联接', {'path': value})
    # The read cache rechecks all parents before yielding the snapshot. Plain
    # callers retain the immediate final resolve check, including all writes.
    final = current if directories is not None else current.resolve()
    if not final.is_relative_to(root):
        raise MemoryError('UNSAFE_PATH', '路径超出工作区', {'path': value})
    return current


def _recheck_directory_cache(cache):
    """只读快照返回前重新验证共享父链，缓存不跨这次调用存活。

    按浅到深检查，先拒绝被替换成 junction 的父目录，再枚举其子项。
    与本快照无关的新兄弟文件不导致失败；使用到的名字必须仍无大小写
    歧义。目录身份被替换时拒绝返回混合读取结果，不尝试修复文件系统。
    """
    for directory, entry in sorted(cache.get('directories', {}).items(), key=lambda item: len(item[0].parts)):
        try:
            current = directory.lstat()
        except OSError as exc:
            raise MemoryError('UNSAFE_PATH', '快照读取期间父目录不可用') from exc
        previous = entry['metadata']
        if (not stat.S_ISDIR(current.st_mode) or stat.S_ISLNK(current.st_mode)
                or getattr(current, 'st_file_attributes', 0) & 0x400):
            raise MemoryError('UNSAFE_PATH', '快照读取期间父目录成为链接或联接')
        if (current.st_dev, current.st_ino) != (previous.st_dev, previous.st_ino):
            raise MemoryError('STALE_BASIS', '快照读取期间父目录被替换')
        names = {}
        for item in directory.iterdir():
            names.setdefault(item.name.casefold(), []).append(item.name)
        for name in entry['used']:
            matches = names.get(name.casefold(), [])
            if len(matches) > 1 or (matches and matches[0] != name):
                raise MemoryError('UNSAFE_PATH', '快照读取期间路径大小写改变')


def _read(path, require_object=True):
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'),
                           parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        if require_object and not isinstance(value, dict):
            raise ValueError('业务元数据必须为 JSON 对象')
        return value
    except (OSError, ValueError, UnicodeError) as exc:
        raise MemoryError('INTEGRITY_ERROR', '无法读取业务元数据', {'path': str(path), 'reason': str(exc)}) from exc


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _home(kind, path, oid):
    p = Path(path)
    if kind == 'tool':
        return f'tools/memory/{oid}'
    if kind in {'run', 'research', 'project', 'core-algorithm'}:
        return (p.parent / 'memory').as_posix()
    return path + '.memory'


def _view(root, path, kind, raw, key=None):
    rel = path.relative_to(root).as_posix()
    oid = raw.get(key) if key else None
    if key and (not isinstance(oid, str) or not oid.strip()):
        raise MemoryError('INTEGRITY_ERROR', '业务身份缺失', {'path': rel, 'field': key})
    temporary = not oid
    oid = oid or 'FILE-' + hashlib.sha256(rel.encode()).hexdigest()[:24]
    home = _home(kind, rel, oid)
    safe_path(root, home)
    return {'schema_version': 1, 'owner_id': oid, 'owner_type': kind,
            'native_ref': {'path': rel, 'id_field': key, 'id_value': None if temporary else oid},
            'memory_home': home, 'adapter_version': 1, 'temporary': temporary,
            'persisted': False, 'title': raw.get('title') or raw.get('name') or path.stem,
            'fingerprint': _hash(path), 'native_data': raw}


def list_owners(root, filters=None, *, metadata_only=False):
    """发现已登记对象和可采用文档；任何坏业务 JSON 均显式失败。

    project_id 等关联字段不产生对象。缺少稳定身份的普通文档只返回临时
    FILE 导航 ID；只有 adopt_owner 能为它建立稳定 OBJ 身份。metadata_only
    用于只读导航：只解析明确身份卡，不加载普通原始 JSON；默认严格扫描
    仍校验每个业务 JSON，validate/写入的错误检查没有被关闭。
    """
    root = Path(root).resolve()
    # One read-only scan shares ancestor directory listings. This cache is
    # rechecked before return and never reused across requests or writes.
    directory_cache = {}
    def _safe(workspace, relative):
        return safe_path(workspace, relative, _directory_cache=directory_cache)
    views, persisted, documents = [], [], []
    for base, default_kind in ROOT_TYPES.items():
        start = _safe(root, base)
        if not start.exists():
            continue
        for folder, dirs, files in os.walk(start, followlinks=False):
            # 记忆目录只读 owner.json，不把内部 JSON 误当业务卡或旧证据。
            for name in list(dirs):
                if name.casefold() in EXCLUDED:
                    dirs.remove(name)
                    continue
                sub = _safe(root, (Path(folder) / name).relative_to(root).as_posix())
                if name == 'memory' or name.endswith('.memory'):
                    if base == 'tools' and sub == root / 'tools/memory':
                        for child in sub.iterdir():
                            child = _safe(root, child.relative_to(root).as_posix())
                            if child.is_dir() and (child / 'owner.json').exists():
                                persisted.append((_safe(root, (child / 'owner.json').relative_to(root).as_posix()), _read(child / 'owner.json')))
                    elif (sub / 'owner.json').exists():
                        p = _safe(root, (sub / 'owner.json').relative_to(root).as_posix())
                        persisted.append((p, _read(p)))
                    dirs.remove(name)
            for name in sorted(files):
                if name.startswith('example.') or '.example.' in name or name.endswith('_TEMPLATE.md'):
                    continue
                path = _safe(root, (Path(folder) / name).relative_to(root).as_posix())
                if path.suffix.lower() == '.json':
                    card = (path == root / 'tools/registry.json' or name in CARDS or
                            name.endswith(('.dataset.json', '.evidence.json')) or
                            (default_kind == 'report' and 'manifests' in path.relative_to(root).parts))
                    if metadata_only and not card:
                        continue
                    # 非登记 JSON 可以是合法数组数据；仍解析语法以报告坏业务
                    # 文件，但不把合法数组误判为损坏对象卡。
                    raw = _read(path, require_object=False)
                    if not isinstance(raw, dict):
                        if card:
                            raise MemoryError('INTEGRITY_ERROR', '业务卡必须为 JSON 对象', {'path': str(path)})
                        continue
                    if path == root / 'tools/registry.json':
                        if not isinstance(raw.get('tools'), list):
                            raise MemoryError('INTEGRITY_ERROR', '工具登记缺少 tools 数组', {'path': str(path)})
                        for item in raw['tools']:
                            if not isinstance(item, dict) or not isinstance(item.get('entrypoint'), str):
                                raise MemoryError('INTEGRITY_ERROR', '工具入口格式无效', {'path': str(path)})
                            entry = _safe(root, item['entrypoint'])
                            if not entry.exists():
                                raise MemoryError('NOT_FOUND', '工具登记入口不存在', {'path': item['entrypoint']})
                            views.append(_view(root, path, 'tool', item, 'tool_id'))
                    elif name in CARDS:
                        kind, key = CARDS[name]
                        views.append(_view(root, path, kind, raw, key))
                    elif name.endswith('.dataset.json'):
                        views.append(_view(root, path, 'data', raw, 'dataset_id'))
                    elif name.endswith('.evidence.json'):
                        views.append(_view(root, path, default_kind, raw, 'evidence_id'))
                    elif default_kind == 'report' and 'report_id' in raw:
                        views.append(_view(root, path, 'report', raw, 'report_id'))
                elif default_kind in {'knowledge', 'report'} and path.suffix.lower() == '.md' and name not in {'README.md', 'AGENTS.md'}:
                    documents.append((path, default_kind))
    declared = {v['native_data'].get('document_path') for v in views}
    views.extend(_view(root, p, kind, {}) for p, kind in documents if p.relative_to(root).as_posix() not in declared)
    if metadata_only:
        # An adopted report may use an arbitrary native JSON filename. Its
        # validated persisted descriptor supplies the explicit locator; this
        # does not require opening every unrelated JSON to guess report_id.
        known = {_native_key(view['native_ref']) for view in views}
        for _path, descriptor in persisted:
            ref = descriptor.get('native_ref', {})
            if ref.get('id_field') and _native_key(ref) not in known:
                native = _safe(root, ref['path'])
                raw = _read(native)
                views.append(_view(root, native, descriptor['owner_type'], raw, ref['id_field']))
                known.add(_native_key(ref))
    for spec, adapter in _EXTENSIONS.values():
        output = adapter.list_owners(root)
        if not isinstance(output, list):
            raise MemoryError('INVALID_SCHEMA', '扩展适配器必须返回对象列表')
        for value in output:
            view = _extension_view(root, spec, value)
            views.append(view)
            # 扩展区不在八类默认扫描根内；由可信适配器的具体定位读取，
            # 不为了发现新类型而递归扫描整个工作区。
            path = _safe(root, view['memory_home'] + '/owner.json')
            if path.is_file() and not any(p == path for p, _ in persisted):
                persisted.append((path, _read(path)))
    by_native = {}
    by_id = {}
    for view in views:
        identity = _native_key(view['native_ref'])
        if identity in by_native or view['owner_id'].casefold() in by_id:
            raise MemoryError('INVALID_SCHEMA', '重复业务身份或原定位', {'owner_id': view['owner_id']})
        by_native[identity] = view
        by_id[view['owner_id'].casefold()] = view
    claimed = set()
    for path, descriptor in persisted:
        # 使用唯一契约校验，不能因兼容读取而容忍损坏 actor、未知字段或版本。
        from .contracts import SCHEMA, validate_schema
        errors = validate_schema(descriptor, _descriptor_schema(), SCHEMA['$defs'])
        if errors:
            raise MemoryError('INTEGRITY_ERROR', 'owner.json 不符合契约', {'path': str(path)}, errors)
        ref = descriptor.get('native_ref', {})
        identity = _native_key(ref)
        original = by_native.get(identity)
        if original is None:
            raise MemoryError('NOT_FOUND', '记忆入口原对象缺失；手工移动需显式迁移', {'path': str(path), 'native_ref': ref})
        if identity in claimed:
            raise MemoryError('INVALID_SCHEMA', '同一原对象被重复认领', {'path': str(path)})
        claimed.add(identity)
        oid = descriptor.get('owner_id')
        expected = (original['memory_home'] if original['owner_type'] in _EXTENSIONS
                    else _home(original['owner_type'], ref['path'], oid))
        if (descriptor.get('schema_version') != 1 or descriptor.get('adapter_version') != 1 or
                descriptor.get('owner_type') != original['owner_type'] or
                descriptor.get('memory_home') != expected or path.parent != _safe(root, expected) or
                not isinstance(oid, str) or not oid or
                (not original['temporary'] and oid != original['owner_id']) or
                (original['temporary'] and not re.fullmatch(r'OBJ-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', oid))):
            raise MemoryError('INTEGRITY_ERROR', '记忆入口与原对象契约不匹配', {'path': str(path)})
        other = by_id.get(oid.casefold())
        if other is not None and other is not original:
            raise MemoryError('INVALID_SCHEMA', '重复记忆身份', {'owner_id': oid})
        by_id.pop(original['owner_id'].casefold(), None)
        original.update(descriptor)
        original.update(persisted=True, temporary=False)
        by_id[oid.casefold()] = original
    aliases = {}
    for view in views:
        for alias in view.get('aliases', []):
            collision = by_id.get(alias.casefold()) or aliases.get(alias.casefold())
            if collision is not None and collision is not view:
                raise MemoryError('INVALID_SCHEMA', '旧导航别名重复认领', {'alias': alias})
            aliases[alias.casefold()] = view
    filters = filters or {}
    result = sorted([v for v in views if all(v.get(k) == value if not isinstance(value, (list, tuple, set))
                    else v.get(k) in value for k, value in filters.items())], key=lambda v: v['owner_id'])
    _recheck_directory_cache(directory_cache)
    return result


def _native_key(ref):
    if (not isinstance(ref, dict) or not isinstance(ref.get('path'), str) or
            any(ref.get(k) is not None and not isinstance(ref[k], str) for k in ('id_field', 'id_value'))):
        raise MemoryError('INTEGRITY_ERROR', 'native_ref 缺少 path')
    return (ref['path'].replace('\\', '/').casefold(), ref.get('id_field'), ref.get('id_value'))


def resolve_owner(root, owner_id):
    matches = [v for v in list_owners(root) if v['owner_id'] == owner_id or owner_id in v.get('aliases', [])]
    if len(matches) != 1:
        raise MemoryError('NOT_FOUND' if not matches else 'INVALID_SCHEMA', '无法唯一解析对象', {'owner_id': owner_id})
    return matches[0]


def require_readable_owner(owner):
    """Public actions cannot read or write a native owner after revocation."""
    if owner['native_data'].get('sensitivity') == 'restricted':
        raise MemoryError('ACCESS_DENIED', '此对象不在当前可读范围')
    return owner


def public_list_owners(root, filters=None):
    """Filter presentation only; internal scans still detect all ID conflicts.

    In particular do not return a restricted owner's native_data, title, path,
    or identity through the selector used by the HTTP and CLI front ends.
    """
    return [owner for owner in list_owners(root, filters) if owner['native_data'].get('sensitivity') != 'restricted']


def ensure_owner(root, descriptor, actor=None):
    """首次提交时原子发布派生 owner.json，不接受调用者指定存储位置。"""
    owner = resolve_owner(root, descriptor['owner_id'])
    require_readable_owner(owner)
    if descriptor.get('memory_home') != owner['memory_home'] or descriptor.get('native_ref') != owner['native_ref']:
        raise MemoryError('INVALID_SCHEMA', '调用者对象定位已变化')
    if owner['persisted']:
        return owner
    if owner['temporary']:
        raise MemoryError('INVALID_SCHEMA', '无稳定身份的文档须先 adopt_owner')
    return _persist(root, owner, actor)


def _persist(root, owner, actor):
    actor = actor or {'kind': 'workflow', 'id': 'memory-owner-adapter'}
    if not isinstance(actor, dict) or set(actor) != {'kind', 'id'} or actor['kind'] not in {'human', 'ai', 'workflow'} or not isinstance(actor['id'], str) or not actor['id'].strip():
        raise MemoryError('INVALID_SCHEMA', 'Actor 格式无效')
    saved = {k: owner[k] for k in ('schema_version', 'owner_id', 'owner_type', 'native_ref', 'memory_home', 'adapter_version')}
    saved.update(created_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), created_by=actor)
    if owner.get('aliases'):
        saved['aliases'] = owner['aliases']
    if _hash(safe_path(root, owner['native_ref']['path'])) != owner['fingerprint']:
        raise MemoryError('STALE_BASIS', '写入入口前原对象已变化')
    path = safe_path(root, owner['memory_home'] + '/owner.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    # 临时文件完成 flush/fsync 后，用硬链接原子、独占发布。并发采用的输家
    # 读取已发布入口；从不覆盖先到者，也不暴露写了一半的 JSON。
    fd, temp = tempfile.mkstemp(prefix='.owner-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(saved, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        safe_path(root, owner['memory_home'] + '/owner.json')
        try:
            os.link(temp, path)
        except FileExistsError:
            pass
    finally:
        os.unlink(temp)
    matches = [v for v in list_owners(root) if _native_key(v['native_ref']) == _native_key(owner['native_ref'])]
    return matches[0]


def adopt_owner(root, native_ref, expected_hash, actor=None):
    """显式采用旧文件，校验调用者观察到的字节哈希；原件完全不变。"""
    # Reject path-like escapes before enumerating registered metadata. A path
    # supplied to this public endpoint never grants permission to read it.
    selected_path = native_ref.get('path') if isinstance(native_ref, dict) else native_ref
    safe_path(root, selected_path)
    matches = [v for v in list_owners(root) if
               (_native_key(v['native_ref']) == _native_key(native_ref) if isinstance(native_ref, dict)
                else v['native_ref']['path'] == native_ref)]
    if len(matches) != 1:
        raise MemoryError('NOT_FOUND' if not matches else 'INVALID_SCHEMA', '采用目标不能唯一定位')
    owner = matches[0]
    require_readable_owner(owner)
    if owner['fingerprint'] != expected_hash:
        raise MemoryError('STALE_BASIS', '采用目标已变化', {'native_ref': owner['native_ref']})
    if owner['persisted']:
        return owner
    if owner['temporary']:
        owner['aliases'] = [owner['owner_id']]
        owner['owner_id'] = 'OBJ-' + str(uuid.uuid4())
    return _persist(root, owner, actor)


def run_adapter(root, owner_id):
    """Run 事件视图沿用 RUN/CLM；不复制 MEM-event，不修改复核语义。"""
    owner = resolve_owner(root, owner_id)
    if owner['owner_type'] != 'run':
        raise MemoryError('INVALID_SCHEMA', '目标不是 Run')
    return {'owner_id': owner_id, 'event_id': owner_id, 'kind': 'event', 'level': 'L2',
            'stored_level': 'L1', 'taxonomy_version': 2,
            'native_ref': owner['native_ref'], 'native_data': owner['native_data'],
            'claims': owner['native_data'].get('claims', []), 'adapted': True}


def register_type(type_spec, adapter):
    """仅供可信 Python 集成代码登记；CLI/HTTP 不暴露此执行入口。"""
    from .contracts import check_schema
    if (not isinstance(type_spec, dict) or not isinstance(type_spec.get('owner_type'), str) or
            type_spec.get('schema_version') != 1 or type_spec.get('adapter_version') != 1 or
            not re.fullmatch(r'[a-z][a-z0-9-]*', type_spec['owner_type']) or
            not isinstance(type_spec.get('schema'), dict) or not callable(getattr(adapter, 'list_owners', None))):
        raise MemoryError('INVALID_SCHEMA', '扩展必须提供类型 schema、版本和可信适配器')
    try:
        check_schema(type_spec['schema'])
    except ValueError as exc:
        raise MemoryError('INVALID_SCHEMA', '扩展 schema 不是受支持契约', {'reason': str(exc)}) from exc
    name = type_spec['owner_type']
    if name in ROOT_TYPES.values() or name in _EXTENSIONS:
        raise MemoryError('INVALID_SCHEMA', '对象类型已登记')
    _EXTENSIONS[name] = (deepcopy(type_spec), adapter)

