"""从现有材料派生有类型关系，不修改事实记录，也不加载嵌入/OCR。

文件和元数据是事实源。归属、直接引用和传播路径必须分开，避免把检索
模块为了召回构造的组内完全图误当成证据。普通文件 ID 使用相对路径。
"""
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote
import evidence as e
import retrieval as r
from .storage import Store

KINDS = {'core-algorithms': 'algorithm', 'runs': 'run', 'research': 'research',
         'knowledge': 'knowledge', 'reports': 'report', 'projects': 'project',
         'data': 'data', 'tools': 'tool'}
TYPES = {'supports', 'input', 'background', 'contradicts', 'references', 'belongs_to',
         'produces', 'contains', 'depends_on', 'related', 'similar', 'keywords'}


def identity(text):
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def business_words(raw):
    """Only explicitly recorded keywords/aliases become lexical candidates."""
    return sorted({word for field in ('keywords', 'aliases')
                   for word in (raw.get(field, []) if isinstance(raw.get(field, []), list) else [])
                   if isinstance(word, str) and word.strip()})


def label_path(root, path):
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


def allowed(root, target):
    path = e.reference_path(root, target)
    if path.is_relative_to(root) and any(p in {'.local', '.git', 'node_modules', '_template', 'generated'} for p in path.relative_to(root).parts):
        raise ValueError('材料位于本机缓存或排除目录')
    return path


def sources(root):
    cfg = r.config(root)
    return cfg, r.discover(root, cfg)


