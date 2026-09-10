"""将本次说明修订经公开CLI保存，并固定回读；不改写历史规范文件。

仅用于本次文档维护Run。请求先预检再提交，保存原始输出；发现已有请求
即停止，避免重复执行产生无意义修订。每批使用实际HEAD和record_hash。
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
OWNER = "PRJ-ARCHITECTURE-EVOLUTION"
PYTHON = ROOT / "services/qdrant/runtime/python.exe"
CLI = ROOT / "automation/scripts/workspace_cli.py"
OLD = RUN.parent / "run-20260909t164914z-d20a9406384a"
os.environ["PYTHONUTF8"] = "1"

def write(name, value):
    path = RUN / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path

def call(name, args):
    done = subprocess.run([str(PYTHON), str(CLI), *args], cwd=ROOT, capture_output=True, encoding="utf-8")
    (RUN / (name + ".json")).write_text(done.stdout, encoding="utf-8")
    if done.returncode:
        (RUN / (name + ".stderr.txt")).write_text(done.stderr, encoding="utf-8")
        raise RuntimeError(done.stdout + done.stderr)
    return json.loads(done.stdout)

def fixed(record):
    return {"target_kind": "record", "target_id": record["record_id"], "revision": record["revision"],
            "sha256": record["record_hash"], "locator": "完整固定正文", "relation": "references"}

FIELDS = ("schema_version", "owner_id", "kind", "title", "body_markdown", "keywords", "payload",
          "sources", "provenance_gap", "record_reason", "discovery", "sensitivity", "level")

def update(record, **changes):
    draft = {key: deepcopy(record[key]) for key in FIELDS}
    draft.update(changes)
    draft["change_reason"] = "按用户反馈扩充术语定义、表示和索引维护及查询闭环；同步固定引用，保留旧版。"
    return {"op": "put_record", "record_id": record["record_id"], "expected_revision": record["revision"], "draft": draft}

def submit(name, state, operations):
    if (RUN / (name + "-request.json")).exists():
        raise RuntimeError("请求已存在，先核对回执再决定是否重试")
    path = write(name + "-request.json", {"schema_version": 3, "request_id": str(uuid.uuid4()),
        "actor": {"kind": "ai", "id": "assistant"}, "owner_id": OWNER,
        "expected_head": state["head"]["commit_id"], "operations": operations})
    call(name + "-validation", ["memory", "validate-draft", "--request", str(path)])
    receipt = call(name + "-receipt", ["memory", "commit", "--request", str(path)])
    current = call(name + "-inspect", ["memory", "inspect", OWNER])
    for operation in operations:
        if "record_id" in operation:
            rid = operation["record_id"]
        else:
            rid = next(row["record_id"] for row in receipt["record_results"] if row["client_key"] == operation["client_key"])
        for key, value in operation["draft"].items():
            assert current["records"][rid][key] == value, (rid, key)
    print(json.dumps({"batch": name, "save_status": receipt["save_status"], "index_status": receipt["index_status"],
                      "authored_fields_equal": True, "records": len(operations)}, ensure_ascii=False), flush=True)
    return current

def main():
    core = ROOT / "projects/architecture-evolution/design/interfaces-v0.1/CORE.md"
    snapshot = RUN / "CORE-expanded.md.snapshot"
    snapshot.write_bytes(core.read_bytes())
    feedback = RUN / "user-feedback.txt"
    feedback.write_text("用户反馈：CORE.md过于简略，术语不直观；要求扩充并改善表述，讲清调用链的输入输出和完整闭环，尤其要定义表示维护与索引维护。\n", encoding="utf-8")
    # 新来源使用新ID；旧来源仍指向先前固定文件，不把历史引用切到当前说明。
    registry = ROOT / "retrieval/sources.json"
    registered = json.loads(registry.read_text(encoding="utf-8"))
    sources = []
    for key, path in (("CORE", snapshot), ("FEEDBACK", feedback)):
        source_id = "SRC-ARCH-CORE-EXPLAIN-20260910-" + key
        assert not any(row["source_id"] == source_id for row in registered["sources"])
        registered["sources"].append({"source_id": source_id, "path": path.relative_to(ROOT).as_posix(),
                                      "enabled": True, "sensitivity": "internal", "context_role": "project"})
        sources.append({"target_kind": "file", "target_id": source_id, "revision": None,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "locator": "完整文件", "relation": "input"})
    registry.write_text(json.dumps(registered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write("fixed-sources.json", sources)
    state = call("before", ["memory", "inspect", OWNER])
    mapping = {}
    for name in ("layered", "sections", "documents"):
        mapping.update(json.loads((OLD / (name + "-fixed-records.json")).read_text(encoding="utf-8")))
    def record(key, current):
        return current["records"][mapping[key]["target_id"]]
    unit = record("U07", state)
    payload = deepcopy(unit["payload"])
    payload["blocks"][1]["markdown"] = core.read_text(encoding="utf-8")
    payload["evidence_refs"] = sources
    payload["retrieval_description"].update(question="材料怎样保存、准备不同形式、建立索引，并用于查询与持续修订？",
        method="用术语定义、假想例子、逐接口输入输出和保存/查询闭环说明原设计。",
        key_findings=["内容版本、材料表示和索引是不同职责；查询返回材料及缺口，新证据再进入保存和维护流程。"],
        limitations=["文档解释已扩充，接口和运行算法未改变；示例不代表实际实验，用户尚未复核新表述。"])
    event = {key: deepcopy(unit[key]) for key in FIELDS}
    event.update(kind="event", level="L2", title="根据可读性反馈扩充核心功能说明", body_markdown="用户指出术语与流程过于简略；本轮补充定义、存储维护输入输出、查询补查和使用后修订闭环。",
        sources=sources, record_reason="保留用户反馈和本次解释方式的选择，不新增实验结论。",
        payload={"occurred_at": None, "question_refs": [], "goal_ref": None, "route_ref": None,
            "action": "扩充CORE并同步受影响文稿", "observation": "原说明未充分定义表示与索引，用户难以理解；已提出具体扩写要求。",
            "decision": "先定义概念，再逐项说明维护接口和两条闭环；不增加新功能。", "decision_refs": sources,
            "run_refs": [], "failure": None, "claims": [], "missing_refs": []})
    state = submit("unit-event", state, [update(unit, title="核心功能说明：存储维护与查询闭环", payload=payload, sources=sources),
        {"op": "put_record", "client_key": "READABILITY-FEEDBACK", "draft": event}])
    new_unit = fixed(record("U07", state))
    old_unit_id = new_unit["target_id"]
    def replace_refs(refs):
        return [new_unit if ref["target_id"] == old_unit_id else ref for ref in refs]
    ops = []
    for key in ("P7", "B0", "B1"):
        chapter = record(key, state)
        payload = deepcopy(chapter["payload"])
        for block in payload["blocks"]:
            if block["type"] == "unit":
                if block["ref"]["target_id"] == old_unit_id:
                    block["ref"] = new_unit
            else:
                block["evidence_refs"] = replace_refs(block["evidence_refs"])
        if key == "P7":
            payload["title"] = "核心功能说明：定义、维护与完整闭环"
            payload["blocks"][0]["markdown"] = "本章集中解释容易混淆的概念，并说明保存、表示、索引、查询和修订怎样连接。示例为说明用途，运行接口仍待实施。"
        if key == "B0":
            payload["title"] = "核心概念、七项功能和完整闭环"
            payload["blocks"][0]["markdown"] = """材料表示，是为阅读或检索提供的一种内容形式，例如全文、局部正文、摘要或专题综合。索引则是帮助快速找到这些内容的辅助数据，例如关键词对应表和向量。L0–L4描述记录职责，与文字长短不同。

