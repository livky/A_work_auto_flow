"""按需产生候选。结果不进入 EvidenceGraph，不提升任何业务结论的可信状态。"""
from collections import defaultdict
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import evidence as e
import retrieval as r
from .projection import identity, allowed


def keyword_candidates(graph, seeds, progress=lambda *_: None):
    nodes = {n['id']: n for n in graph['nodes']}
    inverted = defaultdict(set)
    for n in nodes.values():
        for word in n['keywords']:
            inverted[str(word).casefold()].add(n['id'])
    pairs = []
    for i, sid in enumerate(seeds):
        shared = defaultdict(set)
        for word in nodes[sid]['keywords']:
            for target in inverted[str(word).casefold()] - {sid}:
                shared[target].add(word)
        for tid, words in sorted(shared.items(), key=lambda x: (-len(x[1]), x[0]))[:10]:
            pairs.append(candidate(sid, tid, 'keywords', '共享业务关键词：' + '、'.join(sorted(words)),
                                   shared_keywords=sorted(words)))
        progress(i + 1, len(seeds))
    return {'edges': pairs, 'coverage': {'seeds': seeds, 'method': 'recorded-keywords', 'complete_pairwise': False}}


def candidate(sid, tid, kind, reason, **extra):
    return {'id': 'CAND-' + identity(sid + tid + kind), 'source': sid, 'target': tid, 'type': kind,
            'origin': reason, 'locator': '', 'derived': True, 'candidate': True,
            'original_source': sid, 'original_target': tid, 'display_source': sid, 'display_target': tid, **extra}


def semantic_candidates(root, graph, seeds, progress=lambda *_: None):
    """仅查询已存在的同模型向量，不初始化集合、索引、编码器或网络。

每个文件最多均匀采样八个已有片段向量。查询返回源片段定位及采样覆盖，
不把 max 分数当概率。Qdrant 自身排他锁防止与 CLI 并发打开存储。
"""
    import qdrant_backend as qb
    from importlib.metadata import version
    root = Path(root).resolve()
    cfg = r.config(root)
    if not qb.enabled(cfg):
        raise ValueError('语义功能不可用：未配置本地向量存储')
    try:
        from qdrant_client import QdrantClient, models
    except ImportError as exc:
        raise ValueError('语义功能不可用：本机缺少向量依赖，请使用完整安装配置') from exc
    setting = cfg['embedding']
    manifest = e.read(root / setting['manifest'])
    model_path = root / setting['path']
    qb.verify_model(str(model_path), tuple(sorted(manifest['files'].items())))
    model_id = 'workspace_' + __import__('hashlib').sha256(json.dumps({'model': manifest, 'fastembed': version('fastembed'),
                         'encoding': 'passage-query-window-v1'}, sort_keys=True).encode()).hexdigest()[:12]
    storage = (root / cfg['vector_store']['path']).resolve()
    database = root / 'retrieval/generated/search.sqlite3'
    if not storage.is_relative_to(root) or not (storage / 'meta.json').exists() or not database.exists():
        raise ValueError('缺少既有索引；请先运行 index-knowledge')
    # 读取 SQLite 的 ready 快照；先验证当前源指纹，过期向量不参与候选。
    # A sqlite context manager commits/rolls back but does not close the handle.
    # Explicit closure matters on Windows, where an open reader blocks migration.
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        docs = r.read_docs(db)
    by_path = {str(allowed(root, n['path'])): n for n in graph['nodes'] if n['path'] and n['id'].startswith('FILE-')}
    current = {sid: by_path[doc['path']] for sid, doc in docs.items() if doc['path'] in by_path and doc['digest'] == by_path[doc['path']]['fingerprint']}
    if not current:
        raise ValueError('没有指纹匹配的已索引材料；请更新索引')
    lookup = {n['id']: n for n in graph['nodes']}
    source_by_path = {doc['path']: sid for sid, doc in docs.items() if sid in current}
    try:
        client = QdrantClient(path=str(storage))
    except RuntimeError as exc:
        raise ValueError('向量存储正被其他任务使用；稍后重试，不清除其锁') from exc
    output, coverage = [], []
    try:
        if not client.collection_exists(model_id):
            raise ValueError('当前模型集合不存在；请更新索引')
        for i, seed in enumerate(seeds):
            sid = source_by_path.get(str(allowed(root, lookup[seed]['path'])))
            if not sid:
                coverage.append({'seed': seed, 'error': '无当前版本片段向量', 'sampled': 0})
                progress(i + 1, len(seeds))
                continue
            points, cursor = [], None
            while True:
                batch, cursor = client.scroll(model_id, scroll_filter=models.Filter(must=[models.FieldCondition(
                    key='source_id', match=models.MatchValue(value=sid))]), limit=128, offset=cursor,
                    with_vectors=True, with_payload=True)
                # A partially refreshed index may retain old chunks for the same
                # source ID; only vectors for its ready digest are eligible.
                points.extend(point for point in batch if point.payload.get('digest') == docs[sid]['digest'])
                progress(i, len(seeds))  # 分页边界可取消。
                if cursor is None:
                    break
            points.sort(key=lambda p: (p.payload.get('start', 0), str(p.id)))
            indices = sorted({round(j * (len(points) - 1) / max(1, min(8, len(points)) - 1)) for j in range(min(8, len(points)))})
            matches = {}
            for j in indices:
                p = points[j]
                # 只允许当前图中授权且版本匹配的来源；不会泄漏被排除材料的分数或标题。
                hits = client.query_points(model_id, query=p.vector, limit=100,
                    query_filter=models.Filter(must=[models.FieldCondition(key='source_id', match=models.MatchAny(any=list(current)))]),
                    with_payload=True).points
                for hit in hits:
                    other = hit.payload.get('source_id')
                    if other == sid or other not in current or hit.payload.get('digest') != docs[other]['digest']:
                        continue
                    if other not in matches or hit.score > matches[other]['score']:
                        matches[other] = {'score': float(hit.score), 'seed_locator': p.payload,
                                          'match_locator': hit.payload}
                progress(i, len(seeds))
            for other, info in sorted(matches.items(), key=lambda x: (-x[1]['score'], x[0]))[:10]:
                output.append(candidate(seed, current[other]['id'], 'similar', '本地片段余弦相似候选',
                                        model_id=model_id, **info))
            coverage.append({'seed': seed, 'total_chunks': len(points), 'sampled': len(indices),
                             'sampled_indices': indices, 'omitted_chunks': len(points) - len(indices)})
            progress(i + 1, len(seeds))
    finally:
        client.close()
    return {'edges': output, 'coverage': {'seeds': coverage, 'model_id': model_id, 'complete_pairwise': False,
            'note': '每源最多八个均匀片段；每片段前100命中合并为前10材料，无业务校准阈值'}}


