"""真实文件事务与 CLI 故障测试；只在隔离中文路径生成合成记录。

测试不将索引占位器视为检索验收。每次故障都核对 HEAD 可见性、旧修订
字节及重试身份，而不是只比较退出码。子进程崩溃使用 os._exit，模拟
未执行 finally 的进程终止，不据此声称任意断电无损。
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "automation/scripts"))
from memory.errors import MemoryError
from memory.service import MemoryService
from memory import owners, recovery
from memory.store import process_identity


def draft(owner_id="RES-TEST"):
    return {"owner_id": owner_id, "kind": "experience", "title": "SYNTHETIC ONLY 预热经验",
            "body_markdown": "中文正文\n保留🙂和换行。", "keywords": ["预热"],
            "sources": [], "provenance_gap": "SYNTHETIC ONLY 测试不具有实验依据",
            "record_reason": "验证不可变修订", "discovery": "owner_only", "sensitivity": "internal",
            "payload": {"problem_structure": "测试漂移", "recommendation": "先核对前置条件",
                        "applicable": ["合成样本 A"], "prohibited": ["不能直接推到 B"],
                        "failure_modes": [], "retry_conditions": [], "claim_refs": [], "claims": []}}


def request(value=None, *, head=None, rid=None, revision=None):
    operation = {"op": "put_record", "draft": value or draft()}
    operation.update({"record_id": rid, "expected_revision": revision} if rid else {"client_key": "experience"})
    return {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": {"kind": "workflow", "id": "synthetic-test"},
            "owner_id": operation["draft"]["owner_id"], "expected_head": head, "operations": [operation], "dry_run": False}


def snapshot_files(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*") if p.is_file()}


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="记忆事务 空格-")
        self.root = Path(self.temp.name).resolve()
        path = self.root / "research/中文 专题/research.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"schema_version": 1, "research_id": "RES-TEST", "title": "SYNTHETIC ONLY"}), encoding="utf-8")
        (self.root / "workspace.json").write_text('{"schema_version":1}', encoding="utf-8")
        self.service = MemoryService(self.root)
        self.native = path.read_bytes()

    def tearDown(self):
        self.temp.cleanup()

    def seed(self):
        req = request()
        receipt = self.service.commit(req)
        return req, receipt, receipt["record_results"][0]["record_id"]

    def assert_code(self, code, action):
        with self.assertRaises(MemoryError) as caught:
            action()
        self.assertEqual(code, caught.exception.code, str(caught.exception))
        return caught.exception

    def test_S01_S02_save_read_and_immutable_revision(self):
        req, receipt, rid = self.seed()
        self.assertEqual(receipt["save_status"], "committed")
        self.assertEqual(receipt["record_results"][0]["status"], "created")
        self.assertEqual(receipt["index_status"], "pending")
        first = self.service.inspect("RES-TEST", record_id=rid)["record"]
        self.assertEqual(first["revision"], 1)
        home = self.root / owners.resolve_owner(self.root, "RES-TEST")["memory_home"]
        old = snapshot_files(home / "commits")
        revised = deepcopy(req["operations"][0]["draft"])
        revised["payload"]["recommendation"] = "先预热 30 分钟（合成限定）"
        result = self.service.commit(request(revised, head=receipt["commit_id"], rid=rid, revision=1))
        second = self.service.inspect("RES-TEST", record_id=rid)["record"]
        self.assertEqual((second["revision"], second["previous_revision"]), (2, 1))
        self.assertEqual(first, self.service.inspect("RES-TEST", 1, record_id=rid)["record"])
        self.assertNotEqual(first["content_hash"], second["content_hash"])
        self.assertEqual(first["created_at"], second["created_at"])
        for name, digest in old.items():
            self.assertEqual(digest, snapshot_files(home / "commits")[name])
        self.assertEqual(self.native, (self.root / "research/中文 专题/research.json").read_bytes())
        self.assertEqual(result["generation"], 2)
        self.assertEqual(result["record_results"][0]["status"], "updated")

    def test_S01_four_kinds_one_commit_and_S06_third_invalid(self):
        from test_memory_contracts import examples
        source = self.root / "original.txt"
        source.write_text("SYNTHETIC ONLY 原始输入\n", encoding="utf-8")
        (self.root / "retrieval").mkdir()
        (self.root / "retrieval/sources.json").write_text(json.dumps({"schema_version": 1, "sources": [
            {"source_id": "SRC-TEST", "path": "original.txt", "enabled": True, "sensitivity": "internal"}]}), encoding="utf-8")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        file_ref = {"target_kind": "file", "target_id": "SRC-TEST", "revision": None,
                    "sha256": digest, "locator": "lines:1-1", "relation": "input"}
        req = request()
        req["operations"] = []
        for index, kind in enumerate(("source", "event", "experience", "map")):
            value = draft()
            value.update(kind=kind, payload=examples()[kind])
            if index == 0:
                value["payload"]["source_ref"] = file_ref
                value["sources"] = [file_ref]
            else:
                value["sources"] = [{"client_key": ("source", "event", "experience")[index-1],
                                      "relation": "derived_from", "locator": "完整记录"}]
            req["operations"].append({"op": "put_record", "client_key": kind, "draft": value})
        bad = deepcopy(req)
        bad["operations"][2]["draft"]["sources"] = [{**file_ref, "target_id": "SRC-ABSENT"}]
        before = snapshot_files(self.root)
        self.assert_code("UNRESOLVED_REFERENCE", lambda: self.service.commit(bad))
        self.assertEqual(before, snapshot_files(self.root))
        receipt = self.service.commit(req)
        current = self.service.inspect("RES-TEST")
        self.assertEqual(len(current["records"]), 4)
        # These drafts omit a version and therefore use the current taxonomy;
        # the separate fixed-Run detail document is the only L1 record kind.
        self.assertEqual({r["level"] for r in current["records"].values()}, {"L0", "L2", "L3", "L4"})
        self.assertEqual({r["revision"] for r in current["records"].values()}, {1})
        self.assertEqual(receipt["generation"], 1)
        self.assertTrue(current["manifest"]["source_checks"])
        home = self.root / current["owner"]["memory_home"]
        self.assertEqual(len(list((home / "commits").iterdir())), 1)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)

    def test_S03_S04_retry_100_and_idempotency_conflict(self):
        req, receipt, rid = self.seed()
        before = snapshot_files(self.root)
        for _ in range(100):
            self.assertEqual(receipt, self.service.commit(req))
        self.assertEqual(before, snapshot_files(self.root))
        wrong = deepcopy(req)
        wrong["operations"][0]["draft"]["body_markdown"] = "另一正文"
        error = self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.service.commit(wrong))
        self.assertEqual(error.details["original_receipt"]["commit_id"], receipt["commit_id"])
        self.assertEqual(before, snapshot_files(self.root))

    def test_S10_preview_and_no_change_receipts(self):
        req = request()
        before = snapshot_files(self.root)
        preview = self.service.validate_draft(req)
        self.assertEqual(before, snapshot_files(self.root))
        self.assertFalse((self.root / "research/中文 专题/memory").exists())
        receipt = self.service.commit(req)
        rid = receipt["record_results"][0]["record_id"]
        self.assertEqual(rid, preview["record_results"][0]["record_id"])
        home = self.root / owners.resolve_owner(self.root, "RES-TEST")["memory_home"]
        committed = snapshot_files(home / "commits")
        no_change = request(head=receipt["commit_id"], rid=rid, revision=1)
        no_change["operations"][0]["draft"]["change_reason"] = "仅操作备注改变"
        repeated = self.service.commit(no_change)
        self.assertEqual(repeated["save_status"], "no_change")
        for _ in range(100):
            self.assertEqual(repeated, self.service.commit(no_change))
        self.assertEqual(committed, snapshot_files(home / "commits"))
        self.assertEqual(len(list((home / "request-receipts").glob("*.json"))), 1)

    def test_C05_S06_batch_resolves_client_keys_or_rejects_all(self):
        req = request()
        second = draft()
        second["sources"] = [{"client_key": "experience", "relation": "derived_from", "locator": "完整经验"}]
        second["provenance_gap"] = None
        req["operations"].append({"op": "put_record", "client_key": "second", "draft": second})
        wrong = deepcopy(req)
        wrong["operations"][1]["draft"]["sources"][0]["client_key"] = "absent"
        before = snapshot_files(self.root)
        self.assert_code("UNRESOLVED_REFERENCE", lambda: self.service.commit(wrong))
        self.assertEqual(before, snapshot_files(self.root))
        result = self.service.commit(req)
        records = self.service.inspect("RES-TEST")["records"]
        self.assertEqual(len(records), 2)
        second_id = result["record_results"][1]["record_id"]
        self.assertNotIn("client_key", json.dumps(records[second_id]))
        self.assertEqual(records[second_id]["sources"][0]["revision"], 1)

    def test_support_cycles_rejected_without_writes(self):
        req = request()
        req["operations"][0]["draft"]["sources"] = [{"client_key": "experience", "relation": "supports", "locator": "自身"}]
        before = snapshot_files(self.root)
        self.assert_code("INVALID_SCHEMA", lambda: self.service.commit(req))
        self.assertEqual(before, snapshot_files(self.root))

    def test_owner_reference_cannot_lower_sensitivity(self):
        native = self.root / "research/中文 专题/research.json"
        for classification in ("restricted", "confidential", "internal"):
            data = json.loads(native.read_text(encoding="utf-8"))
            data["sensitivity"] = classification
            native.write_text(json.dumps(data), encoding="utf-8")
            import evidence
            digest = evidence.EvidenceGraph(self.root).nodes["RES-TEST"]["fingerprint"]
            value = draft()
            value["sensitivity"] = "public"
            value["sources"] = [{"target_kind": "owner", "target_id": "RES-TEST", "revision": None,
                                  "sha256": digest, "locator": "metadata", "relation": "background"}]
            before = snapshot_files(self.root)
            self.assert_code("ACCESS_DENIED", lambda: self.service.validate_draft(request(value)))
            self.assertEqual(before, snapshot_files(self.root))

    def test_S07_fault_windows_keep_previous_snapshot(self):
        req, receipt, rid = self.seed()
        original = self.service.inspect("RES-TEST")
        home = self.root / original["owner"]["memory_home"]
        committed_hashes = snapshot_files(home / "commits")
        for point in ("write", "flush", "after_rename", "before_head"):
            with self.subTest(point=point):
                before_recovery = recovery.inspect(self.root, "RES-TEST")
                change = draft()
                change["body_markdown"] = "失败窗口 " + point
                update = request(change, head=receipt["commit_id"], rid=rid, revision=1)
                def fail(actual):
                    if actual == point:
                        raise OSError("SYNTHETIC ONLY injected " + point)
                service = MemoryService(self.root, fault=fail)
                failure = self.assert_code("STORAGE_ERROR", lambda: service.commit(update))
                self.assertEqual(failure.details["save_status"], "not_committed")
                self.assertEqual(original["records"], self.service.inspect("RES-TEST")["records"])
                self.assertEqual(original["head"], self.service.inspect("RES-TEST")["head"])
                classified = recovery.inspect(self.root, "RES-TEST")
                category = "uncommitted_staging" if point in {"write", "flush"} else "unreachable_commits"
                self.assertTrue(set(classified[category]) - set(before_recovery[category]), classified)
                self.assertEqual(classified["action"], "inspect_only")
                current_hashes = snapshot_files(home / "commits")
                for name, digest in committed_hashes.items():
                    self.assertEqual(current_hashes[name], digest, name)
        retry = self.service.commit(update)
        self.assertEqual(retry["generation"], 2)
        # Old interrupted work remains classified; recovery must never publish
        # it over a newer successful HEAD or silently delete its evidence.
        new_head = self.service.inspect("RES-TEST")["head"]
        recovery.recover(self.root, "RES-TEST", apply=True)
        self.assertEqual(self.service.inspect("RES-TEST")["head"], new_head)

    def test_S08_process_exit_after_head_replays_ledger(self):
        req = request()
        input_path = self.root / "request.json"
        input_path.write_text(json.dumps(req), encoding="utf-8")
        program = """import json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from memory.service import MemoryService
