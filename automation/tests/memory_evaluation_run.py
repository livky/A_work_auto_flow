"""W13 固定合成检索评价准备/执行；默认仅 development，留出需显式 final。

命令：automation/python.ps1 automation/tests/memory_evaluation_run.py --output
.local/memory-evaluation-v1 --prepare-only。已有输出用 --reuse 继续评价。
真实合成复核只检查冻结原文与声明/边界一致，不宣称现实实验通过。
"""
from collections import defaultdict
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "automation/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_fixture import materialize, FIXTURES
import evidence
import retrieval
from memory import contracts, evaluation, index, owners
from memory.benchmark import install_model, synchronous_fts_only, write_json
from memory.service import MemoryService


VERIFIER = '''"""Actual synthetic text consistency check; no physical experiment."""
import hashlib,json,sys
from pathlib import Path
spec=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raw=Path(spec["source"]).read_bytes()
assert hashlib.sha256(raw).hexdigest()==spec["sha256"], "input fingerprint differs"
text=raw.decode("utf-8-sig")
assert "SYNTHETIC ONLY" in text, "not a synthetic source"
for value in [spec["statement"],*spec["limitations"]]:
    assert value in text, "frozen statement or boundary absent from source"
print(json.dumps({"synthetic_only":True,"validation":"source-text consistency only",
"statement":spec["statement"],"limitations":spec["limitations"],"input_sha256":spec["sha256"],
"assertions_passed":2+len(spec["limitations"])},ensure_ascii=False))
'''


def execute_legacy(fixture):
    """执行子进程校验后调用既有 review/finalize，不能复制状态充当执行。"""
    script = fixture.root / "synthetic-verifier.py"
    script.write_text(VERIFIER, encoding="utf-8")
    script_hash = evidence.sha256(script)
    recipes = json.loads((FIXTURES / "records.json").read_text(encoding="utf-8"))
    receipts = []
    for recipe in recipes["legacy_runs"]:
        source = fixture.sources[recipe["inputs"][0]]
        path = fixture.root / fixture.owners[recipe["run_id"]]["path"]
        spec = path.parent / "verification-input.json"
        write_json(spec, {"source": str(fixture.root / source["path"]), "sha256": source["sha256"],
            "statement": recipe["statement"], "limitations": recipe["limitations"]})
        result = subprocess.run([sys.executable, str(script), str(spec)], capture_output=True, check=True, encoding="utf-8")
        artifact = path.parent / "result.json"
        artifact.write_text(result.stdout, encoding="utf-8")
        raw = evidence.read(path)
        raw.update(status="succeeded", limitations=[*recipe["limitations"], "SYNTHETIC ONLY: source text consistency; no physical or business validation"],
            keywords=recipe["keywords"], code={"commit": script_hash, "git_commit": None, "dirty": False,
                "version_kind": "source-snapshot-sha256", "scope": "exact synthetic-verifier.py only"},
            environment={"python": platform.python_version(), "lock_or_image_digest": evidence.sha256(Path(sys.executable))},
            inputs=[{"path": source["path"], "sha256": source["sha256"]},
                    {"path": script.relative_to(fixture.root).as_posix(), "sha256": script_hash}],
            artifacts=[{"path": artifact.relative_to(fixture.root).as_posix(), "sha256": evidence.sha256(artifact)}],
            quality_results=[{"check": "Executed synthetic source-text consistency verifier", "required": True, "status": "passed"}])
        write_json(path, raw)
        review = evidence.review_claim(fixture.root, recipe["claim_id"], "accepted", "synthetic-authorized-text-workflow",
            "Actual subprocess checked frozen source hash, exact statement and limitations; no business validity asserted",
            evidence=artifact.relative_to(fixture.root).as_posix(), scope=recipe["claim_scope"])
        finalized = evidence.finalize_run(fixture.root, recipe["run_id"], recipe["claim_scope"])
        if not finalized["finalized"]:
            raise RuntimeError(str(finalized))
        # The old fulltext baseline consumes the real native README and Run,
        # which must contain the executed statement rather than template prose.
        (path.parent / "README.md").write_text("# SYNTHETIC ONLY " + recipe["run_id"] + "\n\n" +
            recipe["question"] + "\n\n" + recipe["statement"] + "\n\n" + "\n".join(recipe["limitations"]), encoding="utf-8")
        receipts.append({"run_id": recipe["run_id"], "command": result.args, "exit_code": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr, "review": review, "finalization": finalized})
    graph = evidence.EvidenceGraph(fixture.root)
    def refresh(value):
        if isinstance(value, dict):
            if value.get("target_kind") in {"owner", "claim"} and value.get("target_id") in graph.nodes:
                value["sha256"] = graph.nodes[value["target_id"]]["fingerprint"]
            for child in value.values():
                refresh(child)
        elif isinstance(value, list):
            for child in value:
                refresh(child)
    refresh(fixture.drafts)
    return receipts


