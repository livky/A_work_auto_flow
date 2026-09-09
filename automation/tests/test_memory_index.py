"""SYNTHETIC ONLY：真实 SQLite/规范存储检索回归与离线能力边界。

确定性向量适配器只验证独立水位/故障补偿，不能替代真实 384 维模型评价。
所有创建、原件变化和索引删除均限制在测试 TemporaryDirectory 中。
"""
from copy import deepcopy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch
import importlib.util
import os
import shutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "automation/scripts"))
from memory import index, search, evaluation, owners
from memory.errors import MemoryError
from memory.service import MemoryService
from memory_fixture import materialize, snapshot, build_verified_legacy


def draft(owner_id="RES-A", *, title="SYNTHETIC ONLY 预热 零点漂移", body="先预热再比较偏差", discovery="workspace_summary"):
    return {"owner_id": owner_id, "kind": "experience", "title": title, "body_markdown": body,
        "keywords": ["预热", "漂移"], "sources": [], "provenance_gap": "SYNTHETIC ONLY 软件检索测试，无真实实验",
        "record_reason": "SYNTHETIC ONLY 验证局部结果可检索", "discovery": discovery, "sensitivity": "internal",
        "payload": {"problem_structure": "合成温漂", "recommendation": "核对条件再预热", "applicable": ["仅样本 A"],
                    "prohibited": ["不能直接推广样本 B"], "failure_modes": [], "retry_conditions": [], "claim_refs": [], "claims": []}}


def request(value, *, head=None, rid=None, revision=None, key="record"):
    op = {"op": "put_record", "draft": deepcopy(value)}
    op.update({"record_id": rid, "expected_revision": revision} if rid else {"client_key": key})
    return {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": {"kind": "workflow", "id": "synthetic-index-test"},
            "owner_id": value["owner_id"], "expected_head": head, "operations": [op]}


class DeterministicVectorBackend:
    """测试专用持久字典：只验水位/点身份，不生成或冒充语义向量。"""
    storage = {}
    collection = "synthetic_only_vector_protocol"

    def __init__(self, root):
        self.entries = self.storage.setdefault(str(Path(root).resolve()), {})

    def close(self):
        pass

    def sync_owner(self, owner_id, entries, *, fault=lambda _point: None):
        old = {eid for eid, row in self.entries.items() if row["owner_id"] == owner_id}
        for eid in old - {row["entry_id"] for row in entries}:
            del self.entries[eid]
        for row in entries:
            fault("vector_upsert")
            self.entries[row["entry_id"]] = {**deepcopy(row), "vector_id": hashlib.sha256(row["signature"].encode()).hexdigest()}
        return {"collection": self.collection, "points": len(self.entries)}

    def search(self, query, allowed_ids):
        return [{**row, "vector_score": 0.9} for _, row in sorted(self.entries.items()) if row["canonical_id"] in allowed_ids]


class MemoryIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="记忆检索 合成-")
        self.root = Path(self.temp.name)
        for oid in ("RES-A", "RES-B"):
            path = self.root / "research" / oid / "research.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"schema_version": 1, "research_id": oid, "title": "SYNTHETIC ONLY " + oid,
                "sensitivity": "internal", "claims": [], "dependencies": []}), encoding="utf-8")
        (self.root / "workspace.json").write_text('{"schema_version":1}', encoding="utf-8")
        self.service = MemoryService(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, value=None, *, head=None, rid=None, revision=None):
        receipt = self.service.commit(request(value or draft(), head=head, rid=rid, revision=revision))
        return receipt, receipt["record_results"][0]["record_id"]

    def query(self, text="预热", **options):
        return search.search(self.root, {"query": text, "purpose": "exploration", "vector": "off", **options}, record=False)

    def assert_code(self, code, callback):
        with self.assertRaises(MemoryError) as caught:
            callback()
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def add_representations(self, target_id, head, *, owner_id="RES-A"):
        operations = []
        for slot in ("title", "result", "problem", "trigger", "failure", "boundary"):
            ref = {"target_kind": "record", "target_id": target_id, "revision": 1, "sha256": None, "locator": "record", "relation": "derived_from"}
            value = {"owner_id": owner_id, "kind": "representation", "title": "SYNTHETIC ONLY " + slot, "body_markdown": "",
                "keywords": [], "sources": [ref], "provenance_gap": None, "record_reason": "SYNTHETIC ONLY 多表示测试",
                "discovery": "workspace_summary", "sensitivity": "internal", "payload": {"target": ref, "slot": slot,
                    "text": "预热 零点漂移 " + slot, "boundary_refs": []}}
            operations.append({"op": "put_record", "client_key": slot, "draft": value})
        req = {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": {"kind": "workflow", "id": "synthetic-index-test"},
               "owner_id": owner_id, "expected_head": head, "operations": operations}
        return self.service.commit(req), req

    def test_I01_eight_researches_legacy_levels_project_without_identity_changes(self):
        with tempfile.TemporaryDirectory(prefix="八类 索引-") as temporary:
            fixture = materialize(Path(temporary) / "workspace", isolation_root=temporary)
            service = MemoryService(fixture.root)
            mapping = {}
            for theme in ("THERMAL", "PRESSURE", "RETRY", "CACHE", "VIBRATION", "UNITS", "OCR", "REPEAT"):
                keys = ["MEM-SRC-" + theme, "MEM-EXP-" + theme, "MEM-MAP-" + theme]
                receipt = service.commit(fixture.request(keys))
                mapping.update({row["client_key"]: row["record_id"] for row in receipt["record_results"]})
            rebuilt = index.rebuild(fixture.root, vector="off")
            self.assertEqual(rebuilt["index_status"], "indexed")
            for level, kind in (("L2", "event"), ("L3", "experience"), ("L4", "map")):
                result = search.search(fixture.root, {"query": "预热", "purpose": "exploration", "vector": "off", "levels": [level],
                    "kinds": [kind], "stage": "wide", "limit": 100}, record=False)
                self.assertTrue(result["candidates"], (level, result["missing"]))
                self.assertTrue(all(row["level"] == level for row in result["candidates"]))
            source_id = mapping["MEM-SRC-THERMAL"]
            raw = search.search(fixture.root, {"query": source_id, "purpose": "exploration", "vector": "off",
                "retrieval_mode": "trace", "levels": ["L0"], "stage": "wide"}, record=False)
            self.assertEqual([row["canonical_id"] for row in raw["candidates"]], [source_id])
            result = search.search(fixture.root, {"query": "预热 零点漂移", "purpose": "exploration", "vector": "off",
                "owner_id": "RES-SYN-PRESSURE", "kinds": ["experience"], "stage": "wide", "limit": 100}, record=False)
            self.assertIn(mapping["MEM-EXP-THERMAL"], [row["canonical_id"] for row in result["candidates"]])
            with closing(index.connect(fixture.root)) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_records WHERE canonical_id='RUN-SYN-THERMAL'").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_records WHERE canonical_id='CLM-SYN-THERMAL'").fetchone()[0], 1)

    def test_I02_six_slots_and_duplicate_channel_collapse(self):
        receipt, rid = self.save()
        reps, req = self.add_representations(rid, receipt["commit_id"])
        index.sync_owner(self.root, "RES-A", vector="off")
        with closing(index.connect(self.root)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_representations WHERE target_id=?", (rid,)).fetchone()[0], 6)
        result = self.query()
        self.assertEqual([row["canonical_id"] for row in result["candidates"]].count(rid), 1)
        trigger = next(row for row in reps["record_results"] if row["client_key"] == "trigger")
        value = next(op["draft"] for op in req["operations"] if op["client_key"] == "trigger")
        value["payload"]["text"] = "\n".join("预热 零点漂移 同义表达 " + str(i) for i in range(10))
        self.service.commit(request(value, head=reps["commit_id"], rid=trigger["record_id"], revision=1))
        index.sync_owner(self.root, "RES-A", vector="off")
        with closing(index.connect(self.root)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_representations WHERE target_id=?", (rid,)).fetchone()[0], 6)
        before = search.rrf({"fts": ["A", "B"], "vector": ["B", "A"]})
        after = search.rrf({"fts": ["A"] * 10 + ["B"], "vector": ["B", "A"] * 6})
        self.assertEqual([(r["canonical_id"], r["score"]) for r in before], [(r["canonical_id"], r["score"]) for r in after])
        self.assertEqual([row["rank"] for row in search.collapse_channel(["A", "A", "B"])], [1, 2])

    def test_I03_rrf_fixed_numbers_and_tie_order(self):
        rows = search.rrf({"fts": ["A", "B", "C"], "vector": ["B", "C", "A"]})
        scores = {row["canonical_id"]: row["score"] for row in rows}
        self.assertAlmostEqual(scores["A"], 1 / 61 + 1 / 63, delta=1e-12)
        self.assertAlmostEqual(scores["B"], 1 / 62 + 1 / 61, delta=1e-12)
        self.assertLess([r["canonical_id"] for r in rows].index("B"), [r["canonical_id"] for r in rows].index("A"))
        tie = search.rrf({"fts": ["B", "A"], "vector": ["A", "B"]})
        self.assertEqual([r["canonical_id"] for r in tie], ["A", "B"])

    def test_I04_incremental_owner_and_stale_representation(self):
        first, rid = self.save()
        reps, _ = self.add_representations(rid, first["commit_id"])
        self.save(draft("RES-B", title="SYNTHETIC ONLY 另一个对象"))
        index.reconcile(self.root, vector="auto", backend_factory=DeterministicVectorBackend)
        with closing(index.connect(self.root)) as db:
            other = dict(db.execute("SELECT * FROM memory_index_state WHERE owner_id='RES-B'").fetchone())
        vectors_before = deepcopy(DeterministicVectorBackend(self.root).entries)
        value = draft(body="新修订需要重新核对样本，清除旧表示")
        self.save(value, head=reps["commit_id"], rid=rid, revision=1)
        result = index.sync_owner(self.root, "RES-A", vector="auto", backend_factory=DeterministicVectorBackend)
        self.assertEqual(result["fts"]["indexed_generation"], 3)
        with closing(index.connect(self.root)) as db:
            self.assertEqual(dict(db.execute("SELECT * FROM memory_index_state WHERE owner_id='RES-B'").fetchone()), other)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_representations WHERE active=1").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_entries WHERE representation_id IS NOT NULL").fetchone()[0], 0)
        vectors_after = DeterministicVectorBackend(self.root).entries
        self.assertEqual({k: v for k, v in vectors_before.items() if v["owner_id"] == "RES-B"},
                         {k: v for k, v in vectors_after.items() if v["owner_id"] == "RES-B"})

    def test_I05_visibility_shrinks_before_stale_index_refresh(self):
        receipt, rid = self.save()
        index.sync_owner(self.root, "RES-A", vector="off")
        self.assertIn(rid, [row["canonical_id"] for row in self.query(owner_id="RES-B")["candidates"]])
        # 模拟 HEAD 已成功发布但派生同步没有运行，查询必须回源拦截旧值。
        with patch.object(index, "sync_owner", return_value={"index_status": "pending"}):
            self.save(draft(discovery="owner_only"), head=receipt["commit_id"], rid=rid, revision=1)
        result = self.query(owner_id="RES-B")
        self.assertNotIn(rid, [row["canonical_id"] for row in result["candidates"]])
        index.sync_owner(self.root, "RES-A", vector="off")
        self.assertIn(rid, [row["canonical_id"] for row in self.query(owner_id="RES-A")["candidates"]])
        self.assertNotIn(rid, [row["canonical_id"] for row in self.query(owner_id="RES-B")["candidates"]])

    def test_I05_exclusion_wins_over_include_and_full(self):
        _, rid = self.save()
        result = self.query(include_ids=[rid], full_ids=[rid], exclude_ids=[rid])
        self.assertEqual(result["candidates"], [])
        self.assertIn({"canonical_id": rid, "reason": "explicit_exclude"}, result["missing"])
        self.assertEqual(result["selection"]["full_ids"], [rid])

    def test_I05_I07_source_revocation_and_missing_original_remove_cached_text(self):
        source = self.root / "synthetic-original.txt"
        source.write_text("SYNTHETIC ONLY 原始预热测量说明", encoding="utf-8")
        registry = self.root / "retrieval/sources.json"
        registry.parent.mkdir()
        registered = {"schema_version": 1, "sources": [{"source_id": "SRC-TEST", "path": source.name,
            "enabled": True, "sensitivity": "internal"}]}
        registry.write_text(json.dumps(registered), encoding="utf-8")
        value = draft()
        value.update(sources=[{"target_kind": "file", "target_id": "SRC-TEST", "revision": None,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "locator": "完整原文", "relation": "input"}], provenance_gap=None)
        lower = deepcopy(value)
        lower["sensitivity"] = "public"
        self.assert_code("ACCESS_DENIED", lambda: self.service.commit(request(lower)))
        _, rid = self.save(value)
        index.sync_owner(self.root, "RES-A", vector="auto", backend_factory=DeterministicVectorBackend)
        home = self.root / owners.resolve_owner(self.root, "RES-A")["memory_home"]
        before = snapshot(home)
        registered["sources"][0]["enabled"] = False
        registry.write_text(json.dumps(registered), encoding="utf-8")
        # 索引仍含昨日正文；此时查询必须回源拒绝，不能等后台同步才隐藏。
        self.assertEqual(self.query()["candidates"], [])
        removed = index.sync_owner(self.root, "RES-A", vector="auto", backend_factory=DeterministicVectorBackend)
        self.assertTrue(any(row["reason"] == "access_denied" for row in removed["missing"]))
        with closing(index.connect(self.root)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_entries WHERE canonical_id=?", (rid,)).fetchone()[0], 0)
        self.assertFalse(DeterministicVectorBackend(self.root).entries)
        registered["sources"][0]["enabled"] = True
        registry.write_text(json.dumps(registered), encoding="utf-8")
        index.rebuild(self.root, vector="off")
        self.assertTrue(self.query()["candidates"])
        source.unlink()
        rebuilt = index.rebuild(self.root, vector="off")
        self.assertTrue(any(row["reason"] == "unavailable" for result in rebuilt["owners"] for row in result["missing"]))
        self.assertEqual(self.query()["candidates"], [])
        self.assertEqual(snapshot(home), before)

    def test_fixed_old_provenance_cannot_bypass_revoked_original_in_search_or_history(self):
        source = self.root / "synthetic-versioned-source.txt"
        source.write_text("SYNTHETIC ONLY 固定旧来源风险", encoding="utf-8")
        registry = self.root / "retrieval/sources.json"; registry.parent.mkdir()
        registration = {"schema_version": 1, "sources": [{"source_id": "SRC-OLD", "path": source.name,
            "enabled": True, "sensitivity": "internal"}]}
        registry.write_text(json.dumps(registration), encoding="utf-8")
        base = draft(); base["sources"] = [{"target_kind": "file", "target_id": "SRC-OLD", "revision": None,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "locator": "完整", "relation": "derived_from"}]
        base["provenance_gap"] = None
        first, bid = self.save(base)
        derived = draft(); derived["body_markdown"] = "SYNTHETIC ONLY 固定旧来源风险"
        derived["sources"] = [{"target_kind": "record", "target_id": bid, "revision": 1,
            "sha256": None, "locator": "正文", "relation": "derived_from"}]
        derived["provenance_gap"] = None
        second, aid = self.save(derived, head=first["commit_id"])
        third, _ = self.save(draft(), head=second["commit_id"], rid=bid, revision=1)
        # B r2 no longer names the original. A still fixes B r1, so that older
        # provenance must remain subject to the source's current permission.
        registration["sources"][0]["enabled"] = False
        registry.write_text(json.dumps(registration), encoding="utf-8")
        for historical in (False, True):
            result = self.query("固定旧来源风险", include_ids=[aid], full_ids=[aid], history=historical)
            self.assertNotIn(aid, [row["canonical_id"] for row in result["candidates"]])
            self.assertNotIn("固定旧来源风险", " ".join(row["snippet"] for row in result["candidates"]))
            self.assertTrue(any(row.get("canonical_id") == aid and row.get("reason") == "access_denied" for row in result["missing"]))
        clean = draft(); clean["body_markdown"] = "SYNTHETIC ONLY 新版本已移除旧来源正文"
        self.save(clean, head=third["commit_id"], rid=aid, revision=1)
        history = self.query("固定旧来源风险", history=True)
        self.assertNotIn("固定旧来源风险", " ".join(row["snippet"] for row in history["candidates"]))
        self.assertFalse(any(row["canonical_id"] == aid and row["revision"] == 1 for row in history["candidates"]))

    def test_I06_off_auto_and_required_without_model(self):
        _, rid = self.save()
        index.sync_owner(self.root, "RES-A", vector="off")
        self.assertIn(rid, [row["canonical_id"] for row in self.query()["candidates"]])
        auto = search.search(self.root, {"query": "预热", "purpose": "exploration", "vector": "auto"}, record=False)
        self.assertIn(rid, [row["canonical_id"] for row in auto["candidates"]])
        self.assertTrue(auto["degradation"])
        self.assert_code("CAPABILITY_UNAVAILABLE", lambda: search.search(self.root,
            {"query": "预热", "purpose": "exploration", "vector": "required"}, record=False))

    def test_I07_rebuild_preserves_canonical_and_old_tables(self):
        _, rid = self.save()
        home = self.root / owners.resolve_owner(self.root, "RES-A")["memory_home"]
        canonical = snapshot(home)
        with closing(index.connect(self.root)) as db:
            db.execute("CREATE TABLE docs(id TEXT PRIMARY KEY, marker TEXT)")
            db.execute("INSERT INTO docs VALUES('SYNTHETIC-OLD','preserve')")
            db.commit()
        index.rebuild(self.root, vector="off")
        with closing(index.connect(self.root)) as db:
            self.assertEqual(tuple(db.execute("SELECT * FROM docs").fetchone()), ("SYNTHETIC-OLD", "preserve"))
        before = {row["canonical_id"] for row in self.query()["candidates"]}
        index.database_path(self.root).unlink()  # 仅隔离临时派生数据库，无递归删除。
        index.rebuild(self.root, vector="off")
        self.assertEqual({row["canonical_id"] for row in self.query()["candidates"]}, before)
        self.assertEqual(snapshot(home), canonical)
        self.assertIn(rid, before)

    def test_reconcile_repairs_physically_missing_fts_rows(self):
        _, rid = self.save()
        index.sync_owner(self.root, "RES-A", vector="off")
        with closing(index.connect(self.root)) as db:
            db.execute("DELETE FROM memory_fts")
            db.commit()
        repaired = index.reconcile(self.root, "RES-A", vector="off")
        self.assertEqual(repaired["owners"][0]["fts"]["changed_entries"], 1)
        self.assertIn(rid, [row["canonical_id"] for row in self.query()["candidates"]])

    def test_formal_projection_and_legacy_fulltext_use_one_claim_identity(self):
        with tempfile.TemporaryDirectory(prefix="正式检索 合成-") as temporary:
            proof = build_verified_legacy(Path(temporary) / "workspace", isolation_root=temporary)
            root = Path(proof["root"])
            import retrieval
            retrieval.index(root)
            index.rebuild(root, vector="off")
            request = {"query": "测试引用", "purpose": "exploration", "vector": "off", "limit": 100, "stage": "wide"}
            result = search.search(root, request, record=False)
            run = next(row for row in result["candidates"] if row["canonical_id"] == "RUN-SYNTHETIC")
            self.assertIn("legacy_fts", run["rank_channels"])
            formal = search.search(root, {"query": "偏移", "purpose": "formal", "scope": "synthetic:only", "vector": "off"}, record=False)
            self.assertEqual([row["canonical_id"] for row in formal["candidates"]], ["CLM-SYNTHETIC"])
            self.assertTrue(formal["candidates"][0]["effective_validity"])
            import evidence
            evidence.review_claim(root, "CLM-SYNTHETIC", "retracted", "synthetic-test", "SYNTHETIC ONLY 撤回测试",
                evidence="runs/synthetic-base/result.txt", scope="synthetic:only")
            withdrawn = search.search(root, {"query": "偏移", "purpose": "formal", "scope": "synthetic:only", "vector": "off"}, record=False)
            self.assertEqual(withdrawn["candidates"], [])
            self.assertTrue(withdrawn["rejected"])

    def test_I09_history_is_explicit_and_does_not_pollute_current(self):
        first, rid = self.save(draft(body="独有旧词 星云旧稿", title="SYNTHETIC ONLY 旧实验"))
        second = draft(body="全新结果 海洋新稿", title="SYNTHETIC ONLY 新实验")
        self.save(second, head=first["commit_id"], rid=rid, revision=1)
        index.sync_owner(self.root, "RES-A", vector="off")
        self.assertNotIn(rid, [row["canonical_id"] for row in self.query("星云旧稿")["candidates"]])
        history = self.query("星云旧稿", history=True)
        result = next(row for row in history["candidates"] if row["canonical_id"] == rid)
        self.assertEqual(result["revision"], 1)
        self.assertTrue(result["historical"])
        self.assertNotIn(rid, [row["canonical_id"] for row in self.query("星云旧稿")["candidates"]])

    def test_S09_fts_and_vector_failures_reconcile_without_business_revision(self):
        def fts_failure(point):
            if point == "fts_entry":
                raise OSError("SYNTHETIC ONLY FTS injected failure")
        original_sync = index.sync_owner
        with patch.object(index, "sync_owner", side_effect=lambda root, oid, generation=None:
                          original_sync(root, oid, generation, vector="off", fault=fts_failure)):
            receipt, rid = self.save()
        self.assertEqual(receipt["save_status"], "committed")
        self.assertEqual(receipt["error"]["code"], "INDEX_PENDING")
        self.assertEqual(receipt["index_details"]["fts"], "failed")
        home = self.root / owners.resolve_owner(self.root, "RES-A")["memory_home"]
        before = snapshot(home)
        self.assertEqual(self.service.inspect("RES-A", record_id=rid)["record"]["revision"], 1)
        fixed = index.reconcile(self.root, "RES-A", vector="off")
        self.assertEqual(fixed["index_status"], "indexed")
        def vector_failure(point):
            if point == "vector_upsert":
                raise OSError("SYNTHETIC ONLY vector injected failure")
        failed = index.sync_owner(self.root, "RES-A", vector="auto", fault=vector_failure, backend_factory=DeterministicVectorBackend)
        self.assertEqual(failed["fts"]["status"], "indexed")
        self.assertEqual(failed["index_status"], "pending")
        fixed = index.reconcile(self.root, "RES-A", vector="auto", backend_factory=DeterministicVectorBackend)
        self.assertEqual(fixed["index_status"], "indexed")
        self.assertEqual(fixed["owners"][0]["vector"]["indexed_generation"], 1)
        self.assertEqual(snapshot(home), before)
        self.assertEqual(receipt["save_status"], "committed")

    def test_removed_owner_vector_failure_remains_pending_until_reconcile(self):
        self.save()
        index.reconcile(self.root, vector="auto", backend_factory=DeterministicVectorBackend)
        # Move only synthetic fixture data outside the catalog's research root;
        # preserve its canonical files so this tests derived deletion alone.
        (self.root / "research" / "RES-A").rename(self.root / "detached-owner")
        def unavailable(_root):
            raise RuntimeError("synthetic vector backend unavailable")
        failed = index.reconcile(self.root, vector="auto", backend_factory=unavailable)
        self.assertEqual(failed["index_status"], "pending")
        self.assertEqual(failed["pending_removals"], ["RES-A"])
        repaired = index.reconcile(self.root, vector="auto", backend_factory=DeterministicVectorBackend)
        self.assertEqual(repaired["pending_removals"], [])
        self.assertEqual(repaired["index_status"], "indexed")
        self.assertFalse(DeterministicVectorBackend(self.root).entries)
        self.assertTrue((self.root / "detached-owner" / "research.json").is_file())

    def test_status_and_rebuild_preview_are_read_only(self):
        before = snapshot(self.root)
        state = index.status(self.root, "RES-A")
        self.assertEqual(state["index_details"]["fts"], "not_created")
        self.assertEqual(index.rebuild(self.root, dry_run=True)["writes"], 0)
        self.assertEqual(snapshot(self.root), before)

    def test_actual_receipt_matches_generated_contract(self):
        from memory.contracts import SCHEMA, validate_schema
        receipt, rid = self.save()
        self.assertEqual(validate_schema(receipt, SCHEMA["$defs"]["CommitReceipt"], SCHEMA["$defs"]), [])
        changed, _ = self.save(draft(body="修订后的合成正文"), head=receipt["commit_id"], rid=rid, revision=1)
        self.assertEqual(changed["record_results"][0]["status"], "updated")
        self.assertEqual(validate_schema(changed, SCHEMA["$defs"]["CommitReceipt"], SCHEMA["$defs"]), [])

    def test_query_receipt_and_strict_request(self):
        _, rid = self.save()
        result = search.search(self.root, {"query": "预热", "purpose": "exploration", "vector": "off"})
        saved = self.root / "retrieval/queries" / (result["query_id"] + ".json")
        self.assertTrue(saved.is_file())
        current = next(row for row in json.loads(saved.read_text(encoding="utf-8"))["candidates"] if row["canonical_id"] == rid)
        self.assertEqual(current["source_ref"]["revision"], 1)
        self.assertEqual(current["source_ref"]["target_id"], rid)
        for patch in ({"purpose": "formal"}, {"unknown": True}, {"stage": []}, {"vector": "download"}, {"budget": True}):
            value = {"query": "预热", "purpose": "exploration", "vector": "off", **patch}
            with self.assertRaises(MemoryError):
                search.search(self.root, value, record=False)

    def test_evaluation_math_and_holdout_guard(self):
        metrics = evaluation.ranking_metrics({"A": 3, "B": 1}, ["A", "A", "C", "B"], k=2)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertEqual(metrics["duplicates"], 1)
        self.assertAlmostEqual(metrics["ndcg"], 7 / (7 + 1 / __import__('math').log2(3)))
        data = evaluation.load_queries(ROOT / "docs/design/system-memory/fixtures/queries.json")
        self.assertEqual(len(data["queries"]), 32)
        self.assertTrue(all(row["split"] == "development" for row in data["queries"]))
        self.assert_code("ACCESS_DENIED", lambda: evaluation.load_queries(ROOT / "docs/design/system-memory/fixtures/queries.json", split="holdout"))

    def test_evaluation_profiles_use_distinct_real_channels(self):
        receipt, rid = self.save()
        self.add_representations(rid, receipt["commit_id"])
        req = {"query": "trigger", "purpose": "exploration", "owner_id": "RES-A", "vector": "off"}
        single = search.search(self.root, req, record=False, ranking_profile="memory_single")
        multiple = search.search(self.root, req, record=False, ranking_profile="memory_multi")
        baseline = search.search(self.root, req, record=False, ranking_profile="legacy")
        self.assertEqual(single["candidates"], [])
        self.assertEqual(baseline["candidates"], [])
        self.assertEqual([row["canonical_id"] for row in multiple["candidates"]], [rid])
        self.assertNotEqual(single["query_fingerprint"], multiple["query_fingerprint"])
        self.assert_code("INVALID_ARGUMENT", lambda: search.search(self.root, req, record=False, ranking_profile="unknown"))

    @unittest.skipUnless((ROOT / "services/qdrant/models/multilingual-minilm/model_optimized.onnx").is_file()
                         and importlib.util.find_spec("qdrant_client") and importlib.util.find_spec("fastembed"),
                         "真实 384 维离线环境缺失；不能以数学/FTS 测试替代模型验收")
    def test_real_384_vectors_and_M11_collection_isolation(self):
        """实际离线模型/Qdrant；仅给隔离副本建只读模型硬链接，不改原模型。"""
        _, rid = self.save()
        source = ROOT / "services/qdrant/models/multilingual-minilm"
        destination = self.root / "services/qdrant/models/multilingual-minilm"
        for path in source.rglob("*"):
            target = destination / path.relative_to(source)
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                # 硬链接文件只由编码器读取；损坏/维度反例只修改独立清单副本。
                # 跨卷时使用复制，不改模型/环境版本，不从网络下载。
                try:
                    os.link(path, target)
                except OSError:
                    shutil.copyfile(path, target)
        manifest = self.root / "services/qdrant/model-manifest.json"
        shutil.copyfile(ROOT / "services/qdrant/model-manifest.json", manifest)
        cfg = json.loads((ROOT / "retrieval/config.json").read_text(encoding="utf-8"))
        config_path = self.root / "retrieval/config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(cfg), encoding="utf-8")
        import qdrant_backend
        old = qdrant_backend.LocalBackend(self.root, cfg)
        old_collection = old.collection
        old.close()
        home = self.root / owners.resolve_owner(self.root, "RES-A")["memory_home"]
        before = snapshot(home)
        indexed = index.sync_owner(self.root, "RES-A", vector="required")
        self.assertEqual(indexed["index_status"], "indexed", indexed)
        memory_collection = indexed["vector"]["collection"]
        self.assertNotEqual(memory_collection, old_collection)
        required = search.search(self.root, {"query": "先预热核对漂移", "purpose": "exploration", "vector": "required"}, record=False)
        found = next(row for row in required["candidates"] if row["canonical_id"] == rid)
        self.assertIn("vector", found["rank_channels"])
        def fail(point):
            if point == "vector_upsert":
                raise OSError("SYNTHETIC ONLY new collection switch failure")
        with patch.object(index, "ENCODER_VERSION", "synthetic-new-encoder-v2"):
            failed = index.sync_owner(self.root, "RES-A", vector="required", fault=fail)
            self.assertEqual(failed["index_status"], "pending")
        check = index.MemoryVectorBackend(self.root)
        try:
            self.assertEqual(check.collection, memory_collection)
            self.assertTrue(check.backend.client.collection_exists(old_collection))
            self.assertGreater(check.backend.client.count(memory_collection, exact=True).count, 0)
        finally:
            check.close()
        actual_manifest = json.loads(manifest.read_text(encoding="utf-8"))
        altered = {**actual_manifest, "dimensions": 768}
        manifest.write_text(json.dumps(altered), encoding="utf-8")
        self.assert_code("CAPABILITY_UNAVAILABLE", lambda: index.MemoryVectorBackend(self.root))
        manifest.write_text(json.dumps(actual_manifest), encoding="utf-8")
        altered_cfg = deepcopy(cfg)
        altered_cfg["embedding"]["model"] = "unsupported-synthetic-model"
        self.assert_code("CAPABILITY_UNAVAILABLE", lambda: index.MemoryVectorBackend(self.root, altered_cfg))
        self.assertEqual(snapshot(home), before)


if __name__ == "__main__":
    unittest.main()
