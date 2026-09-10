"""本地材料应用入口；单次搜索可显式组装当前页，不把进程内游标持久化。"""
import json
from pathlib import Path

from .api import dispatch
from .coordinator import Coordinator, failure
from .validation import QueryError, object_fields


def add_commands(parsers):
    parser = parsers.add_parser("material-query", help="材料查询、组包与语义维护；请求采用运行JSON契约")
    parser.add_argument("action", choices=("capabilities", "definitions", "foundation-capabilities", "foundation", "search", "structure", "maintenance-plan", "maintenance-review", "maintenance-apply", "maintenance-status"))
    parser.add_argument("--request", type=Path, help="UTF-8 JSON请求文件，最多500KB")
    parser.add_argument("--assemble", action="store_true", help="search后显式组装当前页全部候选；不会继续翻页")


def execute(root, args):
    coordinator = Coordinator(root)
    try:
        if args.assemble and args.action != "search":
            raise QueryError("VALIDATION", "--assemble仅用于search")
        if args.request:
            if args.request.stat().st_size > 500000:
                raise QueryError("VALIDATION", "请求文件超过500KB")
            raw = json.loads(args.request.read_text(encoding="utf-8-sig"))
        elif args.action in {"capabilities", "definitions", "foundation-capabilities"}:
            raw = {}
        else:
            raise QueryError("VALIDATION", "此动作需要--request文件")
        if args.action == "maintenance-status":
            # A read-only status call can establish a fresh authorized context
            # after process restart; it never resumes or reapplies the write.
            object_fields(raw, {"query", "plan_id"})
            search = coordinator.search(raw["query"])
            if not search.get("value"):
                return search, 2
            result = dispatch(coordinator, "maintenance-status", {"plan_id": raw["plan_id"], "query_id": search["value"]["query_id"]})
        elif args.action == "foundation":
            # One explicit query supplies the immutable scope and shared ledger.
            # Multi-step plans/commits need the persistent HTTP session; a later
            # CLI process cannot manufacture a new lifetime for an old query ID.
            object_fields(raw, {"query", "action", "request"})
            if not isinstance(raw["action"], str) or not isinstance(raw["request"], dict) or "query_id" in raw["request"]:
                raise QueryError("VALIDATION", "foundation需要动作及无query_id的请求对象")
            search = coordinator.search(raw["query"])
            if not search.get("value"):
                return search, 2
            result = dispatch(coordinator, "foundation/" + raw["action"],
                              {**raw["request"], "query_id": search["value"]["query_id"]})
        else:
            result = dispatch(coordinator, "foundation/capabilities" if args.action == "foundation-capabilities" else args.action, raw)
        if args.assemble and result.get("value") and result["value"].get("candidates"):
            receipt = result["value"]
            packet = coordinator.assemble({"query_id": receipt["query_id"], "expected_request_digest": receipt["request_digest"],
                                           "candidate_ids": [c["candidate_id"] for c in receipt["candidates"]]})
            return {"search": result, "assembly": packet}, 0 if packet["status"] == "ok" else 2
        return result, 0 if result.get("status", "ok") == "ok" else 2
    except (OSError, ValueError, QueryError) as exc:
        return failure(exc if isinstance(exc, QueryError) else QueryError("VALIDATION", "请求文件不可读或JSON格式错误")), 2
    finally:
        # The CLI process owns these identities. HTTP is the interactive entry
        # for poll/resume/deepen; a later CLI invocation cannot reset this ledger.
        coordinator.close()