def prepare(output):
    """所有配方由真实服务创建新规范 ID，映射用于标签翻译而非强制写 ID。"""
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
    fixture = materialize(output / "workspace", isolation_root=output)
    receipts = execute_legacy(fixture)
    write_json(output / "legacy-execution.json", receipts)
    owner_mapping = {}
    for recipe_id, descriptor in fixture.owners.items():
        if descriptor["owner_type"] != "knowledge":
            continue
        path = fixture.root / descriptor["path"]
        adopted = owners.adopt_owner(fixture.root, descriptor["path"], evidence.sha256(path),
                                    {"kind": "workflow", "id": "synthetic-evaluation"})
        owner_mapping[recipe_id] = adopted["owner_id"]
    def remap_owner(value):
        if isinstance(value, dict):
            if value.get("owner_id") in owner_mapping:
                value["owner_id"] = owner_mapping[value["owner_id"]]
            if value.get("target_kind") == "owner" and value.get("target_id") in owner_mapping:
                value["target_id"] = owner_mapping[value["target_id"]]
            for child in value.values():
                remap_owner(child)
        elif isinstance(value, list):
            for child in value:
                remap_owner(child)
    remap_owner(fixture.drafts)
    grouped = defaultdict(list)
    for value in fixture.drafts:
        grouped[value["owner_id"]].append(value)
    mapping, heads, commits = dict(owner_mapping), {}, []
    service = MemoryService(fixture.root)
    with synchronous_fts_only():
        while grouped:
            progressed = False
            for oid, values in list(grouped.items()):
                ids = {v["record_id"] for v in values}
                dependencies = {ref["target_id"] for value in values for ref in index.references(value)
                                if ref["target_kind"] == "record"} - ids
                if dependencies - mapping.keys():
                    continue
                receipt = service.commit(fixture.request([v["record_id"] for v in values], reference_ids=mapping))
                mapping.update({r["client_key"]: r["record_id"] for r in receipt["record_results"]})
                heads[oid] = receipt["commit_id"]; commits.append(receipt)
                del grouped[oid]; progressed = True
            if not progressed:
                raise RuntimeError("Unresolved cross-owner recipe dependencies: " + str(list(grouped)))
    write_json(output / "mapping.json", mapping)
    write_json(output / "commits.json", commits)
    install_model(fixture.root, ROOT)
    # All old Run files are generated synthetic material, authorized by fixture.
    retrieval.index(fixture.root)
    result = index.rebuild(fixture.root, vector="required")
    if result["index_status"] != "indexed":
        raise RuntimeError(str(result))
    write_json(output / "preparation.json", {"root": str(fixture.root), "records": sum(key.startswith("MEM-") for key in mapping),
        "mapped_identity_count": len(mapping), "heads": heads,
        "fixture_sha256": hashlib.sha256((FIXTURES / "records.json").read_bytes()).hexdigest(),
        "model_sha256": evidence.sha256(fixture.root / "services/qdrant/model-manifest.json"),
        "source_hashes": {str(p.relative_to(ROOT)): evidence.sha256(p) for p in (ROOT / "automation/scripts/memory").glob("*.py")},
        "index": result, "limitation": "Synthetic text consistency only; not real model/business validation"})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--split", choices=("development", "holdout"), default="development")
    parser.add_argument("--phase", choices=("development", "final"), default="development")
    parser.add_argument("--report-name", help="独立评价版本名（默认split）；拒绝覆盖已有排名")
    args = parser.parse_args()
    queries = evaluation.load_queries(FIXTURES / "queries.json", split=args.split, phase=args.phase)
    output = Path(args.output).resolve() if args.reuse else prepare(args.output)
    if args.prepare_only:
        return 0
    mapping = json.loads((output / "mapping.json").read_text(encoding="utf-8"))
    runners = evaluation.build_runners(output / "workspace")
    report_name = args.report_name or args.split
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", report_name):
        parser.error("report-name 只允许字母、数字、下划线和连字符")
    report_path = output / (report_name + "-rankings.json")
    if report_path.exists():
        raise ValueError("既有排名不能覆盖；选择新的 report-name 并保留旧评价")
    program_hashes = {str(p.relative_to(ROOT)): evidence.sha256(p) for p in (ROOT / "automation/scripts/memory").glob("*.py")}
    with (output / (report_name + "-queries.jsonl")).open("x", encoding="utf-8") as stream:
        def progress(row):
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            print(json.dumps({"variant": row["variant"], "query_id": row["query_id"], "metrics": row["metrics"]}, ensure_ascii=False), flush=True)
        result = evaluation.compare_variants(queries["queries"], runners, id_mapping=mapping, phase=args.phase, progress=progress)
    final_hashes = {str(p.relative_to(ROOT)): evidence.sha256(p) for p in (ROOT / "automation/scripts/memory").glob("*.py")}
    write_json(report_path, {"fixture": queries, "variants": result,
        "source_hashes": program_hashes, "source_hashes_after": final_hashes, "program_changed_during_run": program_hashes != final_hashes,
        "timing_limitation": "Quality ranking evaluation may share host load; latency here is not the isolated Z03 measurement"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