def export_summary(graph, question=''):
    """导出当前选择本身，不额外扩展正文或目录；机器版保留全部关系字段。"""
    title = {n['id']: n['title'] for n in graph['nodes']}
    rows = ['# 材料关系摘要', '', '问题：' + question, '生成时间：' + graph['generated_at'],
            '投影指纹：' + graph['fingerprint'], '', '## 材料']
    for n in graph['nodes']:
        rows.append(f"- {n['id']} | {n['title']} | {n['path']} | 定位 {n.get('locator') or '未提供'} | 指纹 {n['fingerprint']} | 复核 {n['review'].get('status', 'not-reviewed')} | 执行 {n.get('execution_status') or '未提供'} | 范围 {n.get('scope') or '未提供'} | 风险 {', '.join(n['risks']) or '当前未报告'}")
    rows += ['', '## 关系（起点引用或关联终点）']
    for edge in graph['edges']:
        detail = {key: edge[key] for key in ('score', 'model_id', 'seed_locator', 'match_locator', 'version_matches') if key in edge}
        rows.append(f"- {edge['source']} → {edge['target']} [{edge['type']}] {'候选' if edge['candidate'] else '派生' if edge['derived'] else '已记录'}；{edge['origin']}；{edge['locator']}；{json.dumps(detail, ensure_ascii=False)}")
    rows += ['', '## 范围与缺口', json.dumps({k: graph.get(k) for k in ('selection', 'coverage', 'errors', 'omitted_nodes', 'omitted_edges')}, ensure_ascii=False),
             '', '关联不等于正确。请核对版本、适用范围和反证，保留排除项与预算，再按需读取原文。']
    return {'schema_version': 1, 'question': question, 'graph': graph, 'markdown': '\n'.join(rows)}
