"""公开预检/提交/回读本次实现记录；只在最终验证报告存在后运行。

本脚本仅保存助手已撰写正文和实际 CLI 回执，不生成 AI 自评。每个请求写入后
使用同一 UUID 重试，已提交批次回读后继续；不会用新请求重复创建规范记录。
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sys
import uuid

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
OWNER = "PRJ-ARCHITECTURE-EVOLUTION"
sys.path.insert(0, str(ROOT / "automation/testing"))
import ai_review

FIELDS = ("schema_version", "owner_id", "kind", "title", "body_markdown", "keywords", "payload", "sources",
          "provenance_gap", "record_reason", "discovery", "sensitivity", "level")
DOCS = ("MEM-3264fce7-c63f-504e-bdb5-3aaa1169eb7b", "MEM-ef137680-afa6-59b8-a263-f2bb33d256c4")
MAP = "MEM-d17b92e3-e99d-563b-bec1-507552ac42ba"


def write_new(name, value):
    path = RUN / name
    ai_review.write_new(path, value)
    return path


def call(label, args, scenario="A01"):
    attempts = json.loads((RUN / "project-recording-attempts.json").read_text(encoding="utf-8"))
    request_file = args[args.index("--request") + 1] if "--request" in args else None
    folder, receipt = ai_review.capture_call(attempts[scenario], [sys.executable,
        str(ROOT / "automation/scripts/workspace_cli.py"), *args], request=request_file, cwd=ROOT, timeout=180)
    with (RUN / "project-recording-calls.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"label": label, "scenario": scenario, "call": str(folder), "exit_code": receipt["exit_code"]}, ensure_ascii=False) + "\n")
    if receipt["exit_code"]:
        raise RuntimeError("公开调用失败，请查看并保留回执：" + str(folder))
    return json.loads((folder / "stdout.txt").read_text(encoding="utf-8-sig"))


def fixed(record):
    return {"target_kind": "record", "target_id": record["record_id"], "revision": record["revision"],
            "sha256": record["record_hash"], "locator": "完整固定正文", "relation": "references"}


def put(record, **changes):
    draft = {key: deepcopy(record[key]) for key in FIELDS}
    draft.update(changes)
    draft["change_reason"] = "接入本轮实际实现与固定验证证据；历史设计章节及历史修订保留。"
    return {"op": "put_record", "record_id": record["record_id"], "expected_revision": record["revision"], "draft": draft}


def submit(name, state, operations, scenario="A01"):
    path = RUN / (name + "-request.json")
    if not path.exists():
        write_new(path.name, {"schema_version": 3, "request_id": str(uuid.uuid4()), "actor": {"kind": "ai", "id": "assistant"},
            "owner_id": OWNER, "expected_head": state["head"]["commit_id"], "operations": operations})
        call(name + "-validate", ["memory", "validate-draft", "--request", str(path)], scenario)
    # A replay uses exactly the stored request, including UUID and old CAS.
    receipt = call(name + "-commit", ["memory", "commit", "--request", str(path)], scenario)
    current = call(name + "-inspect", ["memory", "inspect", OWNER], scenario)
    request = json.loads(path.read_text(encoding="utf-8"))
    mapping = {}
    for op in request["operations"]:
        rid = op.get("record_id") or next(r["record_id"] for r in receipt["record_results"] if r.get("client_key") == op["client_key"])
        row = current["records"][rid]
        for key, value in op["draft"].items():
            if row[key] != value:
                raise AssertionError((rid, key, "公开回读与已提交正文不一致"))
        mapping[op.get("client_key", rid)] = fixed(row)
    saved = RUN / (name + "-fixed.json")
    if not saved.exists():
        write_new(saved.name, mapping)
    print(json.dumps({"batch": name, "save_status": receipt["save_status"], "index_status": receipt["index_status"],
                      "records": len(mapping), "fields_match": True}, ensure_ascii=False), flush=True)
    return current, mapping


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if not (RUN / "FINAL_VALIDATION.md").exists():
        raise RuntimeError("先完成实际验证汇总，再固定本轮来源")
    if (RUN / "implementation-recording-checks.json").exists():
        raise RuntimeError("本轮规范记录已完成；如需新修订请建立新请求而非覆盖回执")
    names = ("IMPLEMENTATION_CONTENT.md", "EVIDENCE_MAINTENANCE_CONTENT.md", "WORKBENCH_VALIDATION_CONTENT.md", "FINAL_VALIDATION.md")
    registry_path = ROOT / "retrieval/sources.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    sources = []
    for number, name in enumerate(names, 1):
        path = RUN / name
        sid = "SRC-ARCH-IMPLEMENTATION-20260910-" + str(number)
        registered = next((r for r in registry["sources"] if r["source_id"] == sid), None)
        entry = {"source_id": sid, "path": path.relative_to(ROOT).as_posix(), "enabled": True, "sensitivity": "internal", "context_role": "project"}
        if registered is not None and registered != entry:
            raise RuntimeError("来源ID冲突，不覆盖已有登记")
        if registered is None:
            registry["sources"].append(entry)
        sources.append({"target_kind": "file", "target_id": sid, "revision": None,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "locator": "完整固定报告", "relation": "input"})
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = call("implementation-before", ["memory", "inspect", OWNER])
    template = next(r for r in state["records"].values() if r["kind"] == "detail")
    titles = ("表示查询运行实现：契约、范围和累计资源", "局部证据、关系加深与语义维护", "工作台接入、验证和Windows升级")
    operations = []
    for i, title in enumerate(titles):
        draft = {key: deepcopy(template[key]) for key in FIELDS}
        draft.update(title=title, keywords=["表示查询v0.2", "实际实现", "固定引用", "累计预算", "软件验证"], sources=[sources[i], sources[-1]],
            record_reason="将实际实现保存为可独立阅读的技术单元；测试及未完成边界引用固定Run。", body_markdown="")
        draft["payload"] = {"unit_type": "analysis", "retrieval_description": {"question": title + "如何工作？",
            "method": "实现与反例回归、公开CLI回读及实际AI/浏览器检查分别记录。",
            "key_findings": [title + "已接通运行入口，详细支持范围和实际验证结果见正文及固定验证报告。"],
            "applicable": ["本次工作区实现及已执行合成案例"], "not_applicable": ["未执行策略、科学模型有效性、真实企业数据外推"],
            "limitations": ["人工、第二物理机和大规模验收单列；历史夹具失败不篡改为通过。"]},
            "run_ref": None, "evidence_refs": [sources[i], sources[-1]],
            "blocks": [{"block_id": "scope", "role": "definitions", "markdown": "本单元记录本次软件实现。变量与单位在正文定义；功能回归、实际AI自查、人工/科学复核分别报告。", "requires_block_ids": []},
                       {"block_id": "implementation", "role": "methods", "markdown": (RUN / names[i]).read_text(encoding="utf-8"), "requires_block_ids": ["scope"]},
                       {"block_id": "validation", "role": "results", "markdown": (RUN / names[-1]).read_text(encoding="utf-8"), "requires_block_ids": ["scope"]}],
            "figures": [], "missing_refs": []}
        operations.append({"op": "put_record", "client_key": "IMPL-U" + str(i+1), "draft": draft})
    state, units = submit("implementation-units-v2", state, operations, "A03")
    base = {key: deepcopy(template[key]) for key in FIELDS}
    unit_refs = list(units.values())
    event = {**deepcopy(base), "kind": "event", "level": "L2", "title": "正式实施表示查询并修复继承审计发现", "sources": unit_refs, "body_markdown": "",
        "payload": {"occurred_at": None, "question_refs": [], "goal_ref": None, "route_ref": None,
            "action": "实施P0-P6并按真实旧契约逐项审计，保存修复和实际验证", "observation": "方法映射存在仍可能丢失范围、表示命中、降级或局部读取语义；实际界面发现partial被错误阻断。",
            "decision": "按具体反例补实现和回归；保留旧记录、失败尝试及独立人工验收状态。", "decision_refs": unit_refs, "run_refs": [], "failure": None, "claims": [], "missing_refs": []}}
    experience = {**deepcopy(base), "kind": "experience", "level": "L3", "title": "接口继承必须按可观察语义验证", "sources": unit_refs, "body_markdown": "",
        "payload": {"problem_structure": "新增应用可保留旧方法名，却在范围、候选归并、正式准入或部分失败时丢失旧义务。",
            "applicable": ["本工作区接口迁移、检索编排及状态化维护开发"], "prohibited": ["不能用接口数量或单元测试推断科学质量和任意策略可用"],
            "failure_modes": ["只测同候选去重而未测多表示", "partial返回有效值但UI阻断", "两个陈旧索引水位相等被当作当前完整"],
            "recommendation": "保留旧断言并映射到真实输入、实际读取和输出；分别审查代码、运行结果、AI使用与人工验收。",
            "retry_conditions": ["接口、范围、提供器、索引和部署规则变化后重跑受影响反例"], "claim_refs": [], "claims": [], "missing_refs": []}}
    state, events = submit("implementation-event-experience", state, [{"op": "put_record", "client_key": "IMPL-EVENT", "draft": event},
        {"op": "put_record", "client_key": "IMPL-EXPERIENCE", "draft": experience}])
    section_template = next(r for r in state["records"].values() if r["kind"] == "document_section")
    operations = []
    for i, title in enumerate(titles):
        draft = {key: deepcopy(section_template[key]) for key in FIELDS}
        draft.update(title=title, sources=[unit_refs[i]], payload={"section_key": "implementation-" + str(i+1), "title": title, "role": "discussion",
            "blocks": [{"type": "prose", "markdown": "本章记录实际实现；前面的设计章节保留为历史时点。", "evidence_refs": [unit_refs[i]]},
                {"type": "unit", "ref": unit_refs[i], "block_ids": ["implementation", "validation"]}], "watch_refs": [], "missing_refs": []})
        operations.append({"op": "put_record", "client_key": "IMPL-P" + str(i+1), "draft": draft})
    brief = {key: deepcopy(section_template[key]) for key in FIELDS}
    brief.update(title="本轮实际实现与验证", sources=unit_refs, payload={"section_key": "implementation-current", "title": "本轮实际实现与验证", "role": "conclusion",
        "blocks": [{"type": "prose", "markdown": "表示查询现已接通原始、全文、章节、单元概览、专题和领域六类表示。用户选择问题与范围，检查可用性后显式组包；缺少的表示只有获准才回退。输出范围是可信授权、硬上限和当前选择的交集，再减显式排除；必需依赖读取也受硬上限约束。固定修订、SHA256和块定位贯穿读取。\n\n查询、续页、加深和组包共用累计资源账本，小结果集逐批核验正文，通道故障保留已完成结果及缺口。正式支持按单个claim的当前依据和适用域判断，不将同篇其他文字借用为已获准结论。已有关系用于导航，采纳联想不产生科学认可。\n\n语义维护先交付实际材料，AI或人阅读并逐项审查草案，再由原CAS事务保存；request_id重试不重复提交，索引失败单独补偿。浏览器已修复有效partial被错误阻断。使用入口为工作台“材料查询”和workbench.cmd material-query；开发与升级方式见材料查询手册。\n\n下面引用与完整过程稿相同的三个固定技术单元，保留验证边界。旧设计简报保留在后续章节，其“尚未实现”描述属于当时状态。", "evidence_refs": unit_refs},
            *[{"type": "unit", "ref": ref, "block_ids": ["scope"]} for ref in unit_refs],
            {"type": "prose", "markdown": (RUN / "FINAL_VALIDATION.md").read_text(encoding="utf-8"), "evidence_refs": unit_refs}], "watch_refs": [], "missing_refs": []})
    operations.append({"op": "put_record", "client_key": "IMPL-BRIEF", "draft": brief})
    state, sections = submit("implementation-sections", state, operations, "A04")
    operations = []
    for i, rid in enumerate(DOCS):
        old = state["records"][rid]
        payload = deepcopy(old["payload"])
        payload.update(scope="本项目接口v0.1历史设计与v0.2本轮实际实现；验证范围和限制见当前实现章节。", purpose="阅读实际实现、固定验证及保留的设计过程")
        payload["common_refs"] += unit_refs
        new_sections = [sections["IMPL-P" + str(n)] for n in range(1, 4)] if i == 0 else [sections["IMPL-BRIEF"]]
        payload["section_refs"] = payload["section_refs"] + new_sections if i == 0 else new_sections + payload["section_refs"]
        operations.append(put(old, payload=payload, sources=payload["section_refs"], title="表示查询：" + ("完整设计与实施过程" if i == 0 else "当前实现与核心简报")))
    stage = state["records"][MAP]
    payload = deepcopy(stage["payload"])
    payload["topic"] = "表示查询从设计到实际实现的阶段地图"
    payload["result_refs"] += [*unit_refs, *events.values()]
    payload["coverage"]["source_versions"] += unit_refs
    payload["coverage"]["missing"] = ["人工和第二台物理机验收待完成", "万条规模实验按既有授权暂缓", "具体软件失败及未支持策略见本轮固定验证报告"]
    payload["next_steps"] = ["按本轮固定回执开展人工验收", "在新需求触发时再评估未注册策略，保留旧义务与当前限制", "规则或实现变更后复核本轮软件经验适用域"]
    operations.append(put(stage, title=payload["topic"], payload=payload, sources=payload["result_refs"]))
    state, final_refs = submit("implementation-documents-map", state, operations, "A04")
    checks = {"same_common_refs": state["records"][DOCS[0]]["payload"]["common_refs"] == state["records"][DOCS[1]]["payload"]["common_refs"]}
    for rid in DOCS:
        row = state["records"][rid]
        path = write_new(rid + "-document-request.json", {"owner_id": OWNER, "document_id": rid, "revision": row["revision"]})
        result = call(rid + "-document", ["memory", "document", "--request", str(path)], "A04")
        checks[rid] = {"ref": fixed(row), "complete": result["report"]["complete"], "missing": result["missing"], "coverage": result["report_coverage"]}
        old_path = write_new(rid + "-historical-request.json", {"owner_id": OWNER, "document_id": rid, "revision": 4})
        old = call(rid + "-historical-document", ["memory", "document", "--request", str(old_path)], "A04")
        checks[rid]["old_revision_4_readable"] = old["report"]["complete"]
    checks.update(head=state["head"], units=units, sections=sections, final_refs=final_refs, human_review="pending", scientific_review="not-reviewed")
    write_new("implementation-recording-checks.json", checks)
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == "__main__":
    main()