def collect(root, progress=lambda *_: None):
    root = Path(root).resolve()
    cfg, discovered = sources(root)
    evidence = e.EvidenceGraph(root)
    nodes, edges, paths, errors = {}, {}, {}, list(evidence.errors)
    body_cache = {}

    def file_node(path, meta=None):
        path = allowed(root, str(path))
        if path in paths:
            return paths[path]
        if len(paths) >= cfg['max_files']:
            raise ValueError('材料数量超过 max_files，未生成部分投影')
        rel = label_path(root, path)
        nid = 'FILE-' + identity(rel)
        item = {'id': nid, 'title': path.name, 'kind': KINDS.get(rel.split('/')[0], 'material'),
                'path': rel, 'fingerprint': '', 'keywords': [], 'review': {}, 'risks': [],
                'execution_status': None, 'scope': None, 'locator': '', 'owner': None,
                'record_reason': '', 'statement': '', 'missing': not path.is_file()}
        if path.is_file():
            before = path.stat()
            if before.st_size > cfg['max_file_bytes']:
                item['risks'].append('超出读取上限')
            else:
                item['fingerprint'] = e.sha256(path)
                if path.suffix.lower() in {'.md', '.json', '.txt', '.py', '.csv'} and before.st_size <= 1_000_000:
                    try:
                        body = path.read_text(encoding='utf-8-sig')
                        body_cache[nid] = body
                        if path.suffix.lower() == '.md':
                            heading = re.search(r'^#\s+(.+)', body, re.M)
                            if heading:
                                item['title'] = heading[1]
                        elif path.suffix.lower() == '.json':
                            raw = json.loads(body)
                            if isinstance(raw, dict):
                                item['title'] = raw.get('title') or item['title']
                                item['keywords'] = business_words(raw)
                    except (ValueError, UnicodeError) as exc:
                        item['risks'].append('无法读取文本：' + str(exc))
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError('扫描期间文件变化，请重新构建投影')
        else:
            item['risks'].append('来源不存在')
        if meta:
            item['title'] = meta.get('title') or item['title']
            item['keywords'] = sorted(set(item['keywords'] + business_words(meta)))
            item['level'] = meta.get('memory_level')
        nodes[nid], paths[path] = item, nid
        return nid

    def edge(source, target, relation, origin, locator='', inferred=False):
        if source == target or source not in nodes or target not in nodes:
            return
        eid = 'EDGE-' + identity(json.dumps([source, target, relation, origin, locator], ensure_ascii=False))
        edges[eid] = {'id': eid, 'source': source, 'target': target, 'type': relation,
                      'origin': origin, 'locator': str(locator), 'derived': inferred,
                      'candidate': False, 'original_source': source, 'original_target': target,
                      'display_source': source, 'display_target': target}
        return edges[eid]

    for index, src in enumerate(discovered):
        try:
            file_node(Path(src['path']), src)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
        progress(index + 1, len(discovered))
    # 稳定业务 ID 与文件 ID 分开：同一个 JSON 可承载多个结论。
    for nid, node in evidence.nodes.items():
        raw = node['raw']
        kind = 'claim' if node['kind'] == 'claim' else KINDS.get(label_path(root, node['path']).split('/')[0], 'material')
        nodes[nid] = {'id': nid, 'title': raw.get('title') or raw.get('statement') or nid,
                      'kind': kind, 'path': label_path(root, node['path']), 'fingerprint': node['fingerprint'],
                      'keywords': business_words(raw), 'review': raw.get('review', {}),
                      'risks': sorted(node['blockers']), 'execution_status': raw.get('status'),
                      'scope': raw.get('scope'), 'locator': 'claim:' + nid if kind == 'claim' else 'metadata',
                      'owner': node['owner'], 'record_reason': raw.get('record_reason') or raw.get('question') or '',
                      'statement': raw.get('statement') or raw.get('conclusion') or '', 'missing': False}
    # 补充 EvidenceGraph 尚未建模的项目、工具和数据卡的稳定主体。
    for fid, body in list(body_cache.items()):
        if nodes[fid]['path'].endswith('.json'):
            try:
                raw = json.loads(body)
                # A reference such as run.project_id must never create a project
                # whose title and fingerprint actually belong to that Run.
                keys = {'project.json': ('project_id',), 'tool.json': ('tool_id',),
                        'dataset.json': ('dataset_id',)}.get(Path(nodes[fid]['path']).name, ())
                if nodes[fid]['path'].endswith('.dataset.json'):
                    keys = ('dataset_id',)
                for key in keys:
                    nid = raw.get(key) if isinstance(raw, dict) else None
                    if isinstance(nid, str) and nid and nid not in nodes:
                        nodes[nid] = {**nodes[fid], 'id': nid, 'locator': key}
                        edge(nid, fid, 'contains', nodes[fid]['path'], key)
            except ValueError:
                pass

    def target(value):
        if value in nodes:
            return value
        if re.match(r'^(RUN|CLM|RES|MOD|EVD|PRJ|DATA|TOOL)-', str(value)):
            nodes[value] = {'id': value, 'title': value, 'kind': 'material', 'path': '', 'fingerprint': '',
                            'keywords': [], 'review': {}, 'risks': ['未登记对象'], 'missing': True,
                            'execution_status': None, 'scope': None, 'locator': '', 'owner': None,
                            'record_reason': '', 'statement': ''}
            return value
        return file_node(allowed(root, value))

    for nid, node in evidence.nodes.items():
        raw = node['raw']
        if node['owner']:
            edge(node['owner'], nid, 'contains', nodes[nid]['path'], 'claims')
        else:
            fid = file_node(node['path'])
            edge(nid, fid, 'contains', nodes[nid]['path'], 'metadata')
        refs = [(ref, 'evidence_refs' if node['owner'] else 'dependencies') for ref in evidence.refs(node)]
        for ref, field in refs:
            if not isinstance(ref, dict) or ref.get('relation') not in e.RELATIONS:
                continue
            try:
                tid = target(ref['target'])
                last = edge(nid, tid, ref['relation'], nodes[nid]['path'] + '#' + field, ref.get('locator', ''))
                if last:
                    last['expected_fingerprint'] = ref.get('sha256', '')
                    last['version_matches'] = bool(ref.get('sha256')) and ref['sha256'] == nodes[tid]['fingerprint']
            except (OSError, ValueError, KeyError) as exc:
                errors.append(str(exc))
        for field, relation in (('inputs', 'input'), ('artifacts', 'produces')):
            for ref in raw.get(field, []):
                if isinstance(ref, dict) and isinstance(ref.get('path'), str):
                    try:
                        target_id = target(ref['path'])
                        # Run input/output files are raw evidence. Merely
                        # linking them from a Run does not create an L1 paper.
                        if nodes[target_id]['id'].startswith('FILE-'):
                            nodes[target_id]['level'] = 'L0'
                        edge(nid, target_id, relation, nodes[nid]['path'], field)
                    except (OSError, ValueError) as exc:
                        errors.append(str(exc))
        for field in ('related_module_ids', 'module_ids', 'related_research_ids', 'related_project_ids'):
            for tid in raw.get(field, []):
                if isinstance(tid, str):
                    edge(nid, target(tid), 'belongs_to', nodes[nid]['path'], field)
        for tid in raw.get('parent_run_ids', []):
            edge(nid, target(tid), 'depends_on', nodes[nid]['path'], 'parent_run_ids')

    for src in discovered:
        path = Path(src['path'])
        fid = paths.get(path)
        if not fid:
            continue
        owner = evidence.owner_for(path)
        if not owner:
            # Only registered identity cards confer directory membership.
            candidates = [n for n in nodes.values() if n.get('locator') in {'project_id', 'tool_id'}
                          and path.is_relative_to((root / n['path']).parent)]
            if candidates:
                owner = max(candidates, key=lambda n: len(n['path']))['id']
        if owner and nodes[owner]['path'] != nodes[fid]['path']:
            edge(fid, owner, 'belongs_to', nodes[owner]['path'], 'directory', True)
        linked = [(p, 'related', 'sources.related') for p in src.get('related', [])]
        if path.suffix.lower() == '.md':
            for match in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', body_cache.get(fid, '')):
                raw = unquote(match[1].strip().strip('<>'))
                dest = raw.split('#')[0]
                if dest and '://' not in dest:
                    linked.append((str((path.parent / dest).resolve()), 'references', 'line ' + str(body_cache[fid][:match.start()].count('\n') + 1)))
        for dest, rel, loc in linked:
            try:
                edge(fid, target(dest), rel, nodes[fid]['path'], loc)
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
    # Canonical memory records are graph entities, never new FILE aliases of
    # immutable JSON. L0 remains available by fixed references, not normal graph
    # discovery. Unclassified legacy materials keep level=None for opt-in use.
    from memory.document import Reader
    from memory.service import MemoryService
    from memory.contracts import project_memory_level
    from memory.evidence_adapter import iter_refs
    from memory.errors import MemoryError
    reader = Reader(MemoryService(root))
    memory_records = {}
    for oid, view in reader.views.items():
        if view['native_data'].get('sensitivity') == 'restricted':
            continue
        if oid in nodes and view['owner_type'] == 'run':
            nodes[oid]['level'] = 'L2'
        state = reader.state(oid)
        for rid, record in state['records'].items():
            level = project_memory_level(record)
            if level not in {'L1', 'L2', 'L3', 'L4'} or record['sensitivity'] == 'restricted':
                continue
            issues, denied = [], False
            for ref in iter_refs({'sources': record['sources'], 'payload': record['payload']}):
                try:
                    reader.check_ref(ref)
                except MemoryError as exc:
                    issues.append(exc.code)
                    denied = denied or exc.code in {'ACCESS_DENIED', 'UNSAFE_PATH'}
            if denied:
                continue
            nodes[rid] = {'id': rid, 'title': record['title'], 'kind': record['kind'],
                'level': level, 'owner': oid, 'path': view['native_ref']['path'],
                'fingerprint': record['record_hash'], 'keywords': record['keywords'],
                'review': {}, 'risks': sorted(set(issues)), 'locator': 'memory:' + rid,
                'record_reason': record['record_reason'], 'statement': record['body_markdown'],
                'record_revision': record['revision'], 'missing': False}
            memory_records[rid] = record
    for rid, record in memory_records.items():
        for ref in iter_refs({'sources': record['sources'], 'payload': record['payload']}):
            edge(rid, ref['target_id'], ref.get('relation', 'references'),
                 nodes[rid]['path'], 'fixed memory reference')
    reader.recheck()
    for node in nodes.values():
        node.setdefault('level', None)
    result = {'schema_version': 1, 'generated_at': r.now(), 'nodes': list(nodes.values()), 'edges': list(edges.values()),
              'errors': sorted(set(errors)), 'coverage': {'files': len(paths), 'index_only': False,
                'excluded': ['模板、导航规则、缓存和未登记外部目录'], 'unread': '非文本内容仅登记元数据；正文通过原有检索/预览按需读取'},
              'synthetic': (root / 'synthetic-marker.json').exists()}
    result['file_stats'] = {label_path(root, path): [path.stat().st_size, path.stat().st_mtime_ns] if path.is_file() else None for path in paths}
    result['boundary'] = {name: e.sha256(root / name) for name in ('retrieval/config.json', 'retrieval/sources.json')}
    for oid, state in reader.states.items():
        if state['head']:
            for name in (reader.views[oid]['native_ref']['path'], reader.views[oid]['memory_home'] + '/HEAD.json'):
                result['boundary'][name] = e.sha256(root / name)
    result['fingerprint'] = e.fingerprint({'nodes': result['nodes'], 'edges': result['edges']})
    return result


