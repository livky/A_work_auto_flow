"""SYNTHETIC ONLY: mixed record versions, trace boundaries and index upgrades.

These tests use local JSON/SQLite and a deterministic vector protocol fixture.
They never load a model or call the network, and preserve frozen v1 recipes.
"""
from copy import deepcopy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "automation/scripts"))
from memory import contracts, index, owners, search
from memory.errors import MemoryError
from memory.service import MemoryService
from memory_fixture import materialize
from test_memory_contracts import draft as contract_draft
from test_memory_index import DeterministicVectorBackend


def request(draft, head=None, *, rid=None, revision=None):
    operation = {"op": "put_record", "draft": deepcopy(draft)}
    operation.update({"record_id": rid, "expected_revision": revision} if rid else {"client_key": "document"})
    return {"schema_version": 2, "request_id": str(uuid.uuid4()), "actor": {"kind": "workflow", "id": "synthetic-v2-test"},
            "owner_id": draft["owner_id"], "expected_head": head, "operations": [operation]}


class MemoryLevelV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="分层 v2 合成-")
        self.fixture = materialize(Path(self.temp.name) / "workspace", isolation_root=self.temp.name)
        self.root = self.fixture.root
        self.service = MemoryService(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_contract_default_v3_and_explicit_legacy_are_distinct(self):
        value = contract_draft("event")
        value.pop('schema_version')
        current = contracts.validate_record(value)
        self.assertTrue(current["valid"], current["errors"])
        self.assertEqual((current["record"]["schema_version"], current["record"]["level"]), (3, "L2"))
        legacy = contracts.validate_record({**value, "schema_version": 1})
        self.assertTrue(legacy["valid"], legacy["errors"])
        frozen = deepcopy(legacy["record"])
        self.assertEqual(contracts.project_memory_level(frozen), "L2")
        self.assertEqual(frozen, legacy["record"])
        self.assertEqual(frozen["level"], "L1")
        self.assertFalse(contracts.validate_record({**value, "schema_version": 2, "level": "L1"})["valid"])
        self.assertFalse(contracts.validate_record({**value, "schema_version": 4})["valid"])

    def detail(self):
        import evidence
        value = contract_draft("detail")
        value["owner_id"] = "RES-SYN-THERMAL"
        value["payload"]["run_ref"].update(target_id="RUN-SYN-THERMAL",
            sha256=evidence.EvidenceGraph(self.root).nodes["RUN-SYN-THERMAL"]["fingerprint"])
        value["payload"]["inputs"] = [self.fixture.source_ref("SRC-SYN-THERMAL")]
        value["sources"] = [deepcopy(value["payload"]["run_ref"])]
        value["body_markdown"] = "# 合成说明\n公式 $s=1+2$，结果3；仅测试结构，不声称Run已执行。"
        return value

    def test_detail_is_a_fixed_run_document_and_not_a_new_experiment(self):
        value = self.detail()
        saved = self.service.commit(request(value))
        self.assertEqual(saved["save_status"], "committed")
        rid = saved["record_results"][0]["record_id"]
        record = self.service.inspect(value["owner_id"], record_id=rid)["record"]
        self.assertEqual((record["kind"], record["schema_version"], record["level"]), ("detail", 2, "L1"))
        self.assertNotIn("claims", record["payload"])
        self.assertEqual(record["payload"]["run_ref"]["target_id"], "RUN-SYN-THERMAL")
        self.assertEqual(len(list((self.root / "runs").glob("*/run.json"))), 8)
        for field in ("question", "method", "steps", "results", "limitations", "run_ref"):
            broken = deepcopy(value)
            del broken["payload"][field]
            self.assertFalse(contracts.validate_record(broken)["valid"], field)
        broken = deepcopy(value)
        broken["payload"]["run_ref"]["sha256"] = None
        self.assertFalse(contracts.validate_record(broken)["valid"])
        self.assertFalse(contracts.validate_record({**value, "schema_version": 1})["valid"])
        broken = deepcopy(value)
        broken["payload"]["run_ref"]["sha256"] = "0" * 64
        with self.assertRaises(MemoryError) as error:
            self.service.commit(request(broken, saved["commit_id"]))
        self.assertEqual(error.exception.code, "STALE_BASIS")

    def test_mixed_revision_keeps_old_hashes_refs_and_idempotency(self):
        legacy_request = self.fixture.request(["MEM-EXP-THERMAL"])
        saved = self.service.commit(legacy_request)
        rid = saved["record_results"][0]["record_id"]
        old = self.service.inspect("RES-SYN-THERMAL", record_id=rid)["record"]
        owner = owners.resolve_owner(self.root, "RES-SYN-THERMAL")
        old_files = {p: p.read_bytes() for p in (self.root / owner["memory_home"] / "commits").rglob("*") if p.is_file()}
        updated = deepcopy(legacy_request["operations"][0]["draft"])
        updated.update(schema_version=2, level="L3", body_markdown=updated["body_markdown"] + "\n明确后续条件。")
        req = request(updated, saved["commit_id"], rid=rid, revision=1)
        receipt = self.service.commit(req)
        again = self.service.commit(req)
        self.assertEqual(receipt["commit_id"], again["commit_id"])
        self.assertEqual(self.service.inspect("RES-SYN-THERMAL", record_id=rid, revision=1)["record"], old)
        self.assertEqual({p: p.read_bytes() for p in old_files}, old_files)
        ref = {"target_kind": "record", "target_id": rid, "revision": 1, "sha256": old["record_hash"], "locator": "payload", "relation": "input"}
        self.assertEqual(self.service._resolve_ref(ref, {}, [])["record_hash"], old["record_hash"])
        current = self.service.inspect("RES-SYN-THERMAL", record_id=rid)["record"]
        self.assertEqual((current["revision"], current["schema_version"], current["level"]), (2, 2, "L3"))
        with self.assertRaises(MemoryError) as error:
            self.service.commit(request(updated, saved["commit_id"], rid=rid, revision=1))
        self.assertEqual(error.exception.code, "VERSION_CONFLICT")

    def test_l0_trace_only_and_cross_owner_representation_cannot_bypass(self):
        first = self.service.commit(self.fixture.request(["MEM-SRC-THERMAL"]))
        rid = first["record_results"][0]["record_id"]
        raw = self.service.inspect("RES-SYN-THERMAL", record_id=rid)["record"]
        rep = contract_draft("representation")
        rep.update(owner_id="RES-SYN-PRESSURE", discovery="workspace_summary")
        rep["payload"].update(target={"target_kind": "record", "target_id": rid, "revision": 1, "sha256": raw["record_hash"], "locator": "body", "relation": "references"}, text="L0-only-canary-untranslatable")
        self.service.commit(request(rep))
        index.reconcile(self.root, vector="required", backend_factory=DeterministicVectorBackend)
        with closing(index.connect(self.root)) as db:
            self.assertEqual(db.execute("SELECT body FROM memory_records WHERE canonical_id=?", (rid,)).fetchone()[0], "")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_entries WHERE canonical_id=?", (rid,)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT active FROM memory_representations WHERE target_id=?", (rid,)).fetchone()[0], 0)
        self.assertFalse(any(row["canonical_id"] == rid for row in DeterministicVectorBackend(self.root).entries.values()))
        query = {"query": rid, "purpose": "exploration", "vector": "off", "include_ids": [rid]}
        self.assertNotIn(rid, {r["canonical_id"] for r in search.search(self.root, query, record=False)["candidates"]})
        traced = search.search(self.root, {**query, "retrieval_mode": "trace"}, record=False)
        self.assertEqual(traced["candidates"][0]["canonical_id"], rid)
        self.assertEqual(traced["candidates"][0]["level"], "L0")
        self.assertIn(raw["body_markdown"][:30], traced["candidates"][0]["snippet"])
        excluded = search.search(self.root, {**query, "retrieval_mode": "trace", "exclude_ids": [rid]}, record=False)
        self.assertNotIn(rid, {r["canonical_id"] for r in excluded["candidates"]})

    def test_projection_refresh_with_same_head_does_not_rewrite_canonical(self):
        first = self.service.commit(self.fixture.request(["MEM-EXP-THERMAL", "MEM-MAP-THERMAL"]))
        ids = [r["record_id"] for r in first["record_results"]]
        owner = owners.resolve_owner(self.root, "RES-SYN-THERMAL")
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root / owner["memory_home"]).rglob("*") if p.is_file()}
        with closing(index.connect(self.root)) as db:
            db.execute("UPDATE memory_records SET level='L2' WHERE canonical_id=?", (ids[0],))
            db.execute("UPDATE memory_index_state SET projection_version=NULL WHERE owner_id='RES-SYN-THERMAL'")
            db.commit()
        self.assertEqual(index.status(self.root, "RES-SYN-THERMAL")["index_status"], "pending")
        result = search.search(self.root, {"query": "预热", "purpose": "exploration", "vector": "off", "levels": ["L3"], "owner_id": "RES-SYN-THERMAL"}, record=False)
        self.assertIn(ids[0], {r["canonical_id"] for r in result["candidates"]})
        self.assertTrue(all(r["level"] == "L3" for r in result["candidates"]))
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
        self.assertEqual(self.service.inspect("RES-SYN-THERMAL")["head"]["commit_id"], first["commit_id"])
        with closing(index.connect(self.root)) as db:
            self.assertEqual(db.execute("SELECT projection_version FROM memory_index_state WHERE owner_id='RES-SYN-THERMAL'").fetchone()[0], index.PROJECTION_VERSION)


if __name__ == "__main__":
    unittest.main()