保存端分三步：②保存正文和来源的新版本；③检查需要的表示，缺失时按获准计划生成，新解释交②保存；④更新相应索引并记录完成进度。摘要保存成功但向量更新失败时，保留摘要，只补做索引。原文变化后，检查依赖的摘要、综合与文稿，旧版继续保留。

查询输入包括问题、材料范围、内容筛选、详细程度、用途与适用条件、允许的扩展方向和预算。⑧先检查③可用表示和④索引进度；⑤找候选，⑦按需要沿关系补充；⑫核验用途与证据，⑥去重排序；⑨通过①读取固定正文，补齐定义、条件、反例和引用。

若缺资料，⑧决定深入同一记录或扩大到允许的范围；各轮保留排除项、已读版本和已用预算。最后返回材料、来源版本、未解决问题和停止原因，由使用者或AI据此作答。排序分数不等于结论可信程度。

使用后发现新证据，再由②保存修订、⑫按需复核、⑪协调下游维护、③更新表示和④更新索引，形成闭环。完整技术说明保存在共享的核心说明单元；这里保留简报长度。"""
        ops.append(update(chapter, title=payload["title"], payload=payload, sources=replace_refs(chapter["sources"])))
    state = submit("chapters", state, ops)
    ops = []
    for key in ("PROCESS", "BRIEF"):
        document = record(key, state)
        payload = deepcopy(document["payload"])
        payload["common_refs"] = replace_refs(payload["common_refs"])
        def refreshed(refs):
            return [fixed(state["records"][ref["target_id"]]) for ref in refs]
        payload["section_refs"] = refreshed(payload["section_refs"])
        ops.append(update(document, payload=payload, sources=refreshed(document["sources"])))
    stage_map = record("MAP", state)
    payload = deepcopy(stage_map["payload"])
    payload["result_refs"] = replace_refs(payload["result_refs"])
    payload["coverage"]["source_versions"] = replace_refs(payload["coverage"]["source_versions"])
    ops.append(update(stage_map, payload=payload, sources=replace_refs(stage_map["sources"])))
    state = submit("documents-map", state, ops)
    checks = {}
    for key in ("PROCESS", "BRIEF"):
        doc = record(key, state)
        path = write(key.lower() + "-read-request.json", {"owner_id": OWNER, "document_id": doc["record_id"], "revision": doc["revision"]})
        result = call(key.lower() + "-read", ["memory", "document", "--request", str(path)])
        checks[key] = {"record_id": doc["record_id"], "revision": doc["revision"], "complete": result["report"]["complete"],
                       "missing": result["missing"], "coverage": result["report_coverage"]}
        # 明确读取上个固定版本，确认仍保持独立可用。
        old_path = write(key.lower() + "-old-request.json", {"owner_id": OWNER, "document_id": doc["record_id"], "revision": 1})
        old = call(key.lower() + "-old-read", ["memory", "document", "--request", str(old_path)])
        previous = json.loads((OLD / (key.lower() + "-document-result.json")).read_text(encoding="utf-8"))
        checks[key]["old_report_unchanged"] = old["report"] == previous["report"]
    checks["same_common_refs"] = record("PROCESS", state)["payload"]["common_refs"] == record("BRIEF", state)["payload"]["common_refs"]
    checks["new_unit_revision"] = record("U07", state)["revision"]
    checks["head"] = state["head"]
    checks["human_review"] = "pending"
    write("readback-checks.json", checks)
    print(json.dumps(checks, ensure_ascii=False))

if __name__ == "__main__":
    main()
