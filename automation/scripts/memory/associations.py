"""可解释导航候选与有界遍历；相似度不会生成科学支持或复核状态。"""
from copy import deepcopy
import math
import unicodedata

from . import owners, contracts
from .errors import MemoryError


def _terms(values):
    return {unicodedata.normalize("NFKC", str(x)).strip().casefold() for x in values if str(x).strip()}


def keyword_candidates(left, right, *, threshold=0.3):
    """Jaccard=交集大小/并集大小；至少两个共有词以排除偶然单词命中。"""
    a, b = _terms(left), _terms(right)
    shared = a & b
    score = len(shared) / len(a | b) if a | b else 0.0
    return {"method": "keyword", "score": score, "threshold": threshold,
            "shared": sorted(shared), "left_only": sorted(a-b), "right_only": sorted(b-a),
            "eligible": len(shared) >= 2 and score >= threshold, "status": "candidate"}


def semantic_candidates(left, right, *, encoder, model, source_versions, threshold=0.8):
    """注入向量只计算余弦；调用者必须附实际编码器及固定来源版本。"""
    if not left or len(left) != len(right) or not all(math.isfinite(x) for x in [*left, *right]):
        raise MemoryError("INVALID_ARGUMENT", "向量维度不一致、为空或包含非有限值")
    denominator = math.sqrt(sum(x*x for x in left) * sum(x*x for x in right))
    score = sum(a*b for a,b in zip(left,right)) / denominator if denominator else 0.0
    return {"method": "semantic", "score": score, "threshold": threshold,
            "eligible": bool(denominator) and score >= threshold, "encoder": encoder,
            "model": model, "source_versions": deepcopy(source_versions), "status": "candidate"}


def record_ref(record, relation="references"):
    return {"target_kind": "record", "target_id": record["record_id"], "revision": record["revision"],
            "sha256": None, "locator": "", "relation": relation}


def source_lineage(service, target_ids):
    """公开来源身份投影；派生/类比关系不能增加科学支持计数。"""
    from .lineage import project
    return project(service, target_ids)


def _visible(service, record, request):
    """发现范围不是授权。先过滤，再计算相似度或展开，避免泄露受限正文。"""
    excluded = set(request.get("exclude_ids", []))
    if record["record_id"] in excluded or record["owner_id"] in excluded or record["sensitivity"] == "restricted":
        return False
    selected = set(request.get("include_ids", [])) | set(request.get("full_ids", []))
    return (record["owner_id"] == request.get("owner_id") or record["record_id"] in selected
            or record["owner_id"] in selected or record["discovery"] == "workspace_summary")


def _records(service):
    for owner in owners.list_owners(service.root):
        if owner["native_data"].get("sensitivity") == "restricted":
            continue
        yield from service.store.read_snapshot(owner)["records"].values()


def view(service, record):
    """回源比较两端当前版本；历史引用仍保留，不偷偷升级关系依据。"""
    changed = []
    for endpoint in (record["payload"]["from"], record["payload"]["to"]):
        try:
            value = service._resolve_ref(endpoint, {}, [])
            if endpoint["target_kind"] == "record":
                current = service.store.read_snapshot(owners.resolve_owner(service.root, value["owner_id"]))["records"][value["record_id"]]
                if current["revision"] != endpoint["revision"]:
                    changed.append({"target_id": endpoint["target_id"], "reason": "revision_changed", "current_revision": current["revision"]})
        except MemoryError as exc:
            changed.append({"target_id": endpoint["target_id"], "reason": exc.code})
    return {"record": record, "stale": bool(changed), "changed_endpoints": changed}


