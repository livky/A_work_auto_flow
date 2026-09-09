"""Z03 冻结规模实测：真实提交/FTS/384维材料包，失败也保留逐次真值。

运行：automation/python.ps1 automation/scripts/memory/benchmark.py --scenario distributed
      --output .local/memory-scale/distributed
兼容 Windows 嵌入式 Python；输出目录必须不存在，避免覆盖旧证据。
默认严格执行 10000 条、预热 5 次、测量 30 次；小样本只用于脚本排错，
报告明确标为非验收。程序不修改阈值、不使用留出查询、不删除结果。
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from copy import deepcopy
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import sys
import time
import uuid

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory import contracts, index, owners, packets, search
from memory.service import MemoryService


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def resources():
    """Windows GetProcessMemoryInfo 的 peak working set，单位为字节。"""
    result = {"os": platform.platform(), "python": sys.version, "logical_cpus": os.cpu_count()}
    if os.name == "nt":
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (key, ctypes.c_size_t) for key in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        values = Counters(); values.cb = ctypes.sizeof(values)
        process = ctypes.windll.kernel32.GetCurrentProcess
        process.restype = wintypes.HANDLE
        read_memory = ctypes.windll.psapi.GetProcessMemoryInfo
        read_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        read_memory.restype = wintypes.BOOL
        if read_memory(process(), ctypes.byref(values), values.cb):
            result.update(rss_bytes=values.WorkingSetSize, peak_rss_bytes=values.PeakWorkingSetSize)
        class Memory(ctypes.Structure):
            _fields_ = [("length", wintypes.DWORD), ("load", wintypes.DWORD)] + [
                (key, ctypes.c_ulonglong) for key in ("total", "available", "total_page", "available_page", "total_virtual", "available_virtual", "extended")]
        mem = Memory(); mem.length = ctypes.sizeof(mem)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            result.update(physical_ram_bytes=mem.total, available_ram_bytes=mem.available)
    else:
        import resource
        result["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    return result


def quantiles(values):
    ordered = sorted(values)
    return {"count": len(values), "seconds": values, "p50": ordered[math.ceil(.5 * len(values))-1],
            "p95": ordered[math.ceil(.95 * len(values))-1], "maximum": ordered[-1]}


def draft(oid, number):
    return {"owner_id": oid, "kind": "experience", "title": f"SYNTHETIC ONLY 规模记录 {number:05d}",
        "body_markdown": "SYNTHETIC ONLY " + ("x" * 1024), "keywords": ["规模", f"sample{number:05d}"],
        "sources": [], "provenance_gap": "隔离性能合成样本，无业务有效性", "record_reason": "Z03 固定规模",
        "discovery": "workspace_summary", "sensitivity": "internal", "payload": {
            "problem_structure": "规模测试", "recommendation": "核对全部记录身份和指纹", "applicable": ["合成样本"],
            "prohibited": ["不能用作业务结论"], "failure_modes": [], "retry_conditions": [], "claim_refs": [], "claims": []}}


def request(oid, head, operations):
    return {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": {"kind": "workflow", "id": "synthetic-z03"},
            "owner_id": oid, "expected_head": head, "operations": operations}


@contextmanager
def synchronous_fts_only():
    """保留真实 FTS 工作，仅从提交计时中排除验收定义排除的向量阶段。"""
    original = index.sync_owner
    def sync(*args, **kwargs):
        kwargs["vector"] = "off"
        return original(*args, **kwargs)
    index.sync_owner = sync
    try:
        yield
    finally:
        index.sync_owner = original


def install_model(root, source_root):
    source = source_root / "services/qdrant/models/multilingual-minilm"
    if not source.is_dir():
        raise RuntimeError("真实 384 维离线模型缺失，不允许跳过")
    for path in source.rglob("*"):
        target = root / "services/qdrant/models/multilingual-minilm" / path.relative_to(source)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(path, target)
            except OSError:
                shutil.copyfile(path, target)
    shutil.copyfile(source_root / "services/qdrant/model-manifest.json", root / "services/qdrant/model-manifest.json")
    (root / "retrieval").mkdir(exist_ok=True)
    shutil.copyfile(source_root / "retrieval/config.json", root / "retrieval/config.json")


def run(output, *, scenario, count=10000, warmup=5, measurements=30, source_root=None, measurement_gate=None, resume_seed=False):
    output = Path(output).resolve()
    prior = None
    if resume_seed:
        prior = json.loads((output / "result.json").read_text(encoding="utf-8"))
        if (prior.get("scenario") != scenario or prior.get("record_count") != count or
                prior.get("stage") not in {None, "seed", "integrity", "waiting_for_measurement_gate"} or
                any(key in prior for key in ("commit", "fts", "vector_context"))):
            raise ValueError("只可续接同一规模的未测量合成造数阶段")
        # Preserve the earlier source fingerprints, failure details and growth
        # samples before any resumed checkpoint replaces the current report.
        write_json(output / ("prior-seed-" + uuid.uuid4().hex + ".json"), prior)
    else:
        output.mkdir(parents=True, exist_ok=False)
    root = output / "workspace"; root.mkdir(exist_ok=resume_seed)
    source_root = Path(source_root or Path(__file__).resolve().parents[3])
    affinity = None
    if os.name == "nt":
        # Cap this benchmark process at eight logical processors; other desktop
        # processes remain untouched. Record physical RAM separately and never
        # describe this host as the specified 16 GiB reference machine.
        from ctypes import wintypes
        handle = ctypes.windll.kernel32.GetCurrentProcess
        handle.restype = wintypes.HANDLE
        limit_cpu = ctypes.windll.kernel32.SetProcessAffinityMask
        limit_cpu.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        affinity = (1 << min(8, os.cpu_count() or 1)) - 1
        if not limit_cpu(handle(), affinity):
            raise OSError("无法固定基准进程到 8 个逻辑核")
    oid_count = 100 if scenario == "distributed" else 1
    oids = [f"RES-SCALE-{n:03d}" for n in range(oid_count)]
    report = {"schema_version": 1, "scenario": scenario, "record_count": count, "owner_count": oid_count,
        "warmup": warmup, "measurements": measurements, "resources_start": resources(), "growth": [],
        "process_affinity_mask": affinity, "ram_reference_verified": False,
        "acceptance_scale": count == 10000 and warmup == 5 and measurements == 30,
        "thresholds": {"commit_p95_seconds": 2, "fts_p95_seconds": 2, "vector_context_p95_seconds": 8, "peak_rss_bytes": 2 * 1024**3},
        "limitation": "本机隔离合成数据；实际硬件单独记录，不等于第二台物理机/真实业务验收",
        "source_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")},
        "status": "running"}
    if prior:
        report["prior_seed_source_hashes"] = prior["source_hashes"]
        report["growth"] = prior["growth"]
        report["resumed_seed"] = True
    def checkpoint(stage):
        report["stage"] = stage
        write_json(output / "result.json", report)
        print(json.dumps({"stage": stage, "time": time.time(), "records": len(expected), **resources()}, ensure_ascii=False), flush=True)
    expected, heads = {}, {}
    try:
        for oid in oids:
            path = root / "research" / oid / "research.json"; path.parent.mkdir(parents=True, exist_ok=resume_seed)
            native = {"schema_version": 1, "research_id": oid, "title": "SYNTHETIC ONLY 规模研究"}
            if resume_seed:
                if json.loads(path.read_text(encoding="utf-8")) != native:
                    raise ValueError("拒绝续写已修改的业务元数据")
            else:
                write_json(path, native)
        if not resume_seed:
            write_json(root / "workspace.json", {"schema_version": 1})
        service = MemoryService(root)
        input_digest = hashlib.sha256()
        # Each owner is committed through the public service, never direct JSON
        # injection. Large single-owner batches exercise its real transaction.
        with synchronous_fts_only():
            for number, oid in enumerate(oids):
                operations = []
                for ordinal in range(number, count, oid_count):
                    value = draft(oid, ordinal)
                    input_digest.update(contracts.canonical_hash(value).encode("ascii"))
                    operations.append({"op": "put_record", "client_key": str(ordinal), "draft": value})
                started = time.perf_counter()
                existing = service.store.read_snapshot(owners.resolve_owner(root, oid)) if resume_seed else {"head": None}
                if existing["head"]:
                    if existing["head"]["generation"] != 1 or len(existing["records"]) != len(operations):
                        raise ValueError("续接发现非初始合成批次")
                    ledger = existing["manifest"]["request_ledger"]
                    if len(ledger) != 1:
                        raise ValueError("续接发现额外提交")
                    request_id, entry = next(iter(ledger.items()))
                    receipt = service.store._receipt(owners.resolve_owner(root, oid), existing, request_id, entry["request_hash"])
                    by_key = {op["client_key"]: op["draft"] for op in operations}
                    for row in receipt["record_results"]:
                        value = existing["records"][row["record_id"]]
                        expected_draft = contracts.validate_record(by_key[row["client_key"]])["record"]
                        if any(value[key] != wanted for key, wanted in expected_draft.items()) or value["content_hash"] != row["content_hash"]:
                            raise ValueError("续接记录与冻结合成输入/提交回执不符")
                else:
                    if resume_seed:
                        from memory import recovery
                        recovery.recover(root, oid, apply=True)
                    receipt = service.commit(request(oid, None, operations))
                heads[oid] = receipt["commit_id"]
                expected.update({row["record_id"]: row["content_hash"] for row in receipt["record_results"]})
                if not existing["head"]:
                    report["growth"].append({"records": len(expected), "commit_seconds": time.perf_counter()-started, **resources()})
                checkpoint("seed")
        report["input_hash"] = input_digest.hexdigest()
        actual = {}
        for view in owners.list_owners(root):
            actual.update({rid: row["content_hash"] for rid, row in service.store.read_snapshot(view)["records"].items()})
        report["integrity"] = {"expected": len(expected), "actual": len(actual), "all_ids_hashes_match": actual == expected,
                               "id_hash_manifest": contracts.canonical_hash(expected)}
        write_json(output / "record-hashes.json", expected)
        checkpoint("integrity")
        if measurement_gate is not None:
            # The coordinating task creates this explicit gate only after other
            # CPU/disk-heavy verification ends. Time spent waiting is not sampled.
            report["measurement_gate"] = str(Path(measurement_gate).resolve())
            checkpoint("waiting_for_measurement_gate")
            while not Path(measurement_gate).is_file():
                time.sleep(1)
        oid = oids[0]; view = owners.resolve_owner(root, oid)
        row = next(iter(service.store.read_snapshot(view)["records"].values()))
        revision, rid = row["revision"], row["record_id"]
        commit_times, fts_times, packet_times = [], [], []
        with synchronous_fts_only():
            for sample in range(warmup + measurements):
                # Preserve this randomly assigned canonical record's original
                # title/keywords/payload; measure only its 1024-byte body change.
                value = {key: deepcopy(row[key]) for key in draft(oid, 0)}
                value["body_markdown"] = chr(65 + sample % 26) * 1024
                value["change_reason"] = "固定 1KiB 变更实测"
                started = time.perf_counter()
                receipt = service.commit(request(oid, heads[oid], [{"op": "put_record", "record_id": rid,
                    "expected_revision": revision, "draft": value}]))
                elapsed = time.perf_counter()-started
                heads[oid] = receipt["commit_id"]; revision += 1
                if sample >= warmup:
                    commit_times.append(elapsed)
                checkpoint("commit " + str(sample + 1))
        report["commit"] = quantiles(commit_times)
        for sample in range(warmup + measurements):
            started = time.perf_counter()
            result = search.search(root, {"query": "规模 sample00000", "purpose": "exploration", "vector": "off", "limit": 6}, record=False)
            elapsed = time.perf_counter()-started
            if sample >= warmup:
                fts_times.append(elapsed)
            if not result["candidates"]:
                raise RuntimeError("固定 FTS 查询错误空结果")
            checkpoint("fts " + str(sample + 1))
        report["fts"] = quantiles(fts_times)
        install_model(root, source_root)
        report["resources_before_model"] = resources()
        started = time.perf_counter()
        result = index.rebuild(root, vector="required")
        report["vector_initial_build_seconds"] = time.perf_counter()-started
        if result["index_status"] != "indexed":
            raise RuntimeError("真实向量初始化失败：" + str(result))
        report["model_manifest_sha256"] = hashlib.sha256((root / "services/qdrant/model-manifest.json").read_bytes()).hexdigest()
        for sample in range(warmup + measurements):
            started = time.perf_counter()
            packet = packets.build_context(service, {"owner_id": oid, "query": "规模 sample00000", "purpose": "exploration", "vector": "required"})
            elapsed = time.perf_counter()-started
            if not packet["manifest"]["items"] or not packet["context_text"]:
                raise RuntimeError("真实向量材料包错误空结果")
            if sample == 0:
                report["vector_context_cold_seconds"] = elapsed
            if sample >= warmup:
                packet_times.append(elapsed)
            checkpoint("vector_context " + str(sample + 1))
        report["vector_context"] = quantiles(packet_times)
        report["resources_end"] = resources()
        report["assertions"] = {"integrity": actual == expected, "commit_p95": report["commit"]["p95"] <= 2,
            "fts_p95": report["fts"]["p95"] <= 2, "vector_context_p95": report["vector_context"]["p95"] <= 8,
            "peak_rss": report["resources_end"].get("peak_rss_bytes", float("inf")) <= 2 * 1024**3}
        report["status"] = "passed" if report["acceptance_scale"] and all(report["assertions"].values()) else "failed"
    except Exception as exc:
        report.update(status="error", error={"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        report["resources_end"] = resources()
        write_json(output / "result.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("distributed", "single"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--records", type=int, default=10000)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--measurements", type=int, default=30)
    parser.add_argument("--measurement-gate", help="数据核对后等待此文件出现，再开始正式计时")
    parser.add_argument("--resume-seed", action="store_true", help="核对原合成输入/回执后继续未完成造数，不覆盖旧记录")
    args = parser.parse_args()
    if min(args.records, args.measurements) < 1 or args.warmup < 0 or (args.scenario == "distributed" and args.records < 100):
        parser.error("样本必须为正，预热非负；distributed 至少 100 条")
    report = run(args.output, scenario=args.scenario, count=args.records, warmup=args.warmup, measurements=args.measurements,
                 measurement_gate=args.measurement_gate, resume_seed=args.resume_seed)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
