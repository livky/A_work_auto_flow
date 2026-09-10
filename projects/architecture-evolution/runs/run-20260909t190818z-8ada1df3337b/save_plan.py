"""本轮设计存档：经公开 memory CLI 修订正文/文稿，保留旧版本。

复用上一轮已使用的预检、提交、回读辅助函数；只更换本轮输出目录。
本脚本是固定Run辅助产物，不是产品功能。重复执行由请求存在检查拒绝。
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
previous = RUN.parent / "run-20260909t184202z-6e13d341b986/update_design.py"
spec = importlib.util.spec_from_file_location("previous_plan_helpers", previous)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
h.RUN = RUN


def main():
    if (RUN / "planning-unit-request.json").exists():
        raise RuntimeError("本轮请求已存在，先核对回执")
    design = ROOT / "docs/design/representation-query-v0.2"
    parts = []
    for path in sorted(design.iterdir()):
        if path.is_file():
            (RUN / (path.name + ".snapshot")).write_bytes(path.read_bytes())
            if path.suffix == ".md":
                parts.append(path.read_text(encoding="utf-8"))
    body = "\n\n".join(parts)
    snapshot = RUN / "implementation-design.txt"
    snapshot.write_text(body, encoding="utf-8")
    source_id = "SRC-ARCH-IMPLEMENTATION-PLAN-20260910"
    registry = ROOT / "retrieval/sources.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    assert not any(row["source_id"] == source_id for row in data["sources"])
    data["sources"].append({"source_id": source_id, "path": snapshot.relative_to(ROOT).as_posix(),
                            "enabled": True, "sensitivity": "internal", "context_role": "project"})
    registry.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sources = [{"target_kind": "file", "target_id": source_id, "revision": None,
                "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(), "locator": "完整设计", "relation": "input"}]
    h.write("fixed-sources.json", sources)
    state = h.call("before", ["memory", "inspect", h.OWNER])
    mapping = {}
    for name in ("layered", "sections", "documents"):
        mapping.update(json.loads((h.OLD / (name + "-fixed-records.json")).read_text(encoding="utf-8")))
    def record(key):
        return state["records"][mapping[key]["target_id"]]
    def update(record, **changes):
        op = h.update(record, **changes)
        op["draft"]["change_reason"] = "将表示提案落实为v0.2接口、工作台、Skill和实施/测试设计；产品实现待后续阶段。"
        return op
    unit = record("U07")
    payload = deepcopy(unit["payload"])
    payload["blocks"][1]["markdown"] = body
    payload["evidence_refs"] = sources
    payload["retrieval_description"].update(question="怎样实现表示查询、工作台、联想加深与AI语义维护？",
        method="明确v0.2契约和14个方法、工作台交互、3个Skill、P0-P6实施及70项测试设计。",
        key_findings=["本轮完成实施准备，类型与状态可检查；运行功能、产品测试和质量验收尚未开展。"],
        limitations=["只有设计静态验证；全部产品用例designed_not_run；Skill安装登记留P6。"])
    event = {key: deepcopy(unit[key]) for key in h.FIELDS}
    event.update(kind="event", level="L2", title="首期实现准备与后续策略预留", body_markdown="用户明确本轮只完成接口、UI、Skill、开发与完整测试计划。",
        sources=sources, record_reason="固定规划边界和首期技术取舍，不能冒充运行功能已完成。",
        payload={"occurred_at": None, "question_refs": [], "goal_ref": None, "route_ref": None,
                 "action": "形成v0.2设计和根待开发计划", "observation": "表示类型与实例、用户查询链路和AI语义动作需要可实施约束。",
                 "decision": "首期复用存储索引、模板组包和有界图；更复杂联想/加深策略留抽象和待办。",
                 "decision_refs": sources, "run_refs": [], "failure": None, "claims": [], "missing_refs": []})
    state = h.submit("planning-unit", state, [update(unit, title="表示查询与AI维护的实施设计", payload=payload, sources=sources),
                     {"op": "put_record", "client_key": "IMPLEMENTATION-PLAN", "draft": event}])
    ref = h.fixed(record("U07"))
    def replace(refs):
        return [ref if item["target_id"] == ref["target_id"] else item for item in refs]
    ops = []
    summary = "v0.2实施设计已完成：六种表示类型与实际内容分离；工作台采用存储结构、查询候选、材料预览三栏；14个应用端口覆盖选择组包、联想加深与语义维护。三个专项Skill使用现有公开动作，P6再接安装发现。P0-P6和70项用例已设计，复杂策略的选择原因与触发条件记入根待开发计划。当前只通过设计检查，产品功能、浏览器、升级及检索质量均未因本轮而验证。"
    for key in ("P7", "B0", "B1"):
        chapter = record(key)
        payload = deepcopy(chapter["payload"])
        payload["blocks"][0]["markdown"] = summary
        for block in payload["blocks"]:
            if block["type"] == "unit" and block["ref"]["target_id"] == ref["target_id"]:
                block["ref"] = ref
            elif "evidence_refs" in block:
                block["evidence_refs"] = replace(block["evidence_refs"])
        ops.append(update(chapter, payload=payload, sources=replace(chapter["sources"])))
    state = h.submit("planning-chapters", state, ops)
    ops = []
    for key in ("PROCESS", "BRIEF"):
        doc = record(key)
        payload = deepcopy(doc["payload"])
        payload["common_refs"] = replace(payload["common_refs"])
        payload["section_refs"] = [h.fixed(state["records"][item["target_id"]]) for item in payload["section_refs"]]
        ops.append(update(doc, payload=payload, sources=[h.fixed(state["records"][item["target_id"]]) for item in doc["sources"]]))
    item = record("MAP")
    payload = deepcopy(item["payload"])
    payload["result_refs"] = replace(payload["result_refs"])
    payload["coverage"]["source_versions"] = replace(payload["coverage"]["source_versions"])
    payload["next_steps"] = ["按v0.2开发计划P0开始旧接口适配并冻结实际测试选择", "P1-P6逐步接入工作台、联想、维护与升级验收", "按根待开发计划的触发条件评估复杂策略"]
    ops.append(update(item, payload=payload, sources=replace(item["sources"])))
    state = h.submit("planning-documents", state, ops)
    checks = {}
    for key in ("PROCESS", "BRIEF"):
        doc = record(key)
        request = h.write(key.lower()+"-read-request.json", {"owner_id": h.OWNER, "document_id": doc["record_id"], "revision": doc["revision"]})
        result = h.call(key.lower()+"-read", ["memory", "document", "--request", str(request)])
        checks[key] = {"revision": doc["revision"], "complete": result["report"]["complete"], "missing": result["missing"]}
    checks["head"] = state["head"]
    checks["human_review"] = "pending"
    h.write("readback-checks.json", checks)
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == "__main__":
    main()
