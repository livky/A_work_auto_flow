"""在隔离F1上记录六种表示的实际读取和输出成本；不是检索质量或规模验收。

用法：automation/python.ps1 <本文件> --out <本Run内尚不存在的目录>
输入为受控合成fixture及当前程序；输出JSON保留逐次公共应用回执、固定输入
和程序指纹。退出码0仅说明测量执行完毕，不表示每个包完整或业务模型有效。
"""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from unittest.mock import patch
import uuid


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "workspace.json").is_file())
sys.path[:0] = [str(ROOT / "automation/scripts"), str(ROOT / "automation/tests")]
from material_query_fixture import materialize
from material_query.api import dispatch
from material_query.budget import DEFAULT_BUDGET
from material_query.contracts import AssociationOptions, DefinitionRef, QueryRequest, Scope
from material_query.coordinator import Coordinator
from material_query.reader import MeteredStore
from material_query.legacy_adapter import from_legacy
from material_query.wire import json_value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    destination = args.out.resolve()
    run = Path(__file__).resolve().parent.parent
    if not destination.is_relative_to(run) or destination.exists():
        parser.error("输出必须是本Run内尚不存在的子目录")
    destination.mkdir(parents=True)
    isolated = ROOT / ".local/testing" / ("query-cost-" + uuid.uuid4().hex)
    fixture = materialize(isolated / "workspace", isolation_root=isolated)
    scope = Scope((fixture.owner_ids["A"], fixture.owner_ids["B"]), None, None, None, None, None, None, False, (), (), None, None)
    observations = []
    # Each scenario intentionally starts a new query. Within that query, search
    # and assembly use the same ledger; no per-stage budget reset is performed.
    for key, record_key in (("original", "A.unit.r2"), ("full", "A.unit.r2"), ("section", "A.unit.r2"),
                            ("unit_digest", "A.unit.r2"), ("topic", "A.report.r2"), ("domain", "A.report.r2")):
        selected = from_legacy(fixture.ref(record_key))[0]
        if key == "section":
            selected = replace(selected, locator="block:m")
        query_scope = replace(scope, include_refs=(selected,))
        query = QueryRequest(DefinitionRef(key, "1"), fixture.record_ids[record_key], (), query_scope, scope, "exploration",
            AssociationOptions("off", "existing-relations", "1", 2, 0.15, None), DEFAULT_BUDGET,
            "fixed", 10, "reject", (), "", channels=("identity",))
        app = Coordinator(fixture.root)
        opened = set()
        read_json = MeteredStore.read_json

        def trace(store, path):
            # Observe actual canonical body opens separately from manifest/HEAD
            # metadata. The underlying reader still owns authorization and cost.
            if path.parent.name == "records":
                opened.add(path.relative_to(fixture.root).as_posix())
            return read_json(store, path)

        started = time.perf_counter()
        try:
            with patch.object(MeteredStore, "read_json", trace):
                search = dispatch(app, "search", json_value(query))
                receipt = search.get("value")
                assembly = None
                if receipt and receipt["candidates"]:
                    assembly = dispatch(app, "assemble", {"query_id": receipt["query_id"], "expected_request_digest": receipt["request_digest"],
                        "candidate_ids": [item["candidate_id"] for item in receipt["candidates"]]})
            observations.append({"definition": key, "input_ref": fixture.ref(record_key), "request": json_value(query),
                                 "search": search, "assembly": assembly, "canonical_body_paths": sorted(opened),
                                 "elapsed_seconds": time.perf_counter() - started})
        finally:
            app.close()
    program_files = list((ROOT / "automation/scripts/material_query").glob("*.py")) + [ROOT / "automation/tests/material_query_fixture.py", Path(__file__)]
    output = {"synthetic_only": True, "fixture_root": str(fixture.root), "budget_per_query": asdict(DEFAULT_BUDGET),
        "python": sys.version, "platform": platform.platform(), "observations": observations,
        "program_fingerprints": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in program_files},
        "limitations": ["同机小型F1；未执行万条规模、真实业务质量或另一物理机验收", "elapsed包含本机负载；read_bytes包括重复元数据读取", "独立查询不共享预算；同一查询的查询与组包累计"]}
    (destination / "results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(destination / "results.json"), "scenarios": len(observations)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
