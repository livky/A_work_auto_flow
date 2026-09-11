"""回读迁移后的真实研究：三种内容来源及概览→经过/技术的固定展开。

只读规范内容；查询状态与回执保存在 .local。默认使用工作台的同一预算。
脚本只报告软件返回和正文；AI 是否理解正文另写实际审查说明。
"""
from dataclasses import replace
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

root = Path.cwd()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--wall-ms", type=int, default=10000, help="本次查询累计时间上限；不改变工作台默认值")
parser.add_argument("--output-name", default="content-readback", help="本次回执名，便于保留预算不足的原回执")
args = parser.parse_args()
if not args.output_name.replace("-", "").isalnum():
    parser.error("output-name 只能含字母、数字和连字符")
sys.path.insert(0, str(root / "automation/scripts"))
from material_query import api
from material_query.budget import DEFAULT_BUDGET
from material_query.contracts import AssociationOptions, DefinitionRef, QueryRequest, Scope
from material_query.coordinator import Coordinator
from material_query.wire import json_value
from memory.evidence_adapter import iter_refs

owner = "RES-FLOATING-POINT-SUMMATION"
snapshot = json.loads((root / ".local/unified-layers/after.json").read_text(encoding="utf-8"))
# 来源上限只增加研究已经明确引用的 Run；召回仍限定该研究本身。
run_ids = sorted({ref["target_id"] for record in snapshot["records"].values()
                  for ref in iter_refs({"sources": record["sources"], "payload": record["payload"]})
                  if ref.get("target_kind") == "owner"})
scope = Scope((owner,), None, None, None, None, None, None, False, (), (), None, None)
ceiling = replace(scope, owner_ids=(owner, *run_ids))
base = QueryRequest(DefinitionRef("full", "1"), "浮点求和", (), scope, ceiling, "exploration",
    AssociationOptions("off", "existing-relations", "1", 0, 0, None), replace(DEFAULT_BUDGET, wall_ms=args.wall_ms), "fixed", 20, "reject", (), "")
receipts = {"note": "实际研究内容回读；不重跑实验，不登记人工科学认可。"}
coordinator = Coordinator(root)
started = perf_counter()
try:
    for source in ("overview_experience", "process", "technical"):
        request = json_value(replace(base, content_source=source))
        value = api.dispatch(coordinator, "search", request)
        receipts[source] = {"request": request, "response": value}
        print(source, value["status"], value.get("code"), value.get("warnings"), flush=True)
        assert value.get("value"), value
        rows = value["value"]["candidates"]
        print([(r.get("content_kind"), r["title"]) for r in rows], flush=True)
        assert rows, "该来源应有已迁移内容"
        if source != "overview_experience":
            continue
        chosen = [row["candidate_id"] for row in rows if row.get("content_kind") == "overview"]
        assert len(chosen) == 1, "当前概览应唯一"
        page = value["value"]
        selected = chosen[:]
        for target in ("process", "technical"):
            expanded = api.dispatch(coordinator, "expand", {"query_id": page["query_id"], "candidate_ids": chosen,
                "expected_request_digest": page["request_digest"], "target": target})
            receipts[target + "_expanded"] = expanded
            print("expand", target, expanded["status"], expanded.get("warnings"), flush=True)
            assert expanded.get("value") and expanded["value"]["candidates"], expanded
            # 实际阅读选中一段过程与一篇技术单元；未选择的内容不强塞进默认预算。
            selected.append(expanded["value"]["candidates"][0]["candidate_id"])
        assembled = api.dispatch(coordinator, "assemble", {"query_id": page["query_id"], "candidate_ids": selected,
            "expected_request_digest": page["request_digest"]})
        receipts["assembly"] = assembled
        print("assembly", assembled["status"], assembled.get("warnings"), flush=True)
        assert assembled.get("value") and len(assembled["value"]["parts"]) == 3, assembled
finally:
    receipts["elapsed_seconds"] = perf_counter() - started
    (root / ".local/unified-layers" / (args.output_name + ".json")).write_text(
        json.dumps(receipts, ensure_ascii=False, indent=2), encoding="utf-8")
    coordinator.close()