def fail(point):
    if point=='after_head': os._exit(73)
MemoryService(Path(sys.argv[2]),fault=fail).commit(json.loads(Path(sys.argv[3]).read_text()))
"""
        child = subprocess.run([sys.executable, "-c", program, str(ROOT / "automation/scripts"), str(self.root), str(input_path)], capture_output=True, text=True)
        self.assertEqual(child.returncode, 73, child.stderr)
        view = self.service.inspect("RES-TEST")
        self.assertEqual(len(view["records"]), 1)
        receipt = self.service.commit(req)
        self.assertEqual(receipt["commit_id"], view["head"]["commit_id"])
        recovered = recovery.recover(self.root, "RES-TEST", apply=True)
        self.assertEqual(recovered["action"], "archived_exited_lock")
        self.assertEqual(view["records"], self.service.inspect("RES-TEST")["records"])
        from memory import index
        before_sync = snapshot_files(self.root / owners.resolve_owner(self.root, "RES-TEST")["memory_home"] / "commits")
        index.reconcile(self.root, "RES-TEST", vector="off")
        state = index.status(self.root, "RES-TEST")
        self.assertEqual(state["index_details"]["fts"], "indexed")
        self.assertEqual(state["index_details"]["indexed_generation"], view["head"]["generation"])
        self.assertEqual(before_sync, snapshot_files(self.root / owners.resolve_owner(self.root, "RES-TEST")["memory_home"] / "commits"))

    def test_S11_corruption_is_not_repaired(self):
        _, receipt, rid = self.seed()
        owner = owners.resolve_owner(self.root, "RES-TEST")
        path = self.root / owner["memory_home"] / f"commits/{receipt['commit_id']}/records/{rid}.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["body_markdown"] = "已篡改"
        path.write_text(json.dumps(value), encoding="utf-8")
        damaged = path.read_bytes()
        self.assert_code("INTEGRITY_ERROR", lambda: self.service.inspect("RES-TEST"))
        self.assertEqual(damaged, path.read_bytes())

    def test_S11_manifest_corruption_is_rejected(self):
        _, receipt, _ = self.seed()
        owner = owners.resolve_owner(self.root, "RES-TEST")
        path = self.root / owner["memory_home"] / f"commits/{receipt['commit_id']}/manifest.json"
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b'"generation":1', b'"generation":9'))
        damaged = path.read_bytes()
        self.assertNotEqual(raw, damaged)
        self.assert_code("INTEGRITY_ERROR", lambda: self.service.inspect("RES-TEST"))
        self.assertEqual(damaged, path.read_bytes())

    @unittest.skipUnless(os.name == "nt", "真实 Windows junction 测试")
    def test_S11_windows_junction_cannot_redirect_store(self):
        self.seed()
        outside = self.root / "external-sentinel"
        outside.mkdir()
        (outside / "sentinel.txt").write_text("SYNTHETIC ONLY", encoding="utf-8")
        link = self.root / "research/中文 专题/memory/redirect"
        made = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        try:
            before = snapshot_files(outside)
            owner = owners.resolve_owner(self.root, "RES-TEST")
            self.assert_code("UNSAFE_PATH", lambda: self.service.store.path(owner, "redirect/new.json"))
            self.assertEqual(before, snapshot_files(outside))
        finally:
            # Remove only the test junction itself, never recurse through its target.
            os.rmdir(link)

    def test_S12_active_and_unknown_locks_not_removed(self):
        self.seed()
        owner = owners.resolve_owner(self.root, "RES-TEST")
        path = self.root / owner["memory_home"] / "write.lock"
        for value in ({"pid": os.getpid(), "start_identity": process_identity(os.getpid()), "owner_id": "RES-TEST"},
                      {"pid": -1, "owner_id": "RES-TEST"}, {}, []):
            path.write_text(json.dumps(value), encoding="utf-8")
            before = path.read_bytes()
            self.assert_code("LOCKED", lambda: recovery.recover(self.root, "RES-TEST", apply=True))
            self.assertEqual(before, path.read_bytes())
            self.assertNotEqual(recovery.inspect(self.root, "RES-TEST")["lock_state"], "absent")

    def test_S05_two_processes_cannot_lose_update(self):
        _, receipt, rid = self.seed()
        processes = []
        program = """import json,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from memory.service import MemoryService
