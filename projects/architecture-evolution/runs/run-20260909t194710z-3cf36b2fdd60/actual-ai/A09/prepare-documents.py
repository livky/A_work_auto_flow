"""Explicitly author a two-document r1 baseline from the already-read old basis.

F3 originally had no document pair. These are newly created synthetic baseline
documents, not recovered historical work. Their text flags that the new input
has not yet been incorporated; they support a subsequent actual update check.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture as c


def fixed(record):
    return {"target_kind": "record", "target_id": record["record_id"], "revision": record["revision"],
        "sha256": record["record_hash"], "locator": "", "relation": "references"}


def save_record(label, draft, previous=None):
    owner = draft["owner_id"]
    head = c.call(label + "-before", "inspect", domain="memory", inspect_args=[owner])["head"]
    operation = {"op": "put_record", "draft": draft}
    if previous:
        operation.update(record_id=previous["record_id"], expected_revision=previous["revision"])
    else:
        operation["client_key"] = label
    request = {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": {"kind": "ai", "id": c.ACTOR},
        "owner_id": owner, "expected_head": head["commit_id"], "operations": [operation]}
    valid = c.call(label + "-validate", "validate-draft", request, domain="memory")
    if valid.get("error"):
        raise ValueError(valid)
    result = c.call(label + "-commit", "commit", request, domain="memory")
    if result.get("save_status") != "committed":
        raise ValueError(result)
    row = result["record_results"][0]
    return c.call(label + "-inspect", "inspect", domain="memory", inspect_args=[owner, "--record-id", row["record_id"], "--revision", str(row["revision"])])["record"]


def draft(kind, title, payload, refs):
    return {"schema_version": 3, "owner_id": "RES-F3-TANK", "kind": kind, "title": title,
        "body_markdown": "", "keywords": ["SYNTHETIC", "F3", "水箱"], "payload": payload, "sources": deepcopy(refs),
        "provenance_gap": None, "record_reason": "A09显式创建旧r1依据的合成文稿基线；不是恢复真实历史",
        "discovery": "workspace_summary", "sensitivity": "internal"}


def document_payload(kind, section, refs):
    return {"document_type": kind, "purpose": "SYNTHETIC F3固定双文稿维护检查", "audience": "合成检查执行者",
        "scope": "旧r1依据基线；新饱和输入尚未融合，不据此认可新参数下的结论",
        "common_refs": deepcopy(refs), "section_refs": [deepcopy(section)], "watch_refs": [], "missing_refs": []}


def main():
    basis = [c.F3["legacy_refs"][name] for name in ("tank_definitions", "tank_model")]
    process = save_record("baseline-process", draft("document", "SYNTHETIC F3 水箱完整过程（旧依据基线）",
        document_payload("research_process", c.F3["legacy_refs"]["tank_section"], basis), basis))
    brief_section = save_record("baseline-brief-section", draft("document_section", "SYNTHETIC F3 水箱结论与边界（旧依据基线）", {
        "section_key": "brief", "title": "水箱结论与边界（旧依据基线）", "role": "conclusion",
        "blocks": [{"type": "prose", "markdown": "旧r1依据仅说明：在给定连续、无延迟且全过程未饱和的合成模型中，液位误差指数衰减。该结论不能推广到饱和泵或现实系统；尚需检查目标所需流量与泵容量。新输入尚未融合到这份显式基线，本文不确认新参数下可达。", "evidence_refs": basis}],
        "watch_refs": [], "missing_refs": []}, basis))
    brief = save_record("baseline-report", draft("document", "SYNTHETIC F3 水箱精简报告（旧依据基线）",
        document_payload("research_report", fixed(brief_section), basis), basis))
    records = {"process": process, "brief_section": brief_section, "report": brief}
    c.write(c.attempt() / "baseline-documents.json", records)
    for key in ("process", "report"):
        record = records[key]
        c.call("baseline-" + key + "-read", "document", {"owner_id": "RES-F3-TANK", "document_id": record["record_id"], "revision": 1}, domain="memory")
    c.call("baseline-documents-reconcile", "reconcile", {"owner_id": "RES-F3-TANK", "vector": "off"}, domain="memory")
    scope = c.queries.request("saturation", "full")["scope"]
    scope.update(owner_ids=["RES-F3-TANK", "RES-F3-SATURATION"], kinds=["detail"], include_refs=[])
    value = c.call("maintenance-plan", "maintenance-plan", {"changed_refs": [c.F3["refs"]["saturation"]],
        "scope": scope, "strategy": "dependency-review", "strategy_version": "1"})
    if not value.get("value"):
        raise ValueError(value)
    plan = value["value"]
    body = ["# A09 维护任务包实际交付", "", "这是返回内容的投影；不代表AI已经完成阅读。", "",
        "```json", json.dumps({key: plan[key] for key in ("plan_id", "plan_digest", "items", "reviewed_refs", "unchecked_regions", "semantic_reviewer", "read_receipt")}, ensure_ascii=False, indent=2), "```", ""]
    for part in plan["context_items"]:
        body += ["## " + part["heading"], "", part["markdown"], "", "固定交付：`" + json.dumps(part["refs"], ensure_ascii=False) + "`", ""]
    c.write(c.attempt() / "delivered/maintenance-plan.md", "\n".join(body))
    print(json.dumps({"documents": {key: fixed(record) for key, record in records.items()},
        "plan_id": plan["plan_id"], "plan_digest": plan["plan_digest"], "items": plan["items"],
        "delivered_parts": len(plan["context_items"]), "unchecked_regions": plan["unchecked_regions"],
        "reviewed_refs": plan["reviewed_refs"], "delivered_path": str(c.attempt() / "delivered/maintenance-plan.md")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