def _indexed_endpoint_views(service, rows, request, adapter):
    """Read either endpoint through one cached canonical edge, then revalidate.

    Reverse views are inspection metadata, not newly persisted relationships
    and not authorization to reverse a directed automatic graph walk.
    """
    from . import index
    seeds = set(request.get('seeds', []))
    if not seeds:
        return None
    excluded = set(request.get('exclude_ids', []))
    seeds -= excluded
    by_id = {row['record_id']: row for row in rows}
    cached = index.connect(service.root, create=False)
    if cached is None:
        return {'candidates': [], 'neighbors': [], 'missing': [{'code': 'INDEX_PENDING'}]}
    try:
        edge_ids = {row['association_id'] for row in cached.execute('SELECT association_id,from_id,to_id FROM memory_edges')
                    if row['from_id'] in seeds or row['to_id'] in seeds}
    finally:
        cached.close()
    candidates, neighbors = [], []
    for rid in sorted(edge_ids):
        record = by_id.get(rid)
        if not record or record['kind'] != 'association':
            continue
        payload = record['payload']
        refs = [payload['from'], payload['to']]
        # Exclusion and discovery apply to both ends before any view is
        # returned. A cached edge never exposes a hidden endpoint's prose.
        denied = False
        for ref in refs:
            target = ref['target_id']
            if target in excluded:
                denied = True; break
            if ref['target_kind'] == 'record' and target not in by_id:
                denied = True; break
            if ref['target_kind'] == 'claim':
                value = adapter.resolve_claim(target)
                if value['owner_id'] in excluded or (value.get('record') and value['record']['record_id'] not in by_id):
                    denied = True; break
            if ref['target_kind'] != 'file' and adapter.access_errors(ref):
                denied = True; break
        if denied:
            continue
        current = view(service, record)
        candidates.append(current)
        if current['stale'] or payload['status'] != 'accepted':
            continue
        for side, other in ((0, 1), (1, 0)):
            if refs[side]['target_id'] in seeds:
                neighbors.append({'association_id': rid, 'association_revision': record['revision'],
                    'from_id': refs[side]['target_id'], 'target_id': refs[other]['target_id'],
                    'source_ref': deepcopy(refs[other]), 'relation': payload['relation'],
                    'direction': 'forward' if side == 0 else 'reverse', 'derived_view': True,
                    'shared_structure': payload['shared_structure'], 'transfer_limits': deepcopy(payload['transfer_limits'])})
    return {'candidates': candidates, 'neighbors': neighbors, 'missing': []}


def propose(service, request):
    method = request.get("method", "keyword")
    rows = [r for r in _records(service) if _visible(service, r, request)]
    from .evidence_adapter import EvidenceAdapter
    adapter = EvidenceAdapter(service)
    rows = [r for r in rows if not adapter.access_errors(r["record_id"])]
    if method == "explicit":
        endpoint_views = _indexed_endpoint_views(service, rows, request, adapter)
        if endpoint_views is not None:
            return endpoint_views
        return {"candidates": [view(service, r) for r in rows if r["kind"] == "association"]}
    if method not in {"keyword", "semantic"}:
        raise MemoryError("INVALID_ARGUMENT", "未知相关性方法")
    seeds = set(request.get("seeds", []))
    if not seeds:
        raise MemoryError("INVALID_ARGUMENT", "相关性分析需要 seeds")
    rows = [r for r in rows if r["kind"] not in {"association", "review", "policy"}]
    vectors, metadata = {}, {}
    if method == "semantic":
        # The existing backend loads the pinned local model with its offline
        # checks. An unavailable encoder is an error, never an online fallback.
        try:
            import retrieval
            from qdrant_backend import LocalBackend
            backend = LocalBackend(service.root, retrieval.config(service.root))
            try:
                vectors = dict(zip((r["record_id"] for r in rows),
                                   (list(v) for v in backend.model.embed([r["body_markdown"] for r in rows]))))
                metadata = {"encoder": "fastembed", "model": str(backend.collection)}
            finally:
                backend.close()
        except (ImportError, OSError, ValueError) as exc:
            raise MemoryError("CAPABILITY_UNAVAILABLE", "本地语义模型不可用", {"reason": str(exc)}) from exc
    candidates, seen = [], set()
    for left in rows:
        if left["record_id"] not in seeds:
            continue
        for right in rows:
            pair = tuple(sorted((left["record_id"], right["record_id"])))
            if left is right or pair in seen:
                continue
            seen.add(pair)
            refs = [record_ref(left), record_ref(right)]
            result = (keyword_candidates(left["keywords"], right["keywords"], threshold=request.get("threshold", .3))
                      if method == "keyword" else semantic_candidates(vectors[left["record_id"]], vectors[right["record_id"]],
                          **metadata, source_versions=refs, threshold=request.get("threshold", .8)))
            if result["eligible"]:
                candidates.append({**result, "from": refs[0], "to": refs[1]})
    return {"candidates": sorted(candidates, key=lambda x: (-x["score"], x["to"]["target_id"]))}


