"""查询到实际应用结果的可追溯反馈；不把采用次数当作科学复核。"""
from copy import deepcopy
import json
import uuid

from . import owners, contracts
from .errors import MemoryError


def save(service, request):
    query_id = request.get("query_id", "")
    try:
        if not query_id.startswith("QMEM-"):
            raise ValueError("prefix")
        uuid.UUID(query_id[5:])
    except (ValueError, TypeError, AttributeError) as exc:
        raise MemoryError("INVALID_ARGUMENT", "反馈需要有效的记忆查询 ID") from exc
    path = owners.safe_path(service.root, "retrieval/queries/" + query_id + ".json")
    try:
        query = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MemoryError("NOT_FOUND", "原查询记录不存在或不可读") from exc
    if query.get("query_id") != query_id:
        raise MemoryError("INTEGRITY_ERROR", "查询记录身份不匹配")
    target = deepcopy(request["target"])
    # This can be a later-discovered missing result, not necessarily a previous
    # candidate. It must nevertheless be an existing authorized fixed version.
    resolved = service._resolve_ref(target, {}, [])
    adopted = deepcopy(request.get("adopted_in"))
    if request.get("label") == "outcome" and not adopted:
        raise MemoryError("INVALID_ARGUMENT", "实际应用结果需引用后续 Run 或事件")
    if adopted:
        application = service._resolve_ref(adopted, {}, [])
        if application.get("kind") != "event" and application.get("owner", {}).get("type") != "run":
            owner = application.get("owner", {})
            if not owner.get("native_data", {}).get("run_id"):
                raise MemoryError("INVALID_ARGUMENT", "采用结果必须指向实际 Run 或事件")
    refs = [target, *([adopted] if adopted else [])]
    draft = {"owner_id": request["owner_id"], "kind": "feedback", "title": request.get("title", "检索使用反馈"),
             "body_markdown": "", "keywords": [], "sources": refs, "provenance_gap": None,
             "record_reason": request.get("note") or "记录检索使用结果", "discovery": "owner_only",
             "sensitivity": request.get("sensitivity", resolved.get("sensitivity", "internal")),
             "payload": {"query_id": query_id, "target": target, "label": request["label"],
                         "note": request.get("note", ""), "adopted_in": adopted}}
    digest = contracts.canonical_hash({"operation": "feedback", "request": {
        k:v for k,v in request.items() if k not in {"request_id", "dry_run"}}})
    return service._commit({"schema_version": 1, "request_id": request["request_id"], "actor": request["actor"],
        "owner_id": request["owner_id"], "expected_head": request["expected_head"],
        "operations": [{"op": "put_record", "client_key": "feedback", "draft": draft}],
        "dry_run": request.get("dry_run", False)}, request_hash=digest)
