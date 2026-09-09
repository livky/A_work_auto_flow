"""Derived impact views, separated from scientific review state mutations."""
from collections import defaultdict, deque

from .evidence_adapter import EvidenceAdapter, DEPENDENT, iter_refs, issue
from .errors import MemoryError


def _adapter(root, service=None):
    if service is None:
        from .service import MemoryService
        service = MemoryService(root)
    return EvidenceAdapter(service)


def _readable(adapter, target, cache):
    """Keep identity-only graphs inside the same visibility boundary as text.

    Missing evidence remains useful as an explicit gap; revoked authorization
    does not authorize exposing the hidden record's ID through an impact path.
    """
    if target not in cache:
        cache[target] = not any(error["code"] in {"ACCESS_DENIED", "UNSAFE_PATH"}
                                for error in adapter.access_errors(target))
    return cache[target]


def _visible_heads(adapter, cache):
    return {oid: head for oid, head in adapter.source_heads.items() if _readable(adapter, oid, cache)}


def reverse_dependencies(root, changed_ids, *, service=None):
    """Return update candidates and support-only propagation paths separately.

    A background/contradiction/analogy edge can warrant updating a summary, but
    it never becomes an automatic scientific retraction, even if another edge
    later in that navigation path happens to be supports/input.
    """
    adapter = _adapter(root, service)
    if not isinstance(changed_ids, list) or any(not isinstance(target, str) or not target for target in changed_ids):
        raise MemoryError("INVALID_ARGUMENT", "changed_ids must contain canonical identities")
    visibility = {}
    if any(not _readable(adapter, target, visibility) for target in changed_ids):
        raise MemoryError("ACCESS_DENIED", "Selected impact source is outside the current readable scope")
    reverse = defaultdict(list)
    for rid, record in adapter.records.items():
        if not _readable(adapter, rid, visibility):
            continue
        payload = {key: value for key, value in record["payload"].items() if key != "claims"}
        for ref in iter_refs({"sources": record["sources"], "payload": payload}):
            reverse[ref["target_id"]].append((rid, ref["relation"]))
        for claim in record["payload"].get("claims", []):
            for ref in claim["evidence_refs"]:
                reverse[ref["target_id"]].append((claim["claim_id"], ref["relation"]))
            # A record's content change invalidates its embedded claim binding.
            reverse[rid].append((claim["claim_id"], "input"))
            # A claim review change updates its container's display, but does
            # not scientifically invalidate unrelated sibling claims.
            reverse[claim["claim_id"]].append((rid, "references"))
    for target, dependencies in adapter.legacy.edges.items():
        if not _readable(adapter, target, visibility):
            continue
        for dependency in dependencies:
            if _readable(adapter, dependency, visibility):
                reverse[dependency].append((target, "input"))
    queue = deque((target, True, [target]) for target in changed_ids)
    visited, results = set(), {}
    while queue:
        target, formal, path = queue.popleft()
        if (target, formal) in visited:
            continue
        visited.add((target, formal))
        for dependent, relation in sorted(reverse[target]):
            if not _readable(adapter, dependent, visibility):
                continue
            propagated = formal and relation in DEPENDENT
            if dependent in path:
                continue
            next_path = path + [dependent]
            result = results.setdefault(dependent, {"canonical_id": dependent, "needs_revalidation": True,
                                                    "formal_dependency": False, "paths": []})
            result["formal_dependency"] |= propagated
            if next_path not in result["paths"]:
                result["paths"].append(next_path)
            queue.append((dependent, propagated, next_path))
    return {"changed_ids": list(changed_ids), "affected": [results[key] for key in sorted(results)],
            "source_heads": _visible_heads(adapter, visibility), "writes": 0}


def question_resolution_validity(root, question_ref, *, service=None, scope=None):
    """Recheck a saved answer while retaining the historical resolved state."""
    adapter = _adapter(root, service)
    target = question_ref if isinstance(question_ref, str) else question_ref.get("target_id")
    record = adapter.records.get(target)
    if not record or record["kind"] != "question":
        raise MemoryError("NOT_FOUND", "Question record does not exist")
    visibility = {}
    if not _readable(adapter, target, visibility):
        raise MemoryError("ACCESS_DENIED", "Selected question is outside the current readable scope")
    errors = []
    if isinstance(question_ref, dict):
        try:
            adapter._reference(question_ref)
        except MemoryError as exc:
            errors.append(issue(exc.code, target, str(exc)))
    state = record["payload"]["status"]
    if state == "resolved":
        refs = record["payload"]["resolution_refs"]
        if not refs:
            errors.append(issue("UNRESOLVED_REFERENCE", target, "Resolved question has no answer references"))
        for ref in refs:
            try:
                answer = adapter._reference(ref)
                failures = adapter._analyze(answer, scope, allow_decision=True) if answer else []
                for failure in failures:
                    errors.append(dict(failure, path=failure["path"] + [target]))
            except MemoryError as exc:
                errors.append(issue(exc.code, ref["target_id"], str(exc), [ref["target_id"], target]))
    return {"record_id": target, "revision": record["revision"], "status": state,
            "resolution_needs_revalidation": state == "resolved" and bool(errors), "errors": errors,
            "source_heads": _visible_heads(adapter, visibility), "writes": 0}
