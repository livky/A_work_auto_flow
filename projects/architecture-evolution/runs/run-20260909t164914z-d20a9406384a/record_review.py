"""保存本轮已发生的阅读、自查及回读导出；不生成或推断人工验收。"""
from pathlib import Path
import importlib.util
import json

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
spec = importlib.util.spec_from_file_location("actual_ai", ROOT / "automation/testing/ai_review.py")
ai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)

def read(name):
    return json.loads((RUN / name).read_text(encoding="utf-8"))

def write(name, value):
    path = RUN / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path

# 导出正文直接来自公开 document 回读；固定引用仍以 JSON 回执为准。
for key in ("process", "brief"):
    result = read(key + "-document-result.json")
    text = ["# " + result["document"]["title"], "", result["document"]["scope"], ""]
    for section in result["report"]["sections"]:
        text += ["## " + section["title"], ""]
        for block in section["blocks"]:
            if block["type"] == "prose":
                text += [block["markdown"], ""]
            else:
                text.extend(b["markdown"] + "\n" for b in block["resolved_blocks"])
    exported = "\n".join(text)
    # 导出改变了文件位置，只重定位阅读链接，原始回执和规范正文保持不变。
    for leaf in ("FUNCTIONS.md", "SPEC.md", "DATATYPES.md", "IMPLEMENTATION.md"):
        exported = exported.replace("](" + leaf + ")", "](../../design/interfaces-v0.1/" + leaf + ")")
    for leaf in ("graph-research.md", "retrieval-boundaries.md", "storage-boundaries.md"):
        exported = exported.replace("](" + leaf + ")", "](../run-20260909t155125z-2961bdf175a8/" + leaf + ")")
    (RUN / (key + "-document.md")).write_text(exported, encoding="utf-8")

process, brief = (read(key + "-document-result.json") for key in ("process", "brief"))
context = read("definition-context-result.json")
checks = {
    "authored_fields_roundtrip": {"layered": 11, "sections_and_map": 11, "documents": 2},
    "independent_documents": process["document"]["record_id"] != brief["document"]["record_id"],
    "same_common_refs": process["document"]["common_refs"] == brief["document"]["common_refs"],
    "process_sections": len(process["report"]["sections"]), "brief_sections": len(brief["report"]["sections"]),
    "complete": {key: value["report"]["complete"] for key, value in (("process", process), ("brief", brief))},
    "uncovered": {key: value["report_coverage"]["uncovered_detail_ids"] for key, value in (("process", process), ("brief", brief))},
    "missing": {key: value["missing"] for key, value in (("process", process), ("brief", brief))},
    "definition_closure": [r.get("block_ids") for r in context["manifest"]["read_refs"] if "block_ids" in r],
    "context_complete": context["manifest"]["complete"],
    "ui": "not-verified: browser ERR_BLOCKED_BY_CLIENT for existing local workbench",
    "human_review": "pending", "scientific_review": "not-reviewed",
}
write("memory-readback-checks.json", checks)
write("ui-check.json", {"attempted": True, "url": "http://127.0.0.1:52763", "tool": "cua.createBrowserTab",
                       "result": "Browser Use cannot open the local URL; net::ERR_BLOCKED_BY_CLIENT",
                       "page_read": False, "screenshot": None,
                       "scope": "两种文稿的实际页面目录、公式、图和链接尚未验证；未绕过浏览器限制。"})

# 每一条观察由本次 AI 实际阅读后编写；机械比较与模型阅读范围分别说明。
observations = {
    "A01": [
        ("meets", "11条作者字段逐项回读相等；抽读U07完整正文，明确Project归属、设计状态和适用边界。", "layered-inspect.json"),
        ("meets", "公开inspect后实际expand U07与CORE原来源，两者返回full、无missing/omitted。已读取U07正文及来源回执。", "expand-unit-result.json"),
        ("meets", "请求actor为ai，没有review操作；记录不借保存成功提升科学复核。首次decision_refs预检失败保留，补齐依据后新请求提交。", "layered-v2-request.json"),
    ],
    "A03": [
        ("meets", "技术单元保存问题、方法、主要发现、适用与不适用范围；完整技术块包含实际接口语义和代码字段。", "layered-inspect.json"),
        ("meets", "P1仅选technical-body，实际section-context补入scope定义块，返回完整且缺失为空；已抽读集合范围公式及变量定义。这里只确认文本，页面渲染尚未核验。", "definition-context-result.json"),
        ("meets", "分析单元run_ref为null且依据固定16个已登记文件来源；章节与文稿使用真实record_hash与revision，不借content_hash替代。", "sections-inspect.json"),
    ],
    "A04": [
        ("meets", "公开document与outline分别读回8章过程稿、2章简报；正文来源完整，共24条规范记录，作者字段全部相等。", "memory-readback-checks.json"),
        ("meets", "两文稿common_refs一致，均覆盖8个L1；已阅读全文简报回执，保留算法未接入、135通过/1失败/19未运行及第二台物理机未验收。", "brief-document-result.json"),
        ("cannot-assess", "内置浏览器访问现有本地工作台返回ERR_BLOCKED_BY_CLIENT，未取得页面或截图；目录/公式/图/链接的实际页面效果不能判定。", "ui-check.json"),
    ],
}
reads = {"A01": ("expand-unit.md", "全文", "full", "已读取U07正文、七项功能、调用链、记录规则及固定来源。"),
         "A03": ("definition-context.md", "开头至集合范围公式与变量说明；其余代码仅机械对比", "partial", "范围公式、属性/证据区分、定义块补齐可从实际回读文本核对。"),
         "A04": ("brief-document-result.json", "report.sections的两个章节全文及共同引用", "partial", "已读取两个章节正文和固定来源；未遍读回执每个重复引用元数据。")}
for scenario, rows in observations.items():
    attempt = next((RUN / "actual-ai" / scenario).glob("attempt-*"))
    filename, locator, coverage, observation = reads[scenario]
    event = write(scenario + "-reading-input.json", {"actor": "assistant", "origin": {"fixed_ref": filename},
        "capture_path": str(RUN / filename), "locator": locator, "coverage": coverage,
        "observation": observation, "unread_or_missing": ["工作台实际页面未读取"] if scenario == "A04" else []})
    ai.record_read(attempt, event)
    assessment = write(scenario + "-assessment-input.json", {"actor": "assistant",
        "comparisons": [{"expectation_id": f"{scenario}-E{i+1}", "status": status, "observation": observation,
                         "evidence_refs": [str(RUN / file)]} for i, (status, observation, file) in enumerate(rows)],
        "readable_artifacts": [], "limitations": ["同一连续任务内AI自查；未作为新上下文场景A02", "人工意见待收集，科学结论未复核", "页面视觉检查受浏览器限制未完成"],
        "human_review": "pending", "scientific_review": "not-reviewed"})
    ai.record_assessment(attempt, assessment)
print(ai.render(RUN / "actual-ai"))
print(json.dumps(checks, ensure_ascii=False))
