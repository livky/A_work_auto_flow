"""将表示组合、联想与维护提案经公开CLI保存，并固定回读；不改写历史规范文件。

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
    draft["change_reason"] = "根据本轮问题澄清类型、实例和查询组合，保存联想、AI维护与图设计提案；新字段尚待下一版契约。"
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
    detail = RUN / "REPRESENTATION_AND_GRAPH.md.snapshot"
    detail.write_bytes((core.parent / "REPRESENTATION_AND_GRAPH.md").read_bytes())
    feedback = RUN / "user-feedback.txt"
    feedback.write_text("用户要求明确各表示如何组合L0-L4与过程稿/简报；提出经验联想；质疑类型为何绑定具体分析；讨论AI主导维护和非AI方法；询问深层回源、联想及关系图结构和更新用途。\n", encoding="utf-8")
    # 新来源使用新ID；旧来源仍指向先前固定文件，不把历史引用切到当前说明。
    registry = ROOT / "retrieval/sources.json"
    registered = json.loads(registry.read_text(encoding="utf-8"))
    sources = []
    for key, path in (("CORE", snapshot), ("DETAIL", detail), ("FEEDBACK", feedback)):
        source_id = "SRC-ARCH-REP-GRAPH-20260910-" + key
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
    payload["blocks"][1]["markdown"] = core.read_text(encoding="utf-8") + "\n\n" + detail.read_text(encoding="utf-8")
    payload["evidence_refs"] = sources
    payload["retrieval_description"].update(question="表示类型怎样组合现有内容，经验联想、AI维护和关系图怎样协作？",
        method="区分类型/实例/查询组合，给出分层来源配方、联想补充通道、AI与确定性维护分工，以及图字段和更新触发。",
        key_findings=["用户按类型、问题与范围查询；G03维护具体实例；经验联想横跨表示，语义由AI/人审阅，版本和索引由工具维护。"],
        limitations=["新类型注册、组合清单、联想策略和部分图字段是下一版提案，尚未纳入当前Python契约；无实际质量实验或用户验收。"])
    event = {key: deepcopy(unit[key]) for key in FIELDS}
    event.update(kind="event", level="L2", title="澄清表示组合与联想、AI和图维护分工", body_markdown="用户进一步询问表示来源组合、类型与实例、经验联想、AI更新审核及关系图维护；本轮形成细化提案。",
        sources=sources, record_reason="保留用户反馈和本次解释方式的选择，不新增实验结论。",
        payload={"occurred_at": None, "question_refs": [], "goal_ref": None, "route_ref": None,
            "action": "细化CORE和专项提案并同步受影响文稿", "observation": "原说明把用户类型查询与G03实例维护混淆；联想、语义维护和图生命周期需要细化。",
            "decision": "采用类型＋问题＋范围查询，已有字段优先组合；联想独立补充，AI审核语义，工具执行版本/索引；扩展字段待下一版。", "decision_refs": sources,
            "run_refs": [], "failure": None, "claims": [], "missing_refs": []})
    state = submit("unit-event", state, [update(unit, title="核心功能说明：存储维护与查询闭环", payload=payload, sources=sources),
        {"op": "put_record", "client_key": "REPRESENTATION-GRAPH-FEEDBACK", "draft": event}])
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
            payload["blocks"][0]["markdown"] = "本章澄清表示类型、具体内容和查询组合，并保留联想、AI分工与关系图维护的完整细化提案；新增字段尚待下一版契约。"
        if key == "B0":
            payload["title"] = "核心概念、七项功能和完整闭环"
            payload["blocks"][0]["markdown"] = """表示类型规定怎样组织材料；具体实例是某版本下已有或可组合的内容；查询材料包针对问题选出多个实例。用户入口是“类型＋问题/关键词＋范围”，G03的指定来源检查只用于实例维护，下一版需补类型注册接口。

默认组合：原始证据取L0；完整/局部说明取L1或完整过程稿章节并补定义；单元概览复用L1检索说明或L3结构字段；专题概览优先L4与简报并补L3/L2；领域综合组合多个专题并保留差异。能用模板组成的概览，不因没有单独摘要文件而报缺失。

经验联想作为所有表示可启用的独立补充通道。通过问题结构、机制、约束和干预检索候选，列出共同点、差异、固定来源和验证建议；继承范围与排除，受单独篇幅/数量及总预算限制。未采用候选不全部永久加边。

AI或人审阅含义、连贯性和新综合，提出保留/局部修订/重建/延期计划；工具负责引用、版本、依赖、索引和恢复。无需每次全量AI重写，AI审核也不证明科学正确。无生成式AI时可以用结构字段模板维护，开放语义由人处理或留缺口。

加深查询包括段落到单元/块/原件的精确回源、已有关系遍历、新结构类比检索。关系图区分定位、依赖、证据、经验和专题组织；先用正反向邻接表即可。内容提交或关系采用后更新投影，来源变化检查下游，索引失败补做。依赖图不覆盖所有新信息，还需检查专题新增材料。

本轮是细化设计提案；新增类型定义、组合清单、联想选项和部分图字段尚未进入v0.1 Python契约。现有算法、类型数量和既有验收边界没有因此改变。"""
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
    payload["next_steps"] = ["将定义注册、表示组合、联想策略及图字段提案收敛并写入下一版契约", *payload["next_steps"]]
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
        old_path = write(key.lower() + "-old-request.json", {"owner_id": OWNER, "document_id": doc["record_id"], "revision": 2})
        old = call(key.lower() + "-old-read", ["memory", "document", "--request", str(old_path)])
        previous = json.loads((RUN.parent / "run-20260909t175530z-40721b975bdb" / (key.lower() + "-read.json")).read_text(encoding="utf-8"))
        checks[key]["old_report_unchanged"] = old["report"] == previous["report"]
    checks["same_common_refs"] = record("PROCESS", state)["payload"]["common_refs"] == record("BRIEF", state)["payload"]["common_refs"]
    checks["new_unit_revision"] = record("U07", state)["revision"]
    checks["head"] = state["head"]
    checks["human_review"] = "pending"
    write("readback-checks.json", checks)
    print(json.dumps(checks, ensure_ascii=False))

if __name__ == "__main__":
    main()
