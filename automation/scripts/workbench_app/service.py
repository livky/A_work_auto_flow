"""HTTP 和 CLI 共用应用服务；把业务读取、本机候选和视图偏好隔离。"""
import json
from pathlib import Path
import threading
import uuid
import evidence as e
import retrieval as r
from .storage import Store
from .jobs import Jobs
from . import projection as p
from . import analysis


class Service:
    def __init__(self, root, controller=None, enable_jobs=True):
        self.root = Path(root).resolve()
        self.controller = controller
        self.store = Store(root)
        self.jobs = Jobs(self.store) if enable_jobs else None
        self.graph = self.store.read('projection')
        self.guard = threading.RLock()
        self.freshness_result = None

    def close(self):
        if self.jobs:
            self.jobs.close()

    def rebuild(self, progress=lambda *_: None):
        graph = p.collect(self.root, progress)
        progress(1, 1)
        self.store.write('projection', graph)
        with self.guard:
            self.graph = graph
        return {'nodes': len(graph['nodes']), 'edges': len(graph['edges']), 'fingerprint': graph['fingerprint']}

    def require_graph(self):
        if self.graph is None:
            raise ValueError('尚未建立材料视图，请点击构建/刷新')
        if any(e.sha256(self.root / name) != digest for name, digest in self.graph.get('boundary', {}).items()):
            raise ValueError('材料读取范围已改变，请刷新投影，旧缓存暂不提供')
        return self.graph

    def view(self, options=None):
        options = options or {}
        allowed_keys = {'center', 'hops', 'query', 'excluded', 'kinds', 'types', 'limit', 'offset', 'candidates'}
        if set(options) - allowed_keys:
            raise ValueError('未知的图筛选参数')
        graph = self.require_graph()
        if options.get('candidates'):
            # 候选缓存只有与当前投影完全一致时才参与关系展示。
            cached = self.store.read('analysis', {})
            extra = [edge for item in cached.values() if item['fingerprint'] == graph['fingerprint'] for edge in item['edges']]
            graph = {**graph, 'edges': graph['edges'] + extra}
        return p.subgraph(graph, **{k: v for k, v in options.items() if k != 'candidates'})

    def freshness(self):
        """按需检查指纹，不在五秒状态轮询里哈希整个语料。"""
        current = p.collect(self.root)
        graph = self.require_graph()
        self.freshness_result = {'stale': current['fingerprint'] != graph['fingerprint'], 'checked_at': r.now(),
                                 'errors': current['errors']}
        return self.freshness_result

    def changed_files(self):
        """快速发现已有文件变化。新文件范围变化由完整版本检查/刷新发现。"""
        if not self.graph:
            return []
        changed = []
        for name, stamp in self.graph.get('file_stats', {}).items():
            try:
                path = p.allowed(self.root, name)
                stat = path.stat() if path.is_file() else None
                now = [stat.st_size, stat.st_mtime_ns] if stat else None
                if now != stamp:
                    changed.append(name)
            except (OSError, ValueError):
                changed.append(name)
        return changed

    def analyze(self, kind, seeds, excluded=(), progress=lambda *_: None):
        graph = self.require_graph()
        if self.changed_files():
            raise ValueError('材料已变化，请刷新投影后重新分析')
        graph = {**graph, 'nodes': [n for n in graph['nodes'] if n['id'] not in excluded],
                 'edges': [edge for edge in graph['edges'] if edge['source'] not in excluded and edge['target'] not in excluded]}
        ids = {n['id'] for n in graph['nodes']}
        if not isinstance(seeds, list) or not 1 <= len(seeds) <= 50 or len(set(seeds)) != len(seeds) or set(seeds) - ids:
            raise ValueError('选择 1–50 个不同的、未排除的种子材料')
        if kind == 'keywords':
            result = analysis.keyword_candidates(graph, seeds, progress)
        elif kind == 'semantic':
            result = analysis.semantic_candidates(self.root, graph, seeds, progress)
        else:
            raise ValueError('未知分析类型')
        result.update(fingerprint=graph['fingerprint'], created_at=r.now(), excluded=list(excluded))
        progress(1, 1)
        if self.changed_files():
            raise ValueError('分析期间材料变化；保留旧缓存，请刷新后重试')
        self.store.update('analysis', lambda old: {**(old or {}), kind: result})
        return result

    def preview(self, nid, fingerprint):
        graph = self.require_graph()
        node = next((n for n in graph['nodes'] if n['id'] == nid), None)
        if node is None or not node['path'] or node['fingerprint'] != fingerprint:
            raise ValueError('材料不在当前投影或版本不一致')
        path = p.allowed(self.root, node['path'])
        # 重新核对当前发现范围/显式引用，不沿用过期缓存的外部授权。
        cfg, source_list = p.sources(self.root)
        known = {Path(s['path']) for s in source_list}
        if path not in known:
            eg = e.EvidenceGraph(self.root)
            referenced = {n['path'] for n in eg.nodes.values()}
            for n in eg.nodes.values():
                refs = list(eg.refs(n)) + [{'target': a['path']} for key in ('inputs', 'artifacts') for a in n['raw'].get(key, []) if isinstance(a, dict) and 'path' in a]
                for ref in refs:
                    try:
                        referenced.add(p.allowed(self.root, ref['target']))
                    except (OSError, ValueError, KeyError):
                        pass
            if path not in referenced:
                raise ValueError('材料已不在当前登记范围；请刷新投影')
        current = e.sha256(path)
        if nid.startswith('FILE-'):
            expected = current
        else:
            ev = e.EvidenceGraph(self.root)
            expected = ev.nodes[nid]['fingerprint'] if nid in ev.nodes else current
        if expected != fingerprint:
            raise ValueError('原件已变化，请刷新投影后读取')
        text = '此格式请使用获准的本地应用查看；本视图不进行自动 OCR。'
        truncated = False
        if path.suffix.lower() in r.TEXT | {'.csv', '.tsv'}:
            with path.open('rb') as stream:
                data = stream.read(65537)
            truncated = len(data) > 65536
            text = data[:65536].decode('utf-8-sig', errors='replace')
        return {'path': node['path'], 'locator': node['locator'], 'text': text, 'truncated': truncated}

    def candidates(self):
        items = self.store.read('candidates', [])
        if not self.graph:
            return items
        self.require_graph()  # Range revocation also applies to saved suggestions.
        graph_nodes = {n['id']: n for n in self.graph['nodes']}
        current = e.EvidenceGraph(self.root)
        fingerprints = {}
        for ref in [ref for item in items for ref in item['refs']]:
            nid = ref['id']
            if nid in fingerprints:
                continue
            try:
                fingerprints[nid] = current.nodes[nid]['fingerprint'] if nid in current.nodes else e.sha256(p.allowed(self.root, graph_nodes[nid]['path']))
            except (OSError, ValueError, KeyError):
                fingerprints[nid] = None
        return [{**item, 'stale': any(fingerprints.get(ref['id']) != ref['fingerprint'] for ref in item['refs'])} for item in items]

    def save_candidate(self, item, dry_run=False):
        if set(item) - {'kind', 'title', 'explanation', 'refs', 'actor'}:
            raise ValueError('候选存在未知字段')
        if item.get('kind') not in {'relation', 'cluster-name', 'bridge-question'}:
            raise ValueError('候选类型无效')
        if not all(isinstance(item.get(k), str) and 0 < len(item[k]) <= 4000 for k in ('title', 'explanation', 'actor')):
            raise ValueError('候选需要标题、解释和提出者')
        nodes = {n['id']: n for n in self.require_graph()['nodes']}
        refs = item.get('refs', [])
        if not isinstance(refs, list) or not 1 <= len(refs) <= 50:
            raise ValueError('候选必须引用 1–50 个来源')
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != {'id', 'fingerprint', 'locator'} or ref['id'] not in nodes or not isinstance(ref['locator'], str) or not ref['locator'].strip():
                raise ValueError('候选来源需要当前 ID、指纹和定位')
            if not isinstance(ref['fingerprint'], str) or not __import__('re').fullmatch(r'[0-9a-f]{64}', ref['fingerprint']):
                raise ValueError('候选引用需要有效 SHA-256 指纹')
        value = {**item, 'id': uuid.uuid4().hex, 'status': 'pending', 'created_at': r.now(), 'history': []}
        if not dry_run:
            self.store.update('candidates', lambda old: (old or []) + [value])
        return value

    def resolve_candidate(self, jid, status, actor, note, dry_run=False):
        if status not in {'pending', 'dismissed', 'handled'} or not actor or not note:
            raise ValueError('处理需要有效状态、处理者和说明；handled 不表示已复核')
        def change(old):
            items = old or []
            item = next((i for i in items if i['id'] == jid), None)
            if not item:
                raise ValueError('找不到候选')
            item['history'].append({'from': item['status'], 'to': status, 'actor': actor, 'note': note, 'at': r.now()})
            item['status'] = status
            return items
        return change(self.store.read('candidates')) if dry_run else self.store.update('candidates', change)

    def request_job(self, data):
        kind = data.get('kind')
        if set(data) - {'kind', 'seeds', 'excluded'}:
            raise ValueError('未知任务参数')
        if kind == 'refresh':
            return self.jobs.submit(kind, self.rebuild)
        if kind == 'freshness':
            return self.jobs.submit(kind, lambda progress: self.freshness())
        if kind in {'keywords', 'semantic'}:
            return self.jobs.submit(kind, lambda progress: self.analyze(kind, data.get('seeds', []), data.get('excluded', []), progress))
        if self.controller and kind in {'monitor', 'doctor'}:
            return self.jobs.submit(kind, lambda progress: self.controller.action(kind))
        raise ValueError('不支持的任务类型')

    def save_view(self, view):
        if not isinstance(view, dict) or set(view) - {'name', 'positions', 'groups', 'center', 'excluded', 'mode'}:
            raise ValueError('视图字段无效')
        if len(json.dumps(view)) > 500_000:
            raise ValueError('视图偏好过大')
        positions, groups = view.get('positions', {}), view.get('groups', [])
        if not isinstance(positions, dict) or not isinstance(groups, list) or view.get('mode', 'radial') not in ('radial', 'groups', 'evidence'):
            raise ValueError('视图布局或模式无效')
        import math
        for pos in positions.values():
            if not isinstance(pos, dict) or set(pos) != {'x', 'y'} or not all(isinstance(n, (int, float)) and math.isfinite(n) for n in pos.values()):
                raise ValueError('位置必须是有限的 x/y 坐标')
        for group in groups:
            if not isinstance(group, dict) or set(group) != {'name', 'members'} or not isinstance(group['name'], str) or not isinstance(group['members'], list) or not all(isinstance(n, str) for n in group['members']):
                raise ValueError('视觉分组需要名称与成员 ID')
        if not isinstance(view.get('excluded', []), list) or not all(isinstance(n, str) for n in view.get('excluded', [])):
            raise ValueError('排除项需要 ID 列表')
        return self.store.write('view', view)
