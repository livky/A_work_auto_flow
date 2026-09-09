"""变化驱动的阶段巩固：程序固定材料清单，AI逐项解释处置，人类另行复核。"""
from copy import deepcopy
import hashlib

from . import contracts, owners, impact
from .associations import record_ref, keyword_candidates
from .evidence_adapter import iter_refs
from .errors import MemoryError


def _at_commit(service, owner, snapshot, commit_id):
    """只沿当前 HEAD 可达的校验链读历史，拒绝孤立或任意路径提交。"""
    if commit_id in (None, "none"):
        return {}
    manifest = snapshot["manifest"]
    visited = set()
    while manifest:
        if manifest["commit_id"] in visited:
            raise MemoryError("INTEGRITY_ERROR", "提交历史出现循环")
        visited.add(manifest["commit_id"])
        if manifest["commit_id"] == commit_id:
            return {rid: service.store._record(owner, rid, entry) for rid, entry in manifest["record_heads"].items()}
        parent = manifest["parent_commit_id"]
        manifest = service.store._manifest(owner, parent, manifest["parent_manifest_hash"]) if parent else None
    raise MemoryError("STALE_BASIS", "巩固起点不属于当前可达历史", {"owner_id": owner["owner_id"]})


def _key(ref):
    return ref["target_kind"], ref["target_id"]


