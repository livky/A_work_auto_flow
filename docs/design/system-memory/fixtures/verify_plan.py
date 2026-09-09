"""校验系统记忆计划输入，不实现或运行未来的记忆产品接口。

默认只读。--self-test 仅在内存副本中注入坏引用、缺资产等错误；
--freeze 仅独占创建一个新版本的指纹清单，绝不覆盖已有文件。
输出 JSON；退出 0=计划输入有效，1=验证失败，2=参数或读取失败。
仅使用 Python 标准库，支持 Windows x64 与中文/空格路径。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys


JSON_NAMES = (
    "records.json", "queries.json", "negative-drafts.json", "scenarios.json",
    "acceptance.json", "work-packages.json", "ai-cases.json", "variants.json",
)
OWNER_TYPES = {"research", "run", "project", "core-algorithm", "knowledge", "report", "data", "tool"}
LEVELS = {"source": "L0", "event": "L1", "experience": "L2", "map": "L3"}
AUXILIARY = {"question", "goal", "route", "checkpoint", "association", "representation", "policy", "consolidation", "feedback"}
EXPECTED_COUNTS = {"owners": 23, "records": 48, "legacy_runs": 8, "sources": 8,
                   "queries": 48, "negative": 16, "scenarios": 16, "cases": 115,
                   "packages": 14, "ai_cases": 12}


def digest(content: bytes) -> str:
    """按原字节哈希，避免 Windows 换行或 BOM 被静默规范化。"""
    return hashlib.sha256(content).hexdigest()


def read_inputs(base: Path):
    data = {name: json.loads((base / name).read_text(encoding="utf-8-sig")) for name in JSON_NAMES}
    # 固定受控输入集合，不扫描共享盘、业务对象或模型缓存。
    files = {name: (base / name).read_bytes() for name in JSON_NAMES}
    for path in sorted((base / "sources").glob("*.md")):
        if path.is_symlink() or not path.resolve().is_relative_to(base):
            raise ValueError("来源资产不能通过链接指向配方目录之外")
        files[path.relative_to(base).as_posix()] = path.read_bytes()
    for name in ("README.md", "verify_plan.py"):
        files[name] = (base / name).read_bytes()
    docs = {name: (base.parent / name).read_text(encoding="utf-8-sig")
            for name in ("01-data-contracts.md", "02-services-algorithms.md",
                         "03-work-packages.md", "04-acceptance.md")}
    return data, files, docs


def targets(value):
    """仅遍历显式 RefSpec，不把正文里出现的任意 ID 当正式引用。"""
    if isinstance(value, dict):
        if "target_id" in value:
            yield value
        for child in value.values():
            yield from targets(child)
    elif isinstance(value, list):
        for child in value:
            yield from targets(child)


def validate(data, files, docs):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def unique(rows, field):
        values = [row.get(field) for row in rows]
        require(all(isinstance(x, str) and x for x in values), "missing ID: " + field)
        require(len(values) == len(set(values)), "duplicate ID: " + field)
        return set(values)

    bundle = data["records.json"]
    queries = data["queries.json"]["queries"]
    negative = data["negative-drafts.json"]["negative"]
    scenarios = data["scenarios.json"]["scenarios"]
    cases = data["acceptance.json"]["cases"]
    packages = data["work-packages.json"]["packages"]
    ai_cases = data["ai-cases.json"]["cases"]
    rows = {"owners": bundle["owners"], "records": bundle["records"],
            "legacy_runs": bundle["legacy_runs"], "sources": bundle["sources"],
            "queries": queries, "negative": negative, "scenarios": scenarios,
            "cases": cases, "packages": packages, "ai_cases": ai_cases}
    counts = {name: len(value) for name, value in rows.items()}
    for name, expected in EXPECTED_COUNTS.items():
        require(counts[name] == expected, f"count mismatch: {name}: {counts[name]} != {expected}")

    owner_ids = unique(bundle["owners"], "owner_id")
    record_ids = unique(bundle["records"], "record_id")
    source_ids = unique(bundle["sources"], "source_id")
    run_ids = unique(bundle["legacy_runs"], "run_id")
    claim_ids = unique(bundle["legacy_runs"], "claim_id")
    query_ids = unique(queries, "query_id")
    negative_ids = unique(negative, "negative_id")
    scenario_ids = unique(scenarios, "scenario_id")
    case_ids = unique(cases, "test_id")
    package_ids = unique(packages, "package_id")
    unique(ai_cases, "case_id")
    known = owner_ids | record_ids | source_ids | claim_ids
    require(bundle.get("synthetic_only") is True, "missing synthetic marker")
    require({x["owner_type"] for x in bundle["owners"]} == OWNER_TYPES, "owner type coverage")
    require(run_ids <= owner_ids, "legacy run owner missing")

    by_record = {x["record_id"]: x for x in bundle["records"]}
    representation_keys = []
    for record in bundle["records"]:
        rid, kind, payload = record["record_id"], record["kind"], record["payload"]
        require(record["owner_id"] in owner_ids, "unknown owner: " + rid)
        require(kind in LEVELS or kind in AUXILIARY, "unknown kind: " + rid)
        require(record["level"] == LEVELS.get(kind), "level mismatch: " + rid)
        for ref in targets(record):
            require(ref["target_id"] in known, "unknown target: " + ref["target_id"])
            if ref["target_id"].startswith("MEM-"):
                require(isinstance(ref.get("revision"), int) and ref["revision"] > 0,
                        "record revision missing: " + rid)
        if kind == "experience":
            require(bool(payload.get("applicable")), "missing applicable: " + rid)
            require(bool(payload.get("prohibited")), "missing prohibited: " + rid)
        if kind == "question":
            if payload["status"] == "resolved":
                require(bool(payload["resolution_refs"]), "resolved without basis: " + rid)
            if payload["status"] == "superseded":
                replacement = payload.get("replacement_ref") or {}
                require(replacement.get("target_id") in record_ids - {rid}, "invalid replacement: " + rid)
        if kind == "association" and payload["relation"] == "analogous_to":
            require(bool(payload["shared_structure"]) and bool(payload["transfer_limits"]), "analogy boundary missing")
        if kind == "representation":
            representation_keys.append((payload["target"]["target_id"], payload["slot"]))
    require(len(representation_keys) == len(set(representation_keys)), "duplicate representation slot")
    require({r["level"] for r in bundle["records"] if r["level"]} == set(LEVELS.values()), "four-layer coverage")
    require({r["payload"]["status"] for r in bundle["records"] if r["kind"] == "question"}
            == {"open", "investigating", "blocked", "resolved", "superseded"}, "question state coverage")
    for source in bundle["sources"]:
        require(source["path"] in files, "missing asset: " + source["path"])
        require("SYNTHETIC ONLY" in files.get(source["path"], b"").decode("utf-8-sig"), "asset marker missing")
    for review in bundle["review_recipes"]:
        require(review["claim_id"] in claim_ids and review["evidence_source"] in source_ids, "review recipe target missing")

    # 只验证标签的可追溯性；不把这项检查称为检索准确率评价。
    require(sum(q["split"] == "development" for q in queries) == 32, "development split mismatch")
    require(sum(q["split"] == "holdout" for q in queries) == 16, "holdout split mismatch")
    for query in queries:
        require(query["owner_id"] in owner_ids, "query owner missing")
        relevant = query["relevant"]
        require(bool(relevant), "query has no relevance labels")
        require(len({r["canonical_id"] for r in relevant}) == len(relevant), "duplicate relevance label")
        for item in relevant:
            require(item["canonical_id"] in known and item["grade"] in (1, 2, 3), "unknown relevance target")
        bodies = "\n".join(by_record[r["canonical_id"]]["body_markdown"] for r in relevant if r["canonical_id"] in by_record)
        for boundary in query["must_retain"]:
            require(boundary in bodies, "query boundary absent from source: " + query["query_id"])
    for scenario in scenarios:
        require(set(scenario["record_ids"]) <= record_ids, "scenario record missing")
    for item in negative:
        require(item["target_id"] in record_ids, "negative base missing")
        require(bool(item["replace"]) and bool(item["expected_error"]), "incomplete negative recipe")

    used_negative, used_scenarios = set(), set()
    for case in cases:
        tid = case["test_id"]
        require(case["package_id"] in package_ids, "unknown package: " + tid)
        require(set(case["scenario_ids"]) <= scenario_ids, "unknown scenario: " + tid)
        require(set(case["negative_ids"]) <= negative_ids, "unknown negative: " + tid)
        used_negative.update(case["negative_ids"])
        used_scenarios.update(case["scenario_ids"])
        require(bool(case["steps"]) and bool(case["acceptance"]) and bool(case["evidence"]), "incomplete acceptance: " + tid)
        require(case["status"] == "not-run", "spec must not claim executed product tests")
        require(f"### {tid} {case['title']}" in docs["04-acceptance.md"], "human view missing test: " + tid)
        for sentence in case["steps"] + case["acceptance"]:
            require(sentence in docs["04-acceptance.md"], "human view drift: " + tid)
    require(used_negative == negative_ids, "uncovered negative recipe")
    require(used_scenarios == scenario_ids, "uncovered scenario")
    for package in packages:
        pid = package["package_id"]
        expected_tests = {c["test_id"] for c in cases if c["package_id"] == pid}
        require(set(package["test_ids"]) == expected_tests and bool(expected_tests), "package test mapping: " + pid)
        require(set(package["depends_on"] + package.get("verification_depends_on", [])) <= package_ids,
                "package dependency missing: " + pid)
        require(f"## {pid} {package['title']}" in docs["03-work-packages.md"], "human package missing: " + pid)
    graph = {p["package_id"]: p["depends_on"] + p.get("verification_depends_on", []) for p in packages}
    active, visited = set(), set()

    def visit(pid):
        if pid in active:
            errors.append("dependency cycle: " + pid)
            return
        if pid in visited or pid not in graph:
            return
        active.add(pid)
        for parent in graph[pid]:
            visit(parent)
        active.remove(pid)
        visited.add(pid)

    for pid in graph:
        visit(pid)
    for item in ai_cases:
        require(item["must"] and item["forbidden"] and item["repetitions"] == 3, "AI rubric incomplete")
    variants = data["variants.json"]
    require({x["category"] for x in variants["failure_payloads"]}
            == {"execution", "no_improvement", "counterexample", "insufficient_evidence"}, "failure category coverage")
    for change in variants["source_changes"]:
        require(change["asset"] in files, "missing variant asset")
    return errors, counts


def self_test(data, files, docs):
    """对校验器做反例检查；只改内存副本，不损坏工作区或冻结素材。"""
    mutations = [
        ("unknown_reference", lambda d, f, v: d["records.json"]["records"][1]["sources"].append({"target_id": "MEM-ABSENT", "revision": 1}), "unknown target"),
        ("duplicate_id", lambda d, f, v: d["records.json"]["records"].append(copy.deepcopy(d["records.json"]["records"][0])), "duplicate ID"),
        ("lost_boundary", lambda d, f, v: d["records.json"]["records"][1]["payload"].update(applicable=[]), "missing applicable"),
        ("unknown_scenario", lambda d, f, v: d["acceptance.json"]["cases"][0]["scenario_ids"].append("SC-ABSENT"), "unknown scenario"),
        ("dependency_cycle", lambda d, f, v: d["work-packages.json"]["packages"][0]["depends_on"].append("W13"), "dependency cycle"),
        ("missing_asset", lambda d, f, v: f.pop("sources/thermal.md"), "missing asset"),
        ("missing_query", lambda d, f, v: d["queries.json"]["queries"].pop(), "count mismatch: queries"),
        ("false_pass", lambda d, f, v: d["acceptance.json"]["cases"][0].update(status="passed"), "spec must not claim"),
        ("human_view_drift", lambda d, f, v: v.update({"04-acceptance.md": v["04-acceptance.md"].replace("### C01 四层及辅助实体契约", "### OMITTED", 1)}), "human view missing test"),
    ]
    results = []
    for name, mutate, expected in mutations:
        changed, changed_files, changed_docs = copy.deepcopy(data), dict(files), dict(docs)
        mutate(changed, changed_files, changed_docs)
        errors, _ = validate(changed, changed_files, changed_docs)
        results.append({"name": name, "detected": any(expected in error for error in errors)})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="在内存副本中运行校验器反例，不运行产品测试")
    parser.add_argument("--freeze", action="store_true", help="首次独占创建指纹清单；已有文件绝不覆盖")
    parser.add_argument("--manifest", default="fixture-manifest.json", help="本目录中的版本清单文件名")
    args = parser.parse_args(argv)
    base = Path(__file__).resolve().parent
    try:
        if not re.fullmatch(r"fixture-manifest(?:[.-]v[0-9]+)?\.json", args.manifest):
            raise ValueError("manifest必须是本目录中的fixture-manifest[.v数字].json文件名")
        data, files, docs = read_inputs(base)
        errors, counts = validate(data, files, docs)
        hashes = {name: digest(content) for name, content in sorted(files.items())}
        manifest_path = base / args.manifest
        if args.freeze:
            if not errors:
                # x模式提供不可覆盖保证；没有递归写入、联网或生产目录副作用。
                with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
                    json.dump({"fixture_version": 1, "synthetic_only": True, "counts": counts, "files": hashes},
                              stream, ensure_ascii=False, indent=2)
                    stream.write("\n")
        else:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            if manifest["files"] != hashes or manifest["counts"] != counts:
                errors.append("fixture manifest mismatch: 输入或数量与冻结清单不同")
        probes = self_test(data, files, docs) if args.self_test else []
        errors.extend("self-test failed: " + p["name"] for p in probes if not p["detected"])
        result = {"scope": "plan-input-validation-only", "valid": not errors, "counts": counts,
                  "self_checks": probes, "product_tests_executed": 0,
                  "plan_document_hashes": {name: digest(text.encode("utf-8")) for name, text in docs.items()},
                  "manifest_sha256": digest(manifest_path.read_bytes()) if manifest_path.is_file() else None,
                  "errors": errors}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"scope": "plan-input-validation-only", "valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