from memory.errors import MemoryError
root=Path(sys.argv[2]); marker=root/sys.argv[3]
req=json.loads((root/(sys.argv[3]+'.json')).read_text())
marker.write_text('ready')
while not (root/'go').exists(): time.sleep(.01)
try:
    result=MemoryService(root).commit(req)
    print(json.dumps({'status':result['save_status']}))
except MemoryError as exc:
    print(json.dumps({'error':exc.code}))
"""
        try:
            for index in range(2):
                value = draft()
                value["body_markdown"] = f"writer-{index}"
                req = request(value, head=receipt["commit_id"], rid=rid, revision=1)
                (self.root / f"ready-{index}.json").write_text(json.dumps(req), encoding="utf-8")
                processes.append(subprocess.Popen([sys.executable, "-c", program, str(ROOT / "automation/scripts"),
                                                    str(self.root), f"ready-{index}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            import time
            deadline = time.monotonic() + 20
            while not all((self.root / f"ready-{i}").exists() for i in range(2)):
                if time.monotonic() > deadline:
                    self.fail("子进程未到达并发屏障")
                time.sleep(.01)
            (self.root / "go").write_text("go")
            results = []
            for child in processes:
                out, error = child.communicate(timeout=20)
                self.assertEqual(child.returncode, 0, error)
                results.append(json.loads(out))
            self.assertEqual(sum(r.get("status") == "committed" for r in results), 1, results)
            self.assertEqual(sum(r.get("error") in {"VERSION_CONFLICT", "LOCKED"} for r in results), 1, results)
            losing = next(i for i, r in enumerate(results) if "error" in r)
            loser_request = json.loads((self.root / f"ready-{losing}.json").read_text())
            conflict = self.assert_code("VERSION_CONFLICT", lambda: self.service.commit(loser_request))
            actual_head = self.service.inspect("RES-TEST")["head"]
            self.assertEqual(conflict.details["current_head"], actual_head)
            self.assertNotEqual(conflict.details["current_head"]["commit_id"], loser_request["expected_head"])
            current = self.service.inspect("RES-TEST", record_id=rid)["record"]
            self.assertEqual(current["revision"], 2)
            self.assertEqual(current["body_markdown"], f"writer-{1-losing}")
            self.assertNotEqual(current["body_markdown"], loser_request["operations"][0]["draft"]["body_markdown"])
        finally:
            for child in processes:
                if child.poll() is None:
                    child.kill()
                    child.communicate()

    @unittest.skipUnless(os.name == "nt", "真实 Windows 文件共享占用测试")
    def test_S12_real_windows_head_sharing_denial(self):
        _, receipt, rid = self.seed()
        home = self.root / owners.resolve_owner(self.root, "RES-TEST")["memory_home"]
        program = """import ctypes,sys
