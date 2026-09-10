"""维护状态从持久计划和规范事务回执恢复，状态读取不得推进工作。

全部写入只发生在独立 F1 副本的显式 plan/review/apply 准备步骤。status
经公开 API 调用；用完整文件指纹、真实跨 owner 故障和丢失临时回执证明
只读及恢复事实，不将测试桩产生的提交当作规范完成。
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import uuid

from material_query_fixture import materialize
from material_query import maintenance
from material_query.api import dispatch
from material_query.budget import DEFAULT_BUDGET
from material_query.contracts import AssociationOptions, DefinitionRef, MaintenanceRequest, MaintenanceStatusReceipt, QueryRequest, Result, Scope
from material_query.coordinator import Coordinator
from material_query.legacy_adapter import from_legacy
from material_query.reader import MeteredStore
from material_query.validation import QueryError, parse
from material_query.wire import json_value
from memory import api, contracts, index, owners
from memory.service import MemoryService
from memory.store import MemoryStore


class MaterialMaintenanceStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boundary = tempfile.TemporaryDirectory()
        cls.fx = materialize(Path(cls.boundary.name) / "持久状态 F1", isolation_root=cls.boundary.name)

    @classmethod
    def tearDownClass(cls):
        cls.boundary.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "状态测试独立副本"
        shutil.copytree(self.fx.root, self.root)
        self.app = Coordinator(self.root)
        self.scope = Scope((self.fx.owner_ids["B"],), None, ("experience",), None, None, None, None,
                           False, (), (), None, None)

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def context(self, scope=None, budget=DEFAULT_BUDGET):
        # This is the trusted context factory also used by search/start. Status
        # requires its identity and budget, not a redundant content recall.
        selected = scope or self.scope
        request = QueryRequest(DefinitionRef("full", "1"), "读取持久维护状态", (), selected, selected,
            "exploration", AssociationOptions("off", "existing-relations", "1", 2, 0.15, None),
            budget, "current", 20, "skip", (), "", channels=("identity",))
        return self.app._new(request)

    def status(self, plan_id, *, state=None, scope=None):
        state = state or self.context(scope)
        result = dispatch(self.app, "maintenance-status", {"query_id": state.query_id, "plan_id": plan_id})
        parse(result, Result[MaintenanceStatusReceipt])
        return result

    def plan(self, keys=("B.experience",), scope=None):
        refs = tuple(from_legacy(self.fx.ref(key))[0] for key in keys)
        result = maintenance.plan(self.app, json_value(MaintenanceRequest(refs, scope or self.scope, "dependency-review", "1")))
        self.assertIsNotNone(result["value"], result)
        return result["value"]

    def reviewed(self, value=None, keys=("B.experience",), action="revise"):
        original = value or self.plan(keys)
        proposed = deepcopy(original)
        proposed.update(semantic_reviewer="SYNTHETIC status reviewer", reviewer_kind="human",
            review_note="已阅读合成固定任务包；仅核验软件状态，不声称现实科学复核")
        proposed["reviewed_refs"] = [deepcopy(ref) for part in proposed["context_items"] for ref in part["refs"]]
        for key in keys:
            record = self.fx.records[key]
            item = next(item for item in proposed["items"] if item["ref"]["id"] == record["record_id"])
            item.update(action=action, reasons=["合成状态回归的明确修订"])
            if action == "retract":
                draft = {"claim_id": self.fx.claims["accepted"], "reason": "SYNTHETIC撤回状态回归"}
            else:
                draft = {name: deepcopy(record[name]) for name in (*contracts.CONTENT_FIELDS, "schema_version", "record_reason")}
                draft["change_reason"] = "SYNTHETIC status change"
                draft["payload"]["recommendation"] += "；STATUS_CHANGED"
            item["draft_json"] = json.dumps(draft, ensure_ascii=False)
        result = maintenance.review(self.app, {"plan": proposed, "expected_digest": original["plan_digest"]})
        self.assertIsNotNone(result["value"], result)
        return result["value"]

    def apply(self, value, request_id=None):
        return maintenance.apply(self.app, {"plan_id": value["plan_id"], "expected_digest": value["plan_digest"],
                                           "request_id": request_id or str(uuid.uuid4())})

    def hashes(self):
        return {path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob("*") if path.is_file()}

    def head(self, alias="B"):
        return MemoryStore(self.root).read_snapshot(owners.resolve_owner(self.root, self.fx.owner_ids[alias]))["head"]

    def test_unreviewed_plan_survives_restart_and_status_is_strictly_read_only(self):
        plan = self.plan()
        self.app.close()
        self.app = Coordinator(self.root)
        before = self.hashes()
        with patch.object(maintenance, "_write_once", side_effect=AssertionError("status must not write")), \
             patch.object(maintenance.api, "dispatch", side_effect=AssertionError("status must not execute")):
            result = self.status(plan["plan_id"])
        self.assertIn(result["status"], {"ok", "partial"}, result)
        self.assertEqual(result["value"]["commits"], [])
        self.assertEqual(result["value"]["attempts"], [])
        self.assertFalse(result["value"]["plan_versions"][0]["reviewed"])
        self.assertIn(self.fx.owner_ids["B"], result["value"]["pending_owner_ids"])
        self.assertTrue(result["value"]["pending_reviews"])
        self.assertIsNone(result["value"]["resume_cursor"])
        self.assertEqual(before, self.hashes())

    def test_applied_plan_reports_real_commit_fixed_changes_and_live_index_pending(self):
        plan = self.reviewed()
        applied = self.apply(plan)
        expected = applied["value"]["commits"][0]
        self.app.close()
        self.app = Coordinator(self.root)
        before = self.hashes()
        result = self.status(plan["plan_id"])
        receipt = result["value"]
        self.assertEqual(len(receipt["plan_versions"]), 2)
        self.assertEqual([(r["owner_id"], r["commit_id"]) for r in receipt["commits"]], [tuple(expected)])
        self.assertEqual(len(receipt["commits"][0]["receipt_sha256"]), 64)
        change = receipt["commits"][0]["changes"][0]
        self.assertEqual(change["ref"]["revision"], 2)
        self.assertEqual(change["status"], "updated")
        self.assertEqual(receipt["attempts"][0]["pending_owner_ids"], [])
        self.assertTrue(receipt["attempts"][0]["local_completed"])
        self.assertEqual(receipt["index_states"][0]["fts_status"], "pending")
        self.assertFalse(receipt["basis_stale"])
        self.assertEqual(before, self.hashes())

    def test_partial_cross_owner_failure_is_observed_without_resuming_second_owner(self):
        scope = replace(self.scope, owner_ids=(self.fx.owner_ids["A"], self.fx.owner_ids["B"]))
        keys = ("A.experience", "B.experience")
        plan = self.reviewed(self.plan(keys, scope), keys)
        actual, commits = maintenance.api.dispatch, []

        def fail_second(service, action, request):
            if action == "commit" and commits:
                raise QueryError("CONFLICT", "SYNTHETIC第二owner失败")
            result = actual(service, action, request)
            if action == "commit":
                commits.append(result)
            return result

        with patch.object(maintenance.api, "dispatch", side_effect=fail_second):
            applied = self.apply(plan)
        self.assertEqual(len(applied["value"]["commits"]), 1)
        before = self.hashes()
        result = self.status(plan["plan_id"], scope=scope)
        self.assertEqual(len(result["value"]["commits"]), 1, result)
        attempt = result["value"]["attempts"][0]
        self.assertEqual(attempt["state"], "partial")
        self.assertEqual(len(attempt["pending_owner_ids"]), 1)
        self.assertNotIn(attempt["pending_owner_ids"][0], attempt["completed_owner_ids"])
        self.assertEqual(before, self.hashes())

    def test_missing_local_receipt_uses_canonical_ledger_without_repairing_files(self):
        plan = self.reviewed()
        actual_write = maintenance._write_once

        def lose_receipt(path, value):
            if path.name == "owner-0000.json":
                raise OSError("SYNTHETIC临时回执丢失")
            return actual_write(path, value)

        with patch.object(maintenance, "_write_once", side_effect=lose_receipt):
            applied = self.apply(plan)
        self.assertEqual(len(applied["value"]["commits"]), 1)
        before = self.hashes()
        result = self.status(plan["plan_id"])
        self.assertEqual(len(result["value"]["commits"]), 1, result)
        attempt = result["value"]["attempts"][0]
        self.assertEqual(attempt["state"], "committed")
        self.assertFalse(attempt["local_completed"])
        self.assertEqual(attempt["local_receipt_owner_ids"], [])
        self.assertEqual(attempt["pending_owner_ids"], [])
        self.assertEqual(before, self.hashes())

    def test_forged_local_commit_receipt_is_not_trusted(self):
        plan = self.reviewed()
        applied = self.apply(plan)
        path = self.root / applied["value"]["recovery_receipt"]
        receipt_path = path.parent / "owner-0000.json"
        value = json.loads(receipt_path.read_text(encoding="utf-8"))
        value["commit_id"] = "COM-" + str(uuid.uuid4())
        receipt_path.write_text(json.dumps(value), encoding="utf-8")
        before = self.hashes()
        result = self.status(plan["plan_id"])
        self.assertEqual(result["code"], "CONFLICT", result)
        self.assertIsNone(result["value"])
        self.assertIsNone(result["basis"])
        self.assertEqual(before, self.hashes())

    def test_source_revocation_after_restart_rejects_status_without_leaking_receipts(self):
        plan = self.reviewed()
        self.apply(plan)
        registry = self.root / "retrieval/sources.json"
        value = json.loads(registry.read_text(encoding="utf-8"))
        for item in value["sources"]:
            if item["source_id"] == self.fx.sources["B"]["source_id"]:
                item["enabled"] = False
        registry.write_text(json.dumps(value), encoding="utf-8")
        self.app.close()
        self.app = Coordinator(self.root)
        result = self.status(plan["plan_id"])
        self.assertEqual(result["code"], "DENIED", result)
        self.assertIsNone(result["value"])
        self.assertIsNone(result["basis"])

    def test_new_context_ceiling_cannot_read_old_plan_owner_body(self):
        plan = self.plan()
        reads, actual_record = [], MeteredStore._record

        def observed(store, owner, record_id, entry):
            reads.append(owner["owner_id"])
            return actual_record(store, owner, record_id, entry)

        scope = replace(self.scope, owner_ids=(self.fx.owner_ids["A"],))
        with patch.object(MeteredStore, "_record", observed):
            result = self.status(plan["plan_id"], scope=scope)
        self.assertEqual(result["code"], "DENIED", result)
        self.assertIsNone(result["value"])
        self.assertNotIn(self.fx.owner_ids["B"], reads)

    def test_zero_budget_cancellation_and_active_query_do_not_reset_the_ledger(self):
        plan = self.plan()
        state = self.context(budget=replace(DEFAULT_BUDGET, read_bytes=0))
        result = self.status(plan["plan_id"], state=state)
        self.assertEqual(result["code"], "BUDGET", result)
        self.assertEqual(result["consumed"]["read_bytes"], 0)
        cancelled = self.context()
        cancelled.ledger.cancelled.set()
        self.assertEqual(self.status(plan["plan_id"], state=cancelled)["code"], "CANCELLED")
        active = self.context()
        with active.lock:
            result = self.status(plan["plan_id"], state=active)
        self.assertEqual(result["code"], "CONFLICT", result)
        self.assertEqual(result["consumed"]["read_bytes"], 0)

    def test_unknown_plan_and_unknown_request_fields_are_rejected(self):
        state = self.context()
        result = self.status("MP-" + str(uuid.uuid4()), state=state)
        self.assertEqual(result["code"], "SOURCE_MISSING", result)
        result = dispatch(self.app, "maintenance-status", {"query_id": state.query_id,
            "plan_id": "MP-" + str(uuid.uuid4()), "access_owner_ids": [self.fx.owner_ids["B"]]})
        self.assertEqual(result["code"], "VALIDATION", result)

    def test_later_head_change_keeps_verified_old_commit_but_marks_basis_stale(self):
        plan = self.reviewed()
        applied = self.apply(plan)
        service = MemoryService(self.root)
        owner = self.fx.owner_ids["B"]
        record = api.dispatch(service, "inspect", {"owner_id": owner, "record_id": self.fx.record_ids["B.experience"]})["record"]
        draft = {name: deepcopy(record[name]) for name in (*contracts.CONTENT_FIELDS, "schema_version", "record_reason")}
        draft.update(change_reason="SYNTHETIC独立后续修改")
        draft["payload"]["recommendation"] += "；LATER_UNRELATED_CHANGE"
        api.dispatch(service, "commit", {"schema_version": 1, "request_id": str(uuid.uuid4()),
            "owner_id": owner, "expected_head": self.head()["commit_id"], "actor": {"kind": "human", "id": "synthetic"},
            "operations": [{"op": "put_record", "record_id": record["record_id"], "expected_revision": record["revision"], "draft": draft}]})
        before = self.hashes()
        result = self.status(plan["plan_id"])
        self.assertTrue(result["value"]["basis_stale"], result)
        self.assertEqual(result["value"]["commits"][0]["commit_id"], applied["value"]["commits"][0][1])
        self.assertNotEqual(result["value"]["commits"][0]["commit_id"], self.head()["commit_id"])
        self.assertEqual(before, self.hashes())

    def test_review_status_is_unknown_when_pending_then_reads_real_retraction(self):
        scope = replace(self.scope, owner_ids=(self.fx.owner_ids["A"],), kinds=("event",))
        plan = self.reviewed(self.plan(("A.event",), scope), ("A.event",), action="retract")
        self.apply(plan)
        pending = self.status(plan["plan_id"], scope=scope)
        self.assertTrue(pending["value"]["review_states"], pending)
        self.assertTrue(all(row["validity"] != "valid" for row in pending["value"]["review_states"]))
        index.sync_owner(self.root, self.fx.owner_ids["A"], vector="off")
        before = self.hashes()
        with patch.object(index, "sync_owner", side_effect=AssertionError("status must not index")):
            ready = self.status(plan["plan_id"], scope=scope)
        withdrawn = next(row for row in ready["value"]["review_states"] if row["ref"]["id"] == self.fx.claims["accepted"])
        self.assertEqual(withdrawn["review_state"], "retracted", ready)
        self.assertEqual(withdrawn["validity"], "invalid")
        self.assertEqual(before, self.hashes())


if __name__ == "__main__":
    unittest.main()