def decide(service, request):
    """所有处理状态都提交同一记录的修订；反向关系仅在读取时生成。"""
    payload = deepcopy(request["payload"])
    if payload.get("relation") in {"supports", "input"}:
        raise MemoryError("INVALID_ARGUMENT", "相关性服务只保存导航关系")
    owner = owners.resolve_owner(service.root, request["owner_id"])
    snapshot = service.store.read_snapshot(owner)
    def identity(p):
        endpoints = (p["from"]["target_id"], p["to"]["target_id"])
        if p["relation"] in {"analogous_to", "same_problem", "same_failure_mode"}:
            endpoints = tuple(sorted(endpoints))
        return (*endpoints, p["relation"])
    for record in _records(service):
        if record["kind"] == "association" and identity(record["payload"]) == identity(payload) and record["owner_id"] != request["owner_id"]:
            raise MemoryError("VERSION_CONFLICT", "这条关联已有规范归属，请在原对象中修订", {"owner_id": record["owner_id"], "record_id": record["record_id"]})
    matches = [r for r in snapshot["records"].values() if r["kind"] == "association" and identity(r["payload"]) == identity(payload)]
    draft = {"owner_id": request["owner_id"], "kind": "association", "title": request.get("title", "相关性判断"),
             "body_markdown": request.get("body_markdown", ""), "keywords": [], "payload": payload,
             "sources": deepcopy(payload["basis_refs"]), "provenance_gap": None if payload["basis_refs"] else "仅导航关系，尚缺独立依据",
             "record_reason": request["reason"], "change_reason": request["reason"],
             "sensitivity": request.get("sensitivity", "internal"), "discovery": request.get("discovery", "owner_only")}
    operation = {"op": "decide_association", "draft": draft}
    if matches:
        operation.update(record_id=matches[0]["record_id"], expected_revision=request.get("expected_revision", matches[0]["revision"]))
    else:
        operation["client_key"] = "association"
    digest = contracts.canonical_hash({"operation": "association", "request": {
        k: v for k, v in request.items() if k not in {"request_id", "dry_run"}}})
    return service._commit({"schema_version": 1, "request_id": request["request_id"], "actor": request["actor"],
                           "owner_id": request["owner_id"], "expected_head": request["expected_head"],
                           "operations": [operation], "dry_run": request.get("dry_run", False)}, request_hash=digest)


def expand_neighbors(seeds, edges, *, hops=1, exclude_ids=(), allowed_ids=None, expansion_count=0, limit=24):
    """在遍历之前删去禁止节点；绝不允许它成为通往其他节点的隐形桥梁。"""
    if hops not in {1, 2} or expansion_count >= 2 or limit < 0:
        raise MemoryError("INVALID_ARGUMENT", "邻接扩展最多两跳、两次且不能使用负上限")
    excluded = set(exclude_ids)
    allowed = None if allowed_ids is None else set(allowed_ids)
    usable = lambda n: n not in excluded and (allowed is None or n in allowed)
    adjacency = {}
    for edge in edges:
        record = edge.get('record', edge)
        p = record.get("payload", record)
        if p.get("status") != "accepted" or edge.get("stale") or p.get("relation") in {"supports", "input"}:
            continue
        a, b = p["from"]["target_id"], p["to"]["target_id"]
        if usable(a) and usable(b):
            adjacency.setdefault(a, set()).add(b)
            # The frozen directed A→B/C→D graph must not gain E via E→A.
            # Only explicitly symmetric relation types permit reverse walks.
            if p.get('relation') in {'analogous_to', 'same_problem', 'same_failure_mode'}:
                adjacency.setdefault(b, set()).add(a)
    visited = {s for s in seeds if usable(s)}
    frontier = [(s, [s]) for s in sorted(visited)]
    result = []
    for _ in range(hops):
        next_frontier = []
        for node, path in frontier:
            for neighbor in sorted(adjacency.get(node, ())):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                if len(result) >= limit:
                    return result
                result.append({"target_id": neighbor, "path": [*path, neighbor]})
                next_frontier.append((neighbor, [*path, neighbor]))
        frontier = next_frontier
    return result
