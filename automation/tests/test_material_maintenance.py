"""F1 上真实维护计划/审查/受限事务回归；全部数据在独立合成副本内。"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import uuid

from material_query_fixture import materialize
from material_query import maintenance
from material_query.budget import DEFAULT_BUDGET, Ledger
from material_query.contracts import MaintenancePlan, MaintenanceRequest, Scope
from material_query.coordinator import Coordinator
from material_query.legacy_adapter import from_legacy
from material_query.validation import QueryError, parse
from material_query.wire import json_value
from material_query.writer import Writer
from memory import api, contracts, index, owners
from memory.service import MemoryService
from memory.store import MemoryStore


class MaterialMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boundary = tempfile.TemporaryDirectory()
        cls.fx = materialize(Path(cls.boundary.name) / "维护 F1 原配方", isolation_root=cls.boundary.name)

    @classmethod
    def tearDownClass(cls):
        cls.boundary.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "维护 合成副本"
        shutil.copytree(self.fx.root, self.root)
        self.coordinator = Coordinator(self.root)
        self.scope = Scope((self.fx.owner_ids["B"],), None, ("experience",), None, None, None, None,
                           False, (), (), None, None)

    def tearDown(self):
        self.coordinator.close()
        self.temp.cleanup()

    def head(self, alias="B"):
        owner = owners.resolve_owner(self.root, self.fx.owner_ids[alias])
        return MemoryStore(self.root).read_snapshot(owner)["head"]

    def plan(self, key="B.experience", scope=None):
        ref, _ = from_legacy(self.fx.ref(key))
        request = MaintenanceRequest((ref,), scope or self.scope, "dependency-review", "1")
        result = maintenance.plan(self.coordinator, json_value(request))
        self.assertIn(result["status"], {"ok", "partial"}, result)
        self.assertIsNotNone(result["value"], result)
        parse(result["value"], MaintenancePlan)
        return result["value"]

    def proposed(self, value, key="B.experience", action="revise"):
        value = deepcopy(value)
        value.update(semantic_reviewer="SYNTHETIC explicit human reviewer", reviewer_kind="human",
                     review_note="已检查任务包完整内容、原件与适用条件；这是软件回归，不代表现实科学验收")
        value["reviewed_refs"] = [deepcopy(ref) for part in value["context_items"] for ref in part["refs"]]
        item = next(item for item in value["items"] if item["ref"]["id"] == self.fx.record_ids[key])
        item.update(action=action, reasons=["SYNTHETIC：依据当前输入显式修订可复用建议"])
        if action in {"revise", "resynthesize"}:
            record = self.fx.records[key]
            draft = {name: deepcopy(record[name]) for name in (*contracts.CONTENT_FIELDS, "schema_version", "record_reason")}
            draft.update(change_reason="SYNTHETIC：维护测试追加新修订")
            if record["kind"] == "experience":
                draft["payload"]["recommendation"] += "；MQ_MAINTENANCE_CHANGED"
            else:
                draft["title"] += " MQ_MAINTENANCE_CHANGED"
            item["draft_json"] = json.dumps(draft, ensure_ascii=False)
        elif action == "retract":
            item["draft_json"] = json.dumps({"claim_id": self.fx.claims["accepted"], "reason": "SYNTHETIC：显式撤回软件测试主张"}, ensure_ascii=False)
        return value

    def reviewed(self, value=None, key="B.experience", action="revise"):
        original = value or self.plan(key)
        result = maintenance.review(self.coordinator, {"plan": self.proposed(original, key, action), "expected_digest": original["plan_digest"]})
        self.assertIn(result["status"], {"ok", "partial"}, result)
        self.assertIsNotNone(result["value"], result)
        return result["value"]

    def apply(self, value, request_id=None):
        return maintenance.apply(self.coordinator, {"plan_id": value["plan_id"], "expected_digest": value["plan_digest"],
                                                   "request_id": request_id or str(uuid.uuid4())})

    def test_plan_only_defers_and_delivers_complete_content_with_receipt(self):
        before = self.head()
        value = self.plan()
        self.assertTrue(value["items"])
        self.assertTrue(all(item["action"] == "defer" for item in value["items"]))
        self.assertIsNone(value["semantic_reviewer"])
        self.assertEqual(value["reviewed_refs"], [])
        self.assertTrue(value["read_receipt"].startswith("READ-"))
        contents = "\n".join(part["markdown"] for part in value["context_items"])
        self.assertIn("MQ_B_ORIGINAL", contents)
        self.assertIn(self.fx.records["B.experience"]["payload"]["recommendation"], contents)
        self.assertEqual(before, self.head())

    def test_plan_budget_zero_and_foreign_scope_are_rejected_without_business_writes(self):
        before = self.head()
        ref, _ = from_legacy(self.fx.ref("B.experience"))
        request = json_value(MaintenanceRequest((ref,), self.scope, "dependency-review", "1"))
        with patch.object(maintenance, "DEFAULT_BUDGET", replace(DEFAULT_BUDGET, read_bytes=0)):
            result = maintenance.plan(self.coordinator, request)
        self.assertEqual(result["code"], "BUDGET", result)
        self.assertIsNone(result["value"])
        request["scope"]["owner_ids"] = [self.fx.owner_ids["A"]]
        result = maintenance.plan(self.coordinator, request)
        self.assertEqual(result["code"], "DENIED", result)
        self.assertEqual(before, self.head())

    def test_unreviewed_plan_cannot_apply(self):
        result = self.apply(self.plan())
        self.assertEqual(result["code"], "DENIED", result)
        self.assertIsNone(result["value"])

    def test_review_requires_identity_kind_note_and_verified_delivery(self):
        value = self.plan()
        for field, bad in (("semantic_reviewer", None), ("reviewer_kind", None), ("review_note", ""), ("reviewed_refs", [])):
            with self.subTest(field=field):
                proposed = self.proposed(value, action="retain")
                proposed[field] = bad
                result = maintenance.review(self.coordinator, {"plan": proposed, "expected_digest": value["plan_digest"]})
                self.assertIn(result["code"], {"VALIDATION", "DENIED"}, result)
                self.assertIsNone(result["value"])

    def test_review_cannot_change_basis_context_receipt_or_target(self):
        value = self.plan()
        for field in ("basis", "context_items", "read_receipt", "plan_digest", "items"):
            proposed = self.proposed(value, action="retain")
            if field == "basis":
                proposed[field]["owner_heads"][0][1] = "COM-forged"
            elif field == "context_items":
                proposed[field][0]["markdown"] = "FORGED CONTENT"
            elif field == "items":
                proposed[field][0]["ref"]["id"] = "MEM-forged"
            else:
                proposed[field] = "0" * 64
            result = maintenance.review(self.coordinator, {"plan": proposed, "expected_digest": value["plan_digest"]})
            self.assertEqual(result["code"], "CONFLICT", (field, result))
            self.assertIsNone(result["value"])

    def test_review_saves_new_immutable_version_without_business_commit(self):
        before = self.head()
        original = self.plan()
        reviewed = self.reviewed(original)
        self.assertNotEqual(reviewed["plan_digest"], original["plan_digest"])
        folder = self.root / maintenance.BASE / original["plan_id"]
        self.assertTrue((folder / (original["plan_digest"] + ".json")).is_file())
        self.assertTrue((folder / (reviewed["plan_digest"] + ".json")).is_file())
        self.assertEqual(before, self.head())
        repeat = self.reviewed(original)
        self.assertEqual(repeat["plan_digest"], reviewed["plan_digest"])

    def test_draft_cannot_change_owner_kind_or_add_unread_source(self):
        value = self.plan()
        for mutation in ("owner", "kind", "source"):
            proposed = self.proposed(value)
            item = next(item for item in proposed["items"] if item["action"] == "revise")
            draft = json.loads(item["draft_json"])
            if mutation == "owner":
                draft["owner_id"] = self.fx.owner_ids["A"]
            elif mutation == "kind":
                draft["kind"] = "review"
            else:
                draft["sources"].append(self.fx.source_ref("X"))
            item["draft_json"] = json.dumps(draft)
            result = maintenance.review(self.coordinator, {"plan": proposed, "expected_digest": value["plan_digest"]})
            self.assertEqual(result["code"], "DENIED", (mutation, result))

    def test_nonobject_and_invalid_json_drafts_return_validation_without_writes(self):
        value, before = self.plan(), self.head()
        for raw in ("[]", "null", "17", "{broken"):
            proposed = self.proposed(value)
            next(item for item in proposed["items"] if item["action"] == "revise")["draft_json"] = raw
            result = maintenance.review(self.coordinator, {"plan": proposed, "expected_digest": value["plan_digest"]})
            self.assertEqual(result["code"], "VALIDATION", (raw, result))
            self.assertIsNone(result["value"])
        self.assertEqual(before, self.head())

    def test_apply_uses_real_cas_and_same_request_id_replays_without_new_revision(self):
        reviewed = self.reviewed()
        request_id = str(uuid.uuid4())
        result = self.apply(reviewed, request_id)
        self.assertEqual(result["status"], "partial", result)
        self.assertEqual(result["value"]["index_status"], "pending")
        self.assertTrue(result["value"]["commits"])
        owner = self.fx.owner_ids["B"]
        rid = self.fx.record_ids["B.experience"]
        current = api.dispatch(MemoryService(self.root), "inspect", {"owner_id": owner, "record_id": rid})["record"]
        self.assertEqual(current["revision"], 2)
        self.assertIn("MQ_MAINTENANCE_CHANGED", current["payload"]["recommendation"])
        fixed_head = self.head()
        replay = self.apply(reviewed, request_id)
        self.assertEqual(replay["value"], result["value"], replay)
        self.assertEqual(fixed_head, self.head())
        self.assertTrue((self.root / result["value"]["recovery_receipt"]).is_file())

    def test_restart_reauthorizes_plan_and_source_revocation_blocks_apply(self):
        reviewed = self.reviewed()
        self.coordinator.close()
        self.coordinator = Coordinator(self.root)
        registry = self.root / "retrieval" / "sources.json"
        data = json.loads(registry.read_text(encoding="utf-8"))
        for source in data["sources"]:
            if source["source_id"] == self.fx.sources["B"]["source_id"]:
                source["enabled"] = False
        registry.write_text(json.dumps(data), encoding="utf-8")
        result = self.apply(reviewed)
        self.assertEqual(result["code"], "DENIED", result)
        self.assertIsNone(result["value"])

    def test_head_change_between_review_and_apply_rejects_stale_basis(self):
        reviewed = self.reviewed()
        request_id = str(uuid.uuid4())
        first = self.apply(reviewed, request_id)
        self.assertTrue(first["value"]["commits"], first)
        another = self.apply(reviewed, str(uuid.uuid4()))
        self.assertEqual(another["code"], "CONFLICT", another)
        self.assertIsNone(another["value"])

    def test_retract_appends_real_review_and_preserves_claim_record(self):
        scope = replace(self.scope, owner_ids=(self.fx.owner_ids["A"],), kinds=("event",))
        original = self.plan("A.event", scope)
        reviewed = self.reviewed(original, "A.event", "retract")
        result = self.apply(reviewed)
        self.assertTrue(result["value"] and result["value"]["commits"], result)
        snapshot = MemoryStore(self.root).read_snapshot(owners.resolve_owner(self.root, self.fx.owner_ids["A"]))
        claim_record = snapshot["records"][self.fx.record_ids["A.event"]]
        self.assertEqual(claim_record["revision"], 1)
        review = snapshot["records"][self.fx.record_ids["A.review.accepted"]]
        self.assertEqual(review["revision"], 2)
        self.assertEqual(review["payload"]["state"], "retracted")

    def test_writer_reads_only_target_and_current_policy_not_other_owner_bodies(self):
        ledger = Ledger(DEFAULT_BUDGET)
        writer = Writer(self.root, ledger, access_owner_ids=[self.fx.owner_ids["B"]])
        original = self.fx.records["B.experience"]
        draft = {name: deepcopy(original[name]) for name in (*contracts.CONTENT_FIELDS, "schema_version", "record_reason")}
        draft.update(change_reason="合成局部写入")
        draft["payload"]["recommendation"] += " bounded writer"
        request = {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": {"kind": "human", "id": "synthetic"},
                   "owner_id": original["owner_id"], "expected_head": self.head()["commit_id"],
                   "operations": [{"op": "put_record", "record_id": original["record_id"], "expected_revision": 1, "draft": draft}]}
        opened = []
        actual = writer.store.read_json

        def trace(path):
            if path.parent.name == "records":
                opened.append(path.stem)
            return actual(path)

        with ledger.active(), patch.object(writer.store, "read_json", side_effect=trace), \
                patch.object(index, "sync_owner", side_effect=AssertionError("unmetered indexing")):
            result = api.dispatch(writer, "commit", request)
        self.assertEqual(result["save_status"], "committed")
        self.assertEqual(set(opened), {original["record_id"]})
        self.assertGreater(ledger.snapshot()["read_bytes"], 0)

    def test_cancel_during_transaction_releases_exact_lock_and_preserves_old_head(self):
        ledger = Ledger(DEFAULT_BUDGET)
        writer = Writer(self.root, ledger, access_owner_ids=[self.fx.owner_ids["B"]])
        record = self.fx.records["B.experience"]
        draft = {name: deepcopy(record[name]) for name in (*contracts.CONTENT_FIELDS, "schema_version", "record_reason")}
        draft["payload"]["recommendation"] += " cancelled change"
        request = {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": {"kind": "human", "id": "synthetic"},
                   "owner_id": record["owner_id"], "expected_head": self.head()["commit_id"],
                   "operations": [{"op": "put_record", "record_id": record["record_id"], "expected_revision": 1, "draft": draft}]}
        before = self.head()
        writer.store.fault = lambda stage: ledger.cancelled.set() if stage == "before_head" else None
        with self.assertRaises(QueryError) as caught, ledger.active():
            api.dispatch(writer, "commit", request)
        self.assertEqual(caught.exception.code, "CANCELLED")
        self.assertEqual(before, self.head())
        owner = owners.resolve_owner(self.root, record["owner_id"])
        self.assertFalse(writer.store.path(owner, "write.lock").exists())
        self.assertLessEqual(ledger.snapshot()["read_bytes"], DEFAULT_BUDGET.read_bytes)

    def writer_request(self, *, root=None):
        root = root or self.root
        record = self.fx.records["B.experience"]
        draft = {name: deepcopy(record[name]) for name in (*contracts.CONTENT_FIELDS, "schema_version", "record_reason")}
        draft["payload"]["recommendation"] += " resource-boundary change"
        owner = owners.resolve_owner(root, record["owner_id"])
        head = MemoryStore(root).read_snapshot(owner)["head"]
        return {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": {"kind": "human", "id": "synthetic"},
                "owner_id": record["owner_id"], "expected_head": head["commit_id"],
                "operations": [{"op": "put_record", "record_id": record["record_id"], "expected_revision": 1, "draft": draft}]}

    def test_real_read_budget_exhaustion_before_publish_releases_write_lock(self):
        trial = Path(self.temp.name) / "预算测量独立副本"
        shutil.copytree(self.fx.root, trial)
        measured = Ledger(DEFAULT_BUDGET)
        probe = Writer(trial, measured, access_owner_ids=[self.fx.owner_ids["B"]])
        positions = {}
        probe.store.fault = lambda stage: positions.update(before_head=measured.snapshot()["read_bytes"]) if stage == "before_head" else None
        with measured.active():
            api.dispatch(probe, "commit", self.writer_request(root=trial))
        # 普通读取刚好到达 before_head；额外4KiB只预留给安全核对自己的锁。
        limits = replace(DEFAULT_BUDGET, read_bytes=positions["before_head"] + 4096)
        ledger = Ledger(limits)
        writer = Writer(self.root, ledger, access_owner_ids=[self.fx.owner_ids["B"]])
        before = self.head()
        with self.assertRaises(QueryError) as caught, ledger.active():
            api.dispatch(writer, "commit", self.writer_request())
        self.assertEqual(caught.exception.code, "BUDGET")
        self.assertEqual(before, self.head())
        owner = owners.resolve_owner(self.root, self.fx.owner_ids["B"])
        self.assertFalse(writer.store.path(owner, "write.lock").exists())
        self.assertLessEqual(ledger.snapshot()["read_bytes"], limits.read_bytes)

    def test_cancellation_after_head_keeps_committed_receipt_and_removes_lock(self):
        ledger = Ledger(DEFAULT_BUDGET)
        writer = Writer(self.root, ledger, access_owner_ids=[self.fx.owner_ids["B"]])
        writer.store.fault = lambda stage: ledger.cancelled.set() if stage == "after_head" else None
        receipt = None
        before = self.head()
        with self.assertRaises(QueryError) as caught:
            with ledger.active():
                receipt = api.dispatch(writer, "commit", self.writer_request())
        self.assertEqual(caught.exception.code, "CANCELLED")
        self.assertEqual(receipt["save_status"], "committed")
        self.assertEqual(receipt["commit_id"], self.head()["commit_id"])
        self.assertNotEqual(before, self.head())
        owner = owners.resolve_owner(self.root, self.fx.owner_ids["B"])
        self.assertFalse(writer.store.path(owner, "write.lock").exists())

    def test_cross_owner_failure_returns_committed_owner_and_retries_only_pending_owner(self):
        scope = replace(self.scope, owner_ids=(self.fx.owner_ids["A"], self.fx.owner_ids["B"]))
        refs = tuple(from_legacy(self.fx.ref(key))[0] for key in ("A.experience", "B.experience"))
        result = maintenance.plan(self.coordinator, json_value(MaintenanceRequest(refs, scope, "dependency-review", "1")))
        self.assertIsNotNone(result["value"], result)
        proposed = self.proposed(result["value"], "A.experience")
        proposed = self.proposed(proposed, "B.experience")
        reviewed = maintenance.review(self.coordinator, {"plan": proposed, "expected_digest": result["value"]["plan_digest"]})
        self.assertIsNotNone(reviewed["value"], reviewed)
        request_id = str(uuid.uuid4())
        original_dispatch, committed = maintenance.api.dispatch, []

        def fail_second(service, action, request):
            if action == "commit":
                if committed:
                    raise QueryError("CONFLICT", "SYNTHETIC第二owner并发故障")
                receipt = original_dispatch(service, action, request)
                committed.append(request["owner_id"])
                return receipt
            return original_dispatch(service, action, request)

        with patch.object(maintenance.api, "dispatch", side_effect=fail_second):
            partial = self.apply(reviewed["value"], request_id)
        self.assertEqual(partial["status"], "partial", partial)
        self.assertEqual(len(partial["value"]["commits"]), 1)
        self.assertTrue(partial["value"]["pending_items"])
        first = partial["value"]["commits"][0]
        retry = self.apply(reviewed["value"], request_id)
        self.assertEqual(len(retry["value"]["commits"]), 2, retry)
        self.assertIn(first, retry["value"]["commits"])
        for alias in ("A", "B"):
            record = api.dispatch(MemoryService(self.root), "inspect", {"owner_id": self.fx.owner_ids[alias], "record_id": self.fx.record_ids[alias + ".experience"]})["record"]
            self.assertEqual(record["revision"], 2)

    def test_crash_after_canonical_commit_before_local_receipt_recovers_idempotently(self):
        reviewed = self.reviewed()
        request_id = str(uuid.uuid4())
        original_write = maintenance._write_once

        def fail_receipt(path, value):
            if path.name == "owner-0000.json":
                raise OSError("SYNTHETIC失去临时回执写入")
            return original_write(path, value)

        with patch.object(maintenance, "_write_once", side_effect=fail_receipt):
            partial = self.apply(reviewed, request_id)
        self.assertEqual(partial["status"], "partial", partial)
        self.assertEqual(len(partial["value"]["commits"]), 1)
        first_head = self.head()
        retried = self.apply(reviewed, request_id)
        self.assertEqual(first_head, self.head())
        self.assertEqual(retried["value"]["commits"], partial["value"]["commits"], retried)

    def test_unread_dependency_cannot_be_hidden_by_exhausting_output_budget(self):
        ref, _ = from_legacy(self.fx.ref("B.experience"))
        request = json_value(MaintenanceRequest((ref,), self.scope, "dependency-review", "1"))
        with patch.object(maintenance, "DEFAULT_BUDGET", replace(DEFAULT_BUDGET, output_chars=len(maintenance._body(self.fx.records["B.experience"])))):
            result = maintenance.plan(self.coordinator, request)
        self.assertIsNotNone(result["value"], result)
        contents = "\n".join(part["markdown"] for part in result["value"]["context_items"])
        self.assertNotIn("MQ_B_ORIGINAL", contents)
        proposed = self.proposed(result["value"], action="retain")
        rejected = maintenance.review(self.coordinator, {"plan": proposed, "expected_digest": result["value"]["plan_digest"]})
        self.assertEqual(rejected["code"], "DENIED", rejected)


if __name__ == "__main__":
    unittest.main()
