"""可复算检索评价，开发与留出分割显式分开，不把合成指标当业务验收。

本模块不自动修改阈值/标注或执行留出排名。W06 默认只读取 development
集合；W13 的最终调用必须显式指定 phase='final' 才允许评估 holdout。
不同方案由真实 runner 提供，不把同一实现贴三个标签当比较结果。
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import time

from .contracts import canonical_hash
from .errors import MemoryError
from .store import utc_now


def ranking_metrics(relevant, ranking, *, k=6):
    """按规范 ID 算 Recall@k 与 nDCG@k；重复输出另计，不能重复得分。

    relevant 可为 {ID:grade} 或 canonical_id/grade 列表。增益 2^grade-1，
    位置折扣 log2(rank+1)。返回实际分子分母，便于固定 Run 独立复算。
    """
    if type(k) is not int or k < 1:
        raise MemoryError("INVALID_ARGUMENT", "k 必须为正整数")
    labels = dict(relevant) if isinstance(relevant, dict) else {row["canonical_id"]: row["grade"] for row in relevant}
    if any(type(grade) is not int or grade < 0 for grade in labels.values()):
        raise MemoryError("INVALID_ARGUMENT", "相关性 grade 必须为非负整数")
    ids = [row if isinstance(row, str) else row["canonical_id"] for row in ranking]
    unique = list(dict.fromkeys(ids))
    positives = {cid for cid, grade in labels.items() if grade >= 1}
    retrieved = unique[:k]
    matched = len(positives.intersection(retrieved))
    dcg = sum((2 ** labels.get(cid, 0) - 1) / math.log2(rank + 1) for rank, cid in enumerate(retrieved, 1))
    ideal_grades = sorted(labels.values(), reverse=True)[:k]
    idcg = sum((2 ** grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal_grades, 1))
    return {"recall": matched / len(positives) if positives else None,
            "ndcg": dcg / idcg if idcg else None, "matched": matched, "relevant_count": len(positives),
            "dcg": dcg, "ideal_dcg": idcg, "duplicates": len(ids) - len(unique),
            "returned_count": len(ids), "canonical_ids": retrieved}


def load_queries(path, *, split="development", phase="development"):
    """筛选冻结配方；任何非最终调用读取 holdout 都明确拒绝。"""
    if split not in {"development", "holdout"} or phase not in {"development", "final"}:
        raise MemoryError("INVALID_ARGUMENT", "未知评价阶段或数据分割")
    if split == "holdout" and phase != "final":
        raise MemoryError("ACCESS_DENIED", "留出查询仅在 W13 最终评价运行，不用于开发调参")
    path = Path(path)
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    queries = [row for row in data["queries"] if row["split"] == split]
    return {"queries": queries, "split": split, "phase": phase,
            "fixture_hash": hashlib.sha256(raw).hexdigest(), "fixture_version": data.get("fixture_version"),
            "judgments": data.get("judgments"), "limitation": "AI 合成标注，不是人工业务有效性验证"}


def _translated(query, mapping):
    """服务创建的真实 ID 由回执映射，绝不强迫产品接受配方固定 MEM-ID。"""
    result = json.loads(json.dumps(query, ensure_ascii=False))
    for label in result.get("relevant", []):
        label["canonical_id"] = mapping.get(label["canonical_id"], label["canonical_id"])
    result["forbidden_as_formal"] = [mapping.get(cid, cid) for cid in result.get("forbidden_as_formal", [])]
    return result


def evaluate(queries, runner, *, id_mapping=None, phase="development", k=6, variant="memory", progress=None):
    """调用真实检索入口，保存逐查询结果/延迟/源版本，不启动外部模型。"""
    if not callable(runner):
        raise MemoryError("INVALID_ARGUMENT", "评价需要一个真实可调用检索入口")
    if any(query.get("split") != "development" for query in queries) and phase != "final":
        raise MemoryError("ACCESS_DENIED", "开发评价拒绝运行留出查询")
    rows = []
    for original in queries:
        query = _translated(original, id_mapping or {})
        request = {key: query[key] for key in ("query", "purpose", "scope", "owner_id") if key in query}
        request["limit"] = k
        started = time.perf_counter()
        result = runner(request)
        elapsed = time.perf_counter() - started
        candidates = result.get("candidates", result.get("results", []))
        metrics = ranking_metrics(query["relevant"], candidates, k=k)
        relevant_ids = {row["canonical_id"] for row in query["relevant"] if row["grade"] >= 1}
        loaded = [row for row in candidates[:k] if row["canonical_id"] in relevant_ids]
        # Required boundaries apply only when a relevant item was actually loaded.
        # Omitting the entire item hurts recall; it is not counted as truncating its
        # boundary. Inspect returned complete boundary fields, never hidden caches.
        visible = "\n".join(str(row.get("snippet", "")) + "\n" + json.dumps(row.get("boundaries", {}), ensure_ascii=False)
                            for row in loaded)
        if "context_text" in result:
            visible = result["context_text"]
        lost = [text for text in query.get("must_retain", []) if loaded and text not in visible]
        forbidden = sorted({row["canonical_id"] for row in candidates}.intersection(query.get("forbidden_as_formal", []))) if request.get("purpose") == "formal" else []
        rows.append({"query_id": query["query_id"], "split": query.get("split"), "category": query.get("category"),
            "request": request, "metrics": metrics, "boundary_checked": bool(loaded), "lost_boundaries": lost,
            "forbidden_formal_ids": forbidden, "latency_seconds": elapsed, "query_fingerprint": result.get("query_fingerprint"),
            "source_heads": result.get("source_heads", {}), "ranking": candidates, "degradation": result.get("degradation", []),
            "packet_manifest": result.get("packet_manifest"), "graph_paths": result.get("graph_paths"),
            "context_text": result.get("context_text")})
        if progress is not None:
            progress({"variant": variant, **rows[-1]})
    graded = [row for row in rows if row["metrics"]["recall"] is not None]
    boundary_rows = [row for row in rows if row["boundary_checked"]]
    count = len(graded)
    return {"variant": variant, "phase": phase, "created_at": utc_now(), "k": k, "query_count": len(rows),
        "recall": sum(row["metrics"]["recall"] for row in graded) / count if count else None,
        "ndcg": sum(row["metrics"]["ndcg"] for row in graded) / count if count else None,
        "duplicate_count": sum(row["metrics"]["duplicates"] for row in rows),
        "boundary_loss_rate": sum(bool(row["lost_boundaries"]) for row in boundary_rows) / len(boundary_rows) if boundary_rows else 0.0,
        "forbidden_formal_count": sum(len(row["forbidden_formal_ids"]) for row in rows),
        "queries": rows, "input_fingerprint": canonical_hash(queries),
        "limitation": "只评价本次真实检索输出；合成结果不能证明现实业务有效性"}


def compare_variants(queries, runners, *, id_mapping=None, phase="development", k=6, progress=None):
    """每个方案必须提供独立真实 runner，保留逐项结果，不静默填补缺方案。"""
    if not isinstance(runners, dict) or not runners:
        raise MemoryError("INVALID_ARGUMENT", "必须提供命名检索方案及真实入口")
    return {name: evaluate(queries, runner, id_mapping=id_mapping, phase=phase, k=k, variant=name, progress=progress)
            for name, runner in runners.items()}


def align_legacy_identity(root, result):
    """冻结规则：仅旧 Run 恰含一个既有 CLM 时作一对一身份对齐。

    不读取相关性标签，不生成/复制排名，不给多claim文档猜测映射。
    原始身份、Ref和排名保留在alignment，正文/边界/分数全部不改。
    """
    import evidence
    from copy import deepcopy
    graph = evidence.EvidenceGraph(Path(root))
    aligned = deepcopy(result)
    for row in aligned["candidates"]:
        oid = row["canonical_id"]
        node = graph.nodes.get(oid)
        if not node or not node["raw"].get("run_id"):
            continue
        children = [(cid, child) for cid, child in graph.nodes.items()
                    if child.get("kind") == "claim" and child.get("owner") == oid]
        row["alignment"] = {"raw_canonical_id": oid, "raw_source_ref": row.get("source_ref"),
            "rule": "sole-existing-claim-v1", "claim_count": len(children), "mapped": len(children) == 1}
        if len(children) != 1:
            continue
        cid, claim = children[0]
        row["canonical_id"] = cid
        row["source_ref"] = {"target_kind": "claim", "target_id": cid, "revision": None,
                             "sha256": claim["fingerprint"], "locator": "statement", "relation": "references"}
    aligned["identity_alignment_rule"] = "sole-existing-claim-v1"
    return aligned


def build_runners(root):
    """五个真实方案及一个基线身份对齐对照；固定差异不改标签。

    旧基线使用旧 docs/chunks/terms 的实际 BM25 排名与规范身份适配；
    单/多表示关键词移除真实通道，混合方案调用真实离线 384 维后端；
    完整方案额外执行公开关联扩展和材料包组装。不会用一个结果贴五标签。
    """
    from . import associations, packets, search
    from .service import MemoryService
    root = Path(root).resolve()
    service = MemoryService(root)

    def runner(profile, vector, complete=False, align_identity=False):
        def execute(request):
            req = {**request, "vector": vector}
            result = search.search(root, req, record=False, ranking_profile=profile)
            if align_identity:
                result = align_legacy_identity(root, result)
            if not complete:
                return result
            candidates = result["candidates"]
            seeds = [row["canonical_id"] for row in candidates]
            graph = associations.propose(service, {**req, "method": "explicit"})["candidates"]
            edges = [{**item["record"], "stale": item["stale"]} for item in graph]
            # Resolve each graph endpoint through the same live search boundary.
            # A neighbor need not match the original query words; limiting allowed
            # IDs to those initial hits would silently disable graph discovery.
            by_id = {row["canonical_id"]: row for row in candidates}
            endpoints = {ref["target_id"] for edge in edges for ref in (edge["payload"]["from"], edge["payload"]["to"])}
            for tid in sorted(endpoints - by_id.keys()):
                visible = search.search(root, {**req, "query": tid, "vector": "off", "limit": 100}, record=False)
                for row in visible["candidates"]:
                    if row["canonical_id"] == tid:
                        by_id[tid] = row
            allowed = set(by_id)
            neighbors = associations.expand_neighbors(seeds, edges, hops=1,
                allowed_ids=allowed, exclude_ids=request.get("exclude_ids", []))
            expanded = [*candidates, *[by_id[item["target_id"]] for item in neighbors if item["target_id"] in by_id]]
            refs = [row["source_ref"] for row in expanded]
            packet = packets.expand(service, refs, req)
            # Only material actually delivered in the bounded packet counts as a
            # full-scheme hit. Preserve the search score and record graph paths.
            visible_ids = [item["canonical_id"] for item in packet["manifest"]["items"]]
            ranked = {row["canonical_id"]: row for row in expanded}
            result["candidates"] = [ranked[cid] for cid in visible_ids if cid in ranked]
            result["context_text"] = packet["context_text"]
            result["packet_manifest"] = packet["manifest"]
            result["graph_paths"] = neighbors
            return result
        return execute
    return {"legacy_baseline": runner("legacy", "off"),
            "legacy_baseline_identity_aligned": runner("legacy", "off", align_identity=True),
            "single_representation_fts": runner("memory_single", "off"),
            "multi_representation_fts": runner("memory_multi", "off"),
            "multi_representation_hybrid_no_graph": runner("hybrid", "required"),
            "complete_graph_context": runner("hybrid", "required", True)}