def subgraph(graph, center='', hops=1, query='', excluded=(), kinds=(), types=(), limit=300, offset=0, levels=()):
    """所有筛选先于范围导出；局部 BFS 不穿过被排除节点。"""
    limit = max(1, min(int(limit), 300))
    if hops not in (1, 2):
        raise ValueError('展开深度只能为 1 或 2')
    eligible = {n['id']: n for n in graph['nodes'] if n['id'] not in excluded and
                (not levels or (n.get('level') or 'native') in levels) and
                (not kinds or n['kind'] in kinds) and (not query or query.casefold() in (n['title'] + ' ' + n['id']).casefold())}
    edges = [edge for edge in graph['edges'] if edge['source'] in eligible and edge['target'] in eligible and (not types or edge['type'] in types)]
    if center:
        if center not in eligible:
            raise ValueError('中心对象不在当前可见范围')
        adjacent = {}
        for edge in edges:
            adjacent.setdefault(edge['source'], set()).add(edge['target'])
            adjacent.setdefault(edge['target'], set()).add(edge['source'])
        seen, frontier = {center}, {center}
        for _ in range(hops):
            frontier = {v for u in frontier for v in adjacent.get(u, ())} - seen
            seen.update(frontier)
        eligible = {nid: n for nid, n in eligible.items() if nid in seen}
    ordered = sorted(eligible, key=lambda nid: (nid != center, eligible[nid]['kind'], nid))
    shown = set(ordered[offset:offset + limit])
    visible_edges = [edge for edge in edges if edge['source'] in shown and edge['target'] in shown]
    exported = {k: v for k, v in graph.items() if k not in {'file_stats', 'boundary'}}
    return {**exported, 'nodes': [eligible[nid] for nid in ordered if nid in shown], 'edges': visible_edges[:1000],
            'selection': {'center': center, 'hops': hops, 'query': query, 'excluded': list(excluded),
                          'kinds': list(kinds), 'types': list(types), 'levels': list(levels), 'offset': offset},
            'omitted_nodes': len(eligible) - len(shown), 'omitted_edges': max(0, len(visible_edges) - 1000)}
