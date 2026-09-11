"""来源沿袭投影：固定来源身份去重不意味着独立科学支持。"""
from collections import deque
from . import contracts
from .evidence_adapter import EvidenceAdapter, iter_refs, legacy_ref
from .errors import MemoryError


def project(service, target_ids):
    """返回实际可访问原件的 source_count，保留摘要→来源方向和失败原因。

    同一已登记物理路径/版本的多个摘要或别名归并。不同路径即使字节相同
    也不擅自判断同源；该数值仅是来源身份数，不是独立实验/支持的数量。
    """
    if not isinstance(target_ids, list) or any(not isinstance(tid, str) for tid in target_ids):
        raise MemoryError("INVALID_ARGUMENT", "target_ids 必须为规范身份列表")
    adapter = EvidenceAdapter(service)
    queue = deque(({"target_id": tid}, [tid]) for tid in target_ids)
    seen, sources, missing = set(), {}, []
    while queue:
        pinned, path = queue.popleft()
        tid = pinned["target_id"]
        key = (tid, pinned.get("revision"), pinned.get("sha256"))
        if key in seen:
            continue
        seen.add(key)
        failures = adapter.access_errors(pinned)
        if failures:
            missing.extend({"target_id": tid, "code": error["code"], "path": path} for error in failures)
            continue
        record = adapter.access_record(tid, pinned.get("revision")) if tid in adapter.records else None
        refs = []
        if record:
            refs.extend(record["sources"])
            if record["kind"] == "source":
                refs.append(record["payload"]["source_ref"])
            elif record["kind"] in {"experience", "event", "narrative", "overview"}:
                for claim in record["payload"]["claims"]:
                    refs.extend(claim["evidence_refs"])
            elif record["kind"] == "association" and record["payload"]["relation"] == "derived_from":
                refs.append(record["payload"]["to"])
        elif tid in adapter.legacy.nodes:
            node = adapter.legacy.nodes[tid]
            if pinned.get("sha256") and pinned["sha256"] != node["fingerprint"]:
                missing.append({"target_id": tid, "code": "STALE_BASIS", "path": path})
                continue
            # A native Run is already one canonical analysis. Follow its
            # declared evidence dependencies and owned claims, rather than
            # demanding a duplicate MEM event or treating artifacts as new
            # independent scientific evidence. Access checks above still cover
            # native input/artifact permissions through the legacy adapter.
            for old_ref in adapter.legacy.refs(node):
                try:
                    refs.append(legacy_ref(service, adapter, old_ref))
                except MemoryError as exc:
                    missing.append({"target_id": old_ref.get("target") or old_ref.get("path"),
                                    "code": exc.code, "path": path})
            if node["kind"] == "owner":
                refs.extend({"target_kind": "claim", "target_id": cid, "revision": None,
                             "sha256": claim["fingerprint"], "locator": "", "relation": "references"}
                            for cid, claim in adapter.legacy.nodes.items() if claim.get("owner") == tid)
        elif tid in adapter.claims or pinned.get("target_kind") == "claim":
            for claim, record in adapter.access_claim_containers(tid, pinned.get("sha256")):
                refs.extend(claim["evidence_refs"])
                refs.extend(record["sources"])
        else:
            missing.append({"target_id": tid, "code": "UNRESOLVED_REFERENCE", "path": path})
        for ref in refs:
            try:
                # Record lineage follows the actual pinned revision even when
                # current scientific-use validation marks that version stale.
                # Files still require exact hashes and current registration.
                if ref["target_kind"] not in {"record", "claim"}:
                    service._resolve_ref(ref, {}, [])
                if ref["target_kind"] == "file":
                    actual, _registration = service._file(ref)
                    identity = contracts.canonical_hash({"path": str(actual), "sha256": ref["sha256"]})
                    source = sources.setdefault(identity, {"source_identity": identity, "source_ids": [],
                        "sha256": ref["sha256"], "paths": []})
                    if ref["target_id"] not in source["source_ids"]:
                        source["source_ids"].append(ref["target_id"])
                    source_path = [*path, ref["target_id"]]
                    if source_path not in source["paths"]:
                        source["paths"].append(source_path)
                elif ref["target_kind"] in {"record", "claim", "owner"}:
                    queue.append((ref, [*path, ref["target_id"]]))
            except MemoryError as exc:
                missing.append({"target_id": ref["target_id"], "code": exc.code, "path": path})
    return {"source_count": len(sources), "sources": [sources[key] for key in sorted(sources)],
            "missing": missing, "scientific_support_count": None,
            "meaning": "distinct accessible source identities; independence and scientific support are not inferred"}