from ctypes import wintypes
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
k.CreateFileW.restype=wintypes.HANDLE
k.CloseHandle.argtypes=[wintypes.HANDLE]
h=k.CreateFileW(sys.argv[1],0x80000000,1,None,3,0,None)
if h==wintypes.HANDLE(-1).value: raise ctypes.WinError(ctypes.get_last_error())
print('locked',flush=True)
sys.stdin.readline()
k.CloseHandle(h)
"""
        child = subprocess.Popen([sys.executable, "-c", program, str(home / "HEAD.json")],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            value = draft()
            value["body_markdown"] = "占用释放后保存"
            req = request(value, head=receipt["commit_id"], rid=rid, revision=1)
            old = (home / "HEAD.json").read_bytes()
            self.assert_code("STORAGE_ERROR", lambda: self.service.commit(req))
            self.assertEqual(old, (home / "HEAD.json").read_bytes())
            self.assertEqual(self.service.inspect("RES-TEST", record_id=rid)["record"]["revision"], 1)
            child.communicate("release\n", timeout=15)
            result = self.service.commit(req)
            self.assertEqual(result["generation"], 2)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate()

    def test_cli_json_success_pending_and_invalid_input(self):
        from memory.cli import execute
        path = self.root / "request.json"
        path.write_text(json.dumps(request()), encoding="utf-8")
        result, code = execute(self.root, ["commit", "--request", str(path)])
        self.assertEqual((code, result["save_status"]), (3, "committed"))
        result, code = execute(self.root, ["inspect", "RES-TEST"])
        self.assertEqual(code, 0)
        self.assertEqual(len(result["records"]), 1)
        result, code = execute(self.root, ["commit"])
        self.assertEqual((code, result["error"]["code"]), (2, "INVALID_ARGUMENT"))
        path.write_text("broken JSON", encoding="utf-8")
        result, code = execute(self.root, ["commit", "--request", str(path)])
        self.assertEqual((code, result["error"]["code"]), (2, "INVALID_ARGUMENT"))


if __name__ == "__main__":
    unittest.main()