def _source_states(service, refs):
    """固定外部依据的当前状态参与草案指纹；仅通过来源登记读取。"""
    result = {}
    for ref in refs:
        key = contracts.canonical_hash(ref)
        if key in result:
            continue
        state = {"ref": deepcopy(ref), "sha256": None, "error": None}
        try:
            if ref["target_kind"] == "file":
                path, _metadata = service._file(ref)
                state["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif ref['target_kind'] == 'owner':
                descriptor = owners.resolve_owner(service.root, ref['target_id'])
                if descriptor['native_data'].get('sensitivity') == 'restricted':
                    raise MemoryError('ACCESS_DENIED', '归属来源不允许当前AI读取')
                import evidence
                node = evidence.EvidenceGraph(service.root).nodes.get(ref['target_id'])
                state['sha256'] = node['fingerprint'] if node else descriptor['fingerprint']
            elif ref['target_kind'] == 'claim':
                resolved = impact._adapter(service.root, service).resolve_claim(ref['target_id'])
                if resolved.get('sensitivity') == 'restricted':
                    raise MemoryError('ACCESS_DENIED', '结论来源不允许当前AI读取')
                state['sha256'] = resolved['sha256']
            else:
                resolved = service._resolve_ref(ref, {}, [])
                state["sha256"] = resolved.get("sha256")
        except MemoryError as exc:
            state["error"] = exc.code
        result[key] = state
    return result


def _basis_hash(basis):
    """HEAD覆盖规范写入，source_states覆盖未写入HEAD的外部字节变化。"""
    return contracts.canonical_hash({k: basis.get(k, {}) for k in
        ("owner_id", "basis_heads", "changed", "affected", "remaining", "source_states")})


def prepare(service, owner_id, since_commit=None, trigger="manual"):
    owner = owners.resolve_owner(service.root, owner_id)
    snapshot = service.store.read_snapshot(owner)
    consolidations = [r for r in snapshot["records"].values() if r["kind"] == "consolidation"]
    latest = max(consolidations, key=lambda r: (r["updated_at"], r["record_id"]), default=None)
    old_heads = deepcopy(latest["payload"]["basis_heads"]) if latest else {}
    if latest:
        # Own revisions written alongside the last consolidation are already
        # handled. The saved basis remains the prepublish evidence snapshot;
        # this owner's next scan starts at that consolidation's actual commit.
        old_heads[owner_id] = snapshot["manifest"]["record_heads"][latest["record_id"]]["commit_id"]
    if since_commit:
        old_heads[owner_id] = since_commit
    # Only this object's records and their explicit transitive dependencies form
    # the change basis. Unrelated owners never become affected by proximity.
    selected = {owner_id: (owner, snapshot)}
    queue = list(snapshot["records"].values())
    seen, external_refs, unresolved = set(), [], []
    while queue:
        record = queue.pop()
        if record["record_id"] in seen:
            continue
        seen.add(record["record_id"])
        if record["kind"] in {"consolidation", "feedback", "review"}:
            continue
        for ref in iter_refs({"sources": record["sources"], "payload": record["payload"]}):
            if ref["target_kind"] != "record":
                external_refs.append(ref)
                if ref["target_kind"] == "claim":
                    try:
                        claim = service._resolve_ref(ref, {}, [])
                        if claim.get("record"):
                            queue.append(claim["record"])
                            dependency = owners.resolve_owner(service.root, claim["owner_id"])
                            selected.setdefault(claim["owner_id"], (dependency, service.store.read_snapshot(dependency)))
                    except MemoryError as exc:
                        unresolved.append({"target_id": ref["target_id"], "code": exc.code})
                continue
            value = service._resolve_ref(ref, {}, [])
            if value["owner_id"] not in selected:
                dependency = owners.resolve_owner(service.root, value["owner_id"])
                selected[value["owner_id"]] = (dependency, service.store.read_snapshot(dependency))
            queue.append(value)
    basis_heads, changed, current = {}, [], {}
    for oid, (descriptor, state) in sorted(selected.items()):
        basis_heads[oid] = state["head"]["commit_id"] if state["head"] else "none"
        previous = _at_commit(service, descriptor, state, old_heads.get(oid))
        current.update(state["records"])
        for rid, record in state["records"].items():
            if record["kind"] == "review" and (rid not in previous or previous[rid]["content_hash"] != record["content_hash"]):
                # 复核本身是变化，不改写原结果；按结论身份传播到其容器和
                # 下游地图/经验，使跨对象依赖进入只读待处理清单。
                changed.append({"target_kind": "claim", "target_id": record["payload"]["target_claim_id"],
                                "revision": None, "sha256": record["payload"]["target_content_hash"],
                                "locator": "复核变化", "relation": "references"})
            if record["kind"] in {"consolidation", "feedback", "review", "policy"}:
                continue
            if oid != owner_id and rid not in seen:
                continue
            if rid not in previous or previous[rid]["content_hash"] != record["content_hash"]:
                changed.append(record_ref(record))
    source_states = _source_states(service, external_refs)
    for state in source_states.values():
        ref = state["ref"]
        if state["error"] or state["sha256"] != ref.get("sha256"):
            # 可访问的新文件版本可成为固定巩固依据；原记录仍保留旧指纹。
            # 不可访问项只给出状态，并以原身份计算受影响对象。
            changed.append({**ref, "sha256": state["sha256"] or ref.get("sha256")})
    changed = list({contracts.canonical_hash(ref): ref for ref in changed}.values())
    dependencies = impact.reverse_dependencies(service.root, [r["target_id"] for r in changed], service=service)
    affected = []
    # Impact is read-only across objects. Actual writes remain single-owner;
    # foreign affected records stay on the next owner's work list.
    all_records = {r["record_id"]: r for r in impact._adapter(service.root, service).records.values()}
    for value in dependencies["affected"]:
        record = all_records.get(value["canonical_id"])
        if record and record["kind"] not in {"review", "consolidation", "feedback"} and record["sensitivity"] != "restricted":
            affected.append(record_ref(record))
            descriptor = owners.resolve_owner(service.root, record["owner_id"])
            head = service.store.read_snapshot(descriptor)["head"]
            basis_heads[record["owner_id"]] = head["commit_id"] if head else "none"
    remaining = deepcopy(latest["payload"]["remaining_refs"]) if latest else []
    candidates = []
    rows = [r for r in snapshot["records"].values() if r["kind"] in {"experience", "event"}]
    for position, a in enumerate(rows):
        for b in rows[position+1:]:
            overlap = keyword_candidates(a["keywords"], b["keywords"])
            a_sources = {(_key(r), r.get("revision"), r.get("sha256")) for r in a["sources"]}
            b_sources = {(_key(r), r.get("revision"), r.get("sha256")) for r in b["sources"]}
            if overlap["eligible"] and a_sources and a_sources == b_sources:
                candidates.append({"kind": "merge_candidate", "refs": [record_ref(a), record_ref(b)], "reason": "共有关键词且来源身份相同，仍需比较边界"})
            related_ids = {a["record_id"], b["record_id"]}
            related_ids.update(c["claim_id"] for record in (a, b) for c in record["payload"].get("claims", []))
            common_sources = {_key(r) for r in a["sources"]} & {_key(r) for r in b["sources"]}
            contradictory = [r for r in [*a["sources"], *b["sources"]] if r["relation"] == "contradicts"
                             and (r["target_id"] in related_ids or _key(r) in common_sources)]
            if contradictory:
                candidates.append({"kind": "conflict_candidate", "refs": [record_ref(a), record_ref(b)], "basis_refs": contradictory,
                                   "reason": "存在显式反证关系，需复核范围；不自动撤回"})
    result = {"owner_id": owner_id, "trigger": trigger, "since_commit": since_commit, "basis_heads": basis_heads,
              "changed": changed, "affected": affected, "remaining": remaining,
              "candidates": candidates, "source_states": source_states, "missing": unresolved, "writes": 0}
    if _source_states(service, external_refs) != source_states:
        raise MemoryError("STALE_BASIS", "巩固准备期间外部来源变化")
    service._basis_checks(basis_heads)
    result["basis_hash"] = _basis_hash(result)
    return result


def apply(service, request):
    """每个处置保留理由和固定目标；未处置项与 defer 一同留待下次。"""
    basis = request["basis"]
    basis_hash = _basis_hash(basis)
    if basis_hash != basis.get("basis_hash") or basis["owner_id"] != request["owner_id"]:
        raise MemoryError("STALE_BASIS", "巩固材料清单指纹不一致")
    states = basis.get("source_states", {})
    if _source_states(service, [state["ref"] for state in states.values()]) != states:
        raise MemoryError("STALE_BASIS", "巩固准备后的外部来源已变化", {"source_ids": [state["ref"]["target_id"] for state in states.values()]})
    decisions = deepcopy(request["decisions"])
    targets = {_key(ref): ref for ref in [*basis["changed"], *basis["affected"], *basis["remaining"]]}
    handled, decision_keys = set(), set()
    for decision in decisions:
        errors = contracts.validate_schema(decision, contracts.SCHEMA["$defs"]["ConsolidationDecision"], contracts.SCHEMA["$defs"])
        if errors:
            raise MemoryError("INVALID_SCHEMA", "巩固处置不符合契约", errors=errors)
        key = _key(decision["target"])
        if key not in targets or key in decision_keys:
            raise MemoryError("INVALID_ARGUMENT", "巩固目标不在材料包中或重复处置")
        original = targets[key]
        expected_revision = original.get('revision')
        if decision['action'] == 'revise':
            if original['target_kind'] != 'record' or type(expected_revision) is not int:
                raise MemoryError('INVALID_ARGUMENT', '只有规范记录可在当前归属执行revise')
            expected_revision += 1
        if (decision['target'].get('revision') != expected_revision or
                decision['target'].get('sha256') != original.get('sha256')):
            raise MemoryError('STALE_BASIS', '巩固处置未绑定清单中的固定版本')
        decision_keys.add(key)
        if decision["action"] != "defer":
            handled.add(key)
    remaining = [ref for key, ref in targets.items() if key not in handled]
    operations = deepcopy(request.get("operations", []))
    for decision in decisions:
        if decision["action"] == "revise":
            # A revise decision must cite the newly committed version and have
            # its actual revision operation in the same atomic owner batch.
            matches = [op for op in operations if op.get("record_id") == decision["target"]["target_id"]]
            if not matches or decision["target"].get("revision") != matches[0].get("expected_revision", 0)+1:
                raise MemoryError("INVALID_ARGUMENT", "revise 必须绑定本批实际新修订")
    # 将已获准外部来源直接纳入提交来源，交给统一服务在发布HEAD前再次
    # 核对字节指纹，避免prepare/apply检查之后发生变化仍提交成功。
    sources = list(targets.values()) + [{**state['ref'], 'sha256': state['sha256']}
        for state in states.values() if not state['error'] and state['sha256']]
    sources = list({contracts.canonical_hash(ref): ref for ref in sources}.values())
    draft = {"owner_id": request["owner_id"], "kind": "consolidation", "title": request.get("title", "阶段巩固"),
             "body_markdown": "", "keywords": [], "sources": sources,
             "provenance_gap": None if sources else "当前没有待巩固来源",
             "record_reason": request["reason"], "change_reason": request["reason"],
             "sensitivity": request.get("sensitivity", "internal"), "discovery": "owner_only",
             "payload": {"basis_heads": basis["basis_heads"], "trigger": basis["trigger"],
                         "affected_refs": list(targets.values()), "decisions": decisions, "remaining_refs": remaining}}
    owner = owners.resolve_owner(service.root, request["owner_id"])
    snapshot = service.store.read_snapshot(owner)
    normalized = contracts.validate_record(draft)
    if not normalized["valid"]:
        raise MemoryError("INVALID_SCHEMA", "巩固记录不符合契约", errors=normalized["errors"])
    digest = contracts.content_hash(normalized["record"])
    previous = next((r for r in snapshot["records"].values() if r["kind"] == "consolidation" and r["content_hash"] == digest), None)
    repeat = previous is not None
    if repeat:
        expected = {**basis["basis_heads"], request["owner_id"]:
                    snapshot["manifest"]["record_heads"][previous["record_id"]]["commit_id"]}
        service._basis_checks(expected)
        # Repeating the exact decisions may acknowledge the same work without
        # creating another consolidation or recursing the map body. A changed
        # revised record invalidates this optimization.
        for op in operations:
            old = snapshot["records"].get(op.get("record_id"))
            parsed = contracts.validate_record(op["draft"])
            if not old or not parsed["valid"] or contracts.content_hash(parsed["record"]) != old["content_hash"]:
                repeat = False
                break
    operation = {"op": "put_record", "draft": draft}
    if repeat:
        operation.update(record_id=previous["record_id"], expected_revision=previous["revision"])
        for op in operations:
            op["expected_revision"] = snapshot["records"][op["record_id"]]["revision"]
    else:
        operation["client_key"] = "consolidation"
        service._basis_checks(basis["basis_heads"])
        actual = prepare(service, request["owner_id"], basis.get("since_commit"), basis["trigger"])
        if actual["basis_hash"] != basis_hash:
            raise MemoryError("STALE_BASIS", "巩固清单与当前可重建的材料包不同")
    semantic_hash = contracts.canonical_hash({"operation": "consolidation", "request": {
        k:v for k,v in request.items() if k not in {"request_id", "dry_run"}}})
    return service._commit({"schema_version": 1, "request_id": request["request_id"], "actor": request["actor"],
        "owner_id": request["owner_id"], "expected_head": (snapshot["head"]["commit_id"] if snapshot["head"] else None) if repeat else request["expected_head"],
        "operations": [*operations, operation], "dry_run": request.get("dry_run", False)},
        request_hash=semantic_hash, basis_heads={} if repeat else basis["basis_heads"])
