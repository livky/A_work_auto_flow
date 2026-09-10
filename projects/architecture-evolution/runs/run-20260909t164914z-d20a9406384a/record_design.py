"""保存本次 AI 编写的设计；只通过公开 CLI 写入，回执逐次保留。

此脚本是固定 Run 的执行材料，不是通用产品功能。正文来自已固定设计，
分层摘要由本次任务编写；不会生成评测答案或把结构校验当成科学复核。
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import uuid

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
OWNER = "PRJ-ARCHITECTURE-EVOLUTION"
os.environ["PYTHONUTF8"] = "1"
PYTHON = ROOT / "services/qdrant/runtime/python.exe"
CLI = ROOT / "automation/scripts/workspace_cli.py"
spec = importlib.util.spec_from_file_location("actual_ai", ROOT / "automation/testing/ai_review.py")
ai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)
FILES = {row["key"]: row for row in json.loads((RUN / "fixed-sources.json").read_text(encoding="utf-8"))["files"]}

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def source(key):
    row = FILES[key]
    data = (ROOT / row["path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != row["sha256"]:
        raise ValueError("固定来源已变更：" + key)
    return data.decode("utf-8-sig")

def refs(*keys):
    return [FILES[key]["ref"] for key in keys]

def draft(kind, title, payload, sources, level=None, body=""):
    return {"schema_version": 3, "owner_id": OWNER, "kind": kind, "title": title,
            "body_markdown": body, "keywords": ["接口契约", "表示索引", "检索编排", "Project分层记录"],
            "payload": payload, "sources": sources, "provenance_gap": None,
            "record_reason": "按本轮明确要求保存完整设计、选择理由及实际验证边界，供后续实施和固定回读。",
            "discovery": "workspace_summary", "sensitivity": "internal", "level": level}

def call(attempt, args, request=None):
    directory, receipt = ai.capture_call(attempt, [str(PYTHON), str(CLI), "memory", *args],
                                        request=request, cwd=ROOT, timeout=180)
    output = (directory / "stdout.txt").read_text(encoding="utf-8-sig")
    if receipt["exit_code"] != 0:
        print(output)
        print((directory / "stderr.txt").read_text(encoding="utf-8-sig"))
        raise RuntimeError("公开调用失败，证据保留：" + str(directory))
    return json.loads(output), directory

def submit(attempt, name, operations, head):
    path = RUN / (name + "-request.json")
    if path.exists():
        raise ValueError("请求已存在；先检查既有回执，不能静默重复提交")
    write(path, {"schema_version": 3, "request_id": str(uuid.uuid4()), "actor": {"kind": "ai", "id": "assistant"},
                 "owner_id": OWNER, "expected_head": head, "operations": operations})
    validation, _ = call(attempt, ["validate-draft", "--request", str(path)], path)
    write(RUN / (name + "-validation.json"), validation)
    result, _ = call(attempt, ["commit", "--request", str(path)], path)
    write(RUN / (name + "-receipt.json"), result)
    return result

def put(key, value):
    return {"op": "put_record", "client_key": key, "draft": value}

def stage_one():
    attempt = next((RUN / "actual-ai/A01").glob("attempt-*"))
    spec_text = source("SPEC.md")
    sections = re.split(r"(?=^## \d+\.)", spec_text, flags=re.M)
    def part(start, end):
        return "\n".join(sections[start:end+1])
    functions = source("FUNCTIONS.md")
    # 按目录实际 G 编号截取，避免只存概括而遗失具体输入、输出和异常。
    groups = re.split(r"(?=^## )", functions, flags=re.M)
    def methods(ids):
        return "\n".join(s for s in groups if any(i in s.splitlines()[0] for i in ids))
    units = [
        ("U00", "设计方向与原始讨论依据", "为什么选择十二组边界？", "本次日期回顾原讨论，保留原文及来源清单。",
         "本轮整理的历史讨论，不表示重新运行文献检索；最终编号以本轮契约为准。\n\n" + source("prior-discussion"), ["prior-discussion", "prior-sources"]),
        ("U01", "来源、知识属性与公共数据契约", "如何表达输入范围、知识属性和共同约束？", "拆分固定引用、属性、当前证据评估与范围，并定义有类型字段。",
         part(1,2) + "\n\n## 全部数据类型定义\n```python\n" + source("contract_types.py") + "\n```", ["SPEC.md", "contract_types.py"]),
        ("U02", "表示与索引生命周期接口", "表示和索引如何独立维护且保持来源一致？", "分别管理版本内容、派生表示、增量水位与补偿。",
         part(3,4) + "\n" + methods(["G03", "G04"]), ["SPEC.md", "FUNCTIONS.md"]),
        ("U03", "召回、排序与关系导航接口", "如何召回、融合、排序并利用关系？", "用统一候选边界连接可替换策略，正式准入在截断之前。",
         part(5,7) + "\n" + methods(["G05", "G06", "G07"]), ["SPEC.md", "FUNCTIONS.md"]),
        ("U04", "渐进编排与上下文组装接口", "如何逐步扩展且保留定义、范围和预算？", "扩大语料与深入表示分别规划，共享预算和不透明续接状态。",
         part(8,9) + "\n" + methods(["G08", "G09", "X01"]), ["SPEC.md", "FUNCTIONS.md"]),
        ("U05", "存储、视图、维护与证据边界", "其余接口如何调用并管理状态？", "固定单一状态所有者，区分内容提交、索引补偿和复核。",
         part(10,12) + "\n" + methods(["G01", "G02", "G10", "G11", "G12"]) + "\n## 完整端口签名\n```python\n" + source("contract_ports.py") + "\n```", ["SPEC.md", "FUNCTIONS.md", "contract_ports.py"]),
        ("U06", "实现落点、默认策略与真实验证", "后续怎么实现、哪些结果已被验证？", "固定代码映射、首期顺序、验收条件及实际失败/缺项。",
         source("IMPLEMENTATION.md") + "\n\n" + source("project-policy-review.md"), ["IMPLEMENTATION.md", "project-policy-review.md", "contract-checks.json"]),
        ("U07", "核心接口与Project记录简版", "用户怎样快速把握核心功能？", "用七个重点功能与一次查询调用链压缩表述。",
         source("CORE.md"), ["CORE.md", "user-steering.md"]),
    ]
    ops = []
    for key, title, question, method, body, keys in units:
        payload = {"unit_type": "analysis", "retrieval_description": {"question": question, "method": method,
                   "key_findings": [title + "已形成接口设计；除Project默认策略外，运行适配待实施。"],
                   "applicable": ["当前AI研发工作区接口演进与本项目后续实施"],
                   "not_applicable": ["不能当作召回质量或生产性能的实测结论"],
                   "limitations": ["设计尚待运行适配与人工审查；测试结果边界见实现与验证单元。"]},
                   "run_ref": None, "evidence_refs": refs(*keys),
                   "blocks": [{"block_id": "scope", "role": "definitions", "markdown": "本单元保存设计与实际观察。接口定义不等于已运行接入；用户认可方向不等于科学复核。", "requires_block_ids": []},
                              {"block_id": "technical-body", "role": "methods", "markdown": body, "requires_block_ids": ["scope"]}],
                   "figures": [], "missing_refs": []}
        ops.append(put(key, draft("detail", title, payload, refs(*keys), "L1")))
    observations = [
        ("E01", "采用Project默认研究分层记录规则", "用户认可十二组方向，要求细化接口，并让全部Project默认按Research标准记录。",
         "采用explore/fine、保留L0–L4和总结建议；保留显式覆盖。实质工作保存完整技术单元和阶段文稿。", ["user-steering.md", "project-policy-review.md"], None),
        ("E02", "保留回归缺项并限定验证结论", "quick实际运行136项Python：135通过、1项既有冻结夹具失败；19项前端因开发依赖缺失未运行。真实setup扩展旧工作区测试通过。",
         "不重写冻结夹具指纹，也不将未运行算通过；接口结构检查和迁移通过不能替代生产算法或第二台机器验收。", ["project-policy-review.md", "contract-checks.json"],
         {"category": "execution", "tested_scope": "本次quick选择及既有冻结夹具自检", "result": "1项冻结文件哈希自检失败；诊断确认相关文件与HEAD一致，非本次改动造成。", "cannot_infer": "不能据此推断新默认策略错误，也不能宣称全部回归通过。", "retry_conditions": ["独立审查既有冻结夹具来源，明确处理方案后重新验证。"]}),
    ]
    for key, title, observation, decision, keys, failure in observations:
        payload = {"occurred_at": None, "question_refs": [], "goal_ref": None, "route_ref": None,
                   "action": title, "observation": observation, "decision": decision, "decision_refs": refs(*keys),
                   "run_refs": [], "failure": failure, "claims": [], "missing_refs": []}
        ops.append(put(key, draft("event", title, payload, refs(*keys), "L2", observation + "\n\n" + decision)))
    payload = {"problem_structure": "项目已有Run和设计文件，但程序默认basic，单纯登记产物不能保证完整技术正文可按分层入口复用。",
               "recommendation": "同步默认策略、可读规则和真实分层保存；同时保留来源版本、正文、事件及验证限制。",
               "applicable": ["本工作区Project分层记录缺口与类似默认策略检查"],
               "prohibited": ["不能推断其他系统自动形成经验；不能把保存成功当作科学结论复核"],
               "failure_modes": ["只登记文件链接而缺少L1技术正文", "默认策略与README规则不一致"],
               "retry_conditions": ["规则、接口或对象策略变更后重查默认值及实际回读"], "claim_refs": [], "claims": [], "missing_refs": []}
    ops.append(put("X01", draft("experience", "默认规则与真实技术正文保存需要同时闭合", payload, refs("project-policy-review.md", "user-steering.md"), "L3")))
    result = submit(attempt, "layered-v2", ops, None)
    print(json.dumps(result, ensure_ascii=False))

def read_saved(attempt, receipt_name, label):
    state, directory = call(attempt, ["inspect", OWNER])
    write(RUN / (label + "-inspect.json"), state)
    receipt = json.loads((RUN / (receipt_name + "-receipt.json")).read_text(encoding="utf-8"))
    request = json.loads((RUN / (receipt_name + "-request.json")).read_text(encoding="utf-8"))
    expected = {op["client_key"]: op["draft"] for op in request["operations"]}
    fixed = {}
    for row in receipt["record_results"]:
        record = state["records"][row["record_id"]]
        original = expected[row["client_key"]]
        # 比较所有作者字段；服务生成的 ID/时间/哈希不参与正文相等断言。
        for field, value in original.items():
            if record[field] != value:
                raise ValueError("回读不一致：" + row["client_key"] + "/" + field)
        fixed[row["client_key"]] = {"target_kind": "record", "target_id": record["record_id"],
                "revision": record["revision"], "sha256": record["record_hash"], "locator": "完整固定正文", "relation": "references"}
    write(RUN / (label + "-fixed-records.json"), fixed)
    print(json.dumps({"inspection": str(directory), "equal_authored_fields": len(fixed), "head": state["head"]}, ensure_ascii=False))
    return state, fixed

def stage_two():
    parent = next((RUN / "actual-ai/A01").glob("attempt-*"))
    state, fixed = read_saved(parent, "layered-v2", "layered")
    attempt = ai.initialize(RUN / "actual-ai", "A03", RUN / "user-steering.md", "assistant", None,
                            "continuous", str(parent), RUN / "ai-input-environment.json")
    units = [fixed[f"U{i:02d}"] for i in range(8)]
    missing = ["接口运行适配和检索性能实验未执行", "1项既有冻结夹具失败、19项前端未运行", "第二台物理机与人工验收待完成"]
    payload = {"topic": "接口契约v0.1与Project分层记录阶段地图", "goal_refs": [], "route_refs": [],
        "result_refs": list(fixed.values()), "question_refs": [], "conflict_refs": [],
        "next_steps": ["按IMPLEMENTATION先实现G01固定读取、范围和一致性映射", "接入表示与索引水位，再接召回/排序/关系/编排/上下文", "按各阶段真实验收回写结果和限制"],
        "coverage": {"owner_ids": [OWNER], "source_versions": units, "missing": missing}, "missing_refs": []}
    ops = [put("MAP", draft("map", payload["topic"], payload, list(fixed.values()), "L4", "完整设计与简版共用固定技术单元；已完成默认规则修改，检索接口运行适配待实施。"))]
    transitions = ["先保留讨论问题与依据，区分旧讨论行序和最终契约编号。", "明确输入概念与共同约束，是所有后续接口的前提。",
        "在共同契约上分别定义表示和索引的生命周期。", "用统一候选结果串联召回、排序和关系导航。",
        "进一步限定渐进扩展和上下文组装的职责。", "补齐持久化、视图、整理和证据端口，明确状态归属。",
        "最后把设计映射到现有代码，并完整披露已运行验证及缺项。", "以核心功能简版收束本阶段，并明确后续实施入口。"]
    for i, ref in enumerate(units):
        title = state["records"][ref["target_id"]]["title"]
        payload = {"section_key": f"process-{i}", "title": title, "role": "introduction" if i == 0 else "discussion" if i == 6 else "conclusion" if i == 7 else "methods",
            "blocks": [{"type": "prose", "markdown": transitions[i], "evidence_refs": [ref]},
                       {"type": "unit", "ref": ref, "block_ids": ["technical-body"]}], "watch_refs": [], "missing_refs": []}
        ops.append(put(f"P{i}", draft("document_section", title, payload, [ref])))
    for key, title, body, role in [
        ("B0", "七个重点功能和调用链", source("CORE.md"), "methods"),
        ("B1", "验证、边界与实施顺序", "程序实际完成Project默认explore/fine、保留L0–L4与总结建议，显式策略优先。\n\n接口设计完成40个领域方法、3个执行控制方法和72种数据结构，结构检查12个正负样例通过；尚未接入运行检索算法。\n\nquick实际135项Python通过、1项既有冻结夹具失败；19项前端因缺开发依赖未运行。真实setup扩展旧工作区升级/重复升级/恢复通过，但未进行第二台物理机验收。\n\n后续按G01固定读取与范围 → 表示和索引 → 召回/排序/关系 → 渐进编排和上下文实施。每步保留实际水位、失败和固定证据。保存成功不提升科学复核状态。", "conclusion")]:
        payload = {"section_key": key.lower(), "title": title, "role": role,
            "blocks": [{"type": "prose", "markdown": body, "evidence_refs": units}], "watch_refs": [], "missing_refs": []}
        ops.append(put(key, draft("document_section", title, payload, units)))
    print(json.dumps(submit(attempt, "sections", ops, state["head"]["commit_id"]), ensure_ascii=False))

def stage_three():
    parent = next((RUN / "actual-ai/A03").glob("attempt-*"))
    state, sections = read_saved(parent, "sections", "sections")
    units_map = json.loads((RUN / "layered-fixed-records.json").read_text(encoding="utf-8"))
    units = [units_map[f"U{i:02d}"] for i in range(8)]
    attempt = ai.initialize(RUN / "actual-ai", "A04", RUN / "user-steering.md", "assistant", None,
                           "continuous", str(parent), RUN / "ai-input-environment.json")
    ops = []
    for key, dtype, title, keys in [("PROCESS", "research_process", "接口契约与Project记录：完整设计过程", [f"P{i}" for i in range(8)]),
                                    ("BRIEF", "research_report", "接口契约与Project记录：核心简报", ["B0", "B1"])]:
        section_refs = [sections[k] for k in keys]
        payload = {"document_type": dtype, "purpose": "供设计复核和下一阶段实施使用" if key == "PROCESS" else "快速了解核心接口、已完成变化和验证边界",
            "audience": "框架开发者与评审者" if key == "PROCESS" else "项目使用者与实施决策者",
            "scope": "本项目接口契约v0.1；仅Project默认策略已实际修改，运行适配待实施。",
            "common_refs": units, "section_refs": section_refs, "watch_refs": [], "missing_refs": []}
        ops.append(put(key, draft("document", title, payload, section_refs)))
    print(json.dumps(submit(attempt, "documents", ops, state["head"]["commit_id"]), ensure_ascii=False))
    read_saved(attempt, "documents", "documents")

def stage_read():
    attempts = {key: next((RUN / "actual-ai" / key).glob("attempt-*")) for key in ("A01", "A03", "A04")}
    documents = json.loads((RUN / "documents-fixed-records.json").read_text(encoding="utf-8"))
    sections = json.loads((RUN / "sections-fixed-records.json").read_text(encoding="utf-8"))
    units = json.loads((RUN / "layered-fixed-records.json").read_text(encoding="utf-8"))
    def request_call(scenario, name, action, request):
        path = RUN / (name + "-request.json")
        write(path, request)
        result, directory = call(attempts[scenario], [action, "--request", str(path)], path)
        write(RUN / (name + "-result.json"), result)
        text = result.get("context_text", result.get("markdown", ""))
        if text:
            (RUN / (name + ".md")).write_text(text, encoding="utf-8")
        print(json.dumps({"name": name, "keys": list(result), "evidence": str(directory),
                          "manifest": result.get("manifest"), "coverage": result.get("report_coverage")}, ensure_ascii=False))
    request_call("A01", "expand-source", "expand", {"refs": refs("CORE.md"), "budget": 30000})
    request_call("A01", "expand-unit", "expand", {"refs": [units["U07"]], "budget": 30000})
    for key in ("PROCESS", "BRIEF"):
        ref = documents[key]
        request = {"owner_id": OWNER, "document_id": ref["target_id"], "revision": ref["revision"]}
        request_call("A04", key.lower() + "-document", "document", request)
        request_call("A04", key.lower() + "-outline", "outline", request)
    request_call("A03", "definition-context", "section-context", {"owner_id": OWNER,
        "document_id": documents["PROCESS"]["target_id"], "revision": 1,
        "section_id": sections["P1"]["target_id"], "budget": {"max_chars": 100000}})

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["one", "two", "three", "read"])
    args = parser.parse_args()
    {"one": stage_one, "two": stage_two, "three": stage_three, "read": stage_read}[args.stage]()
