"""P0 底层运行适配回归：真实固定清单、公开 CAS、索引事务和有序路径。"""
from copy import copy, deepcopy
from pathlib import Path
import json
import shutil
import tempfile
import unittest
import uuid

import material_query_fixture as fixture
from memory import api, index
from memory.service import MemoryService
from material_query.coordinator import Coordinator
from material_query.contracts import Scope
from material_query.foundation import Foundation, METHOD_MAP
from material_query.legacy_adapter import fixed_record
from material_query.wire import json_value


class MaterialFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="material-foundation-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = fixture.materialize(Path(cls.temp.name) / "底层固定基线", isolation_root=cls.temp.name)

    def setUp(self):
        self.fx = copy(self.base)
        self.fx.root = Path(self.temp.name) / self._testMethodName
        shutil.copytree(self.base.root, self.fx.root)
        self.fx.records, self.fx.refs = deepcopy(self.base.records), deepcopy(self.base.refs)
        self.fx.record_ids, self.fx.receipts = dict(self.base.record_ids), list(self.base.receipts)
        self.fx.service = MemoryService(self.fx.root)
        self.coordinator = Coordinator(self.fx.root)
        self.addCleanup(self.coordinator.executor.shutdown, wait=True)
        self.foundation = Foundation(self.coordinator)
        self.query()

    def query(self, key="A.unit", *, limit=30, budget=None, purpose="exploration", source_ids=None, question=None, include_keys=(),
              owner_ids=None, ceiling_owner_ids=None):
        scope = json_value(Scope(None, None, None, None, None, None, None, True, (), (), None, None))
        scope["source_ids"] = source_ids
        scope["owner_ids"] = owner_ids
        scope["include_refs"] = [self.ref(key) for key in include_keys]
        ceiling = deepcopy(scope)
        if ceiling_owner_ids is not None:
            ceiling["owner_ids"] = ceiling_owner_ids
        request = {"definition": {"key": "full", "version": "1"}, "question": question or self.fx.record_ids[key], "keywords": [],
            "scope": scope, "scope_ceiling": ceiling, "purpose": purpose,
            "association": {"mode": "off", "strategy": "existing-relations", "strategy_version": "1", "max_items": 2,
                            "output_share": 0.15, "supplement_scope": None},
            "budget": {"wall_ms": 90000, "read_bytes": 28 * 1024 * 1024, "output_chars": 80000,
                       "candidates": 1500, "graph_nodes": 200, "graph_edges": 500, "graph_hops": 6, "model_tokens": 0, **(budget or {})},
            "freshness": "fixed", "result_limit": limit, "missing_policy": "reject", "fallback_definitions": [],
            "applicability": fixture.SCOPE if purpose == "formal" else "", "channels": ["identity"]}
        result = self.coordinator.search(request)
        self.assertIn(result["status"], {"ok", "partial"}, result)
        self.assertTrue(result["value"]["candidates"], result)
        self.search = result["value"]
        self.qid = self.search["query_id"]

    def call(self, action, **values):
        return self.foundation.dispatch(action, {"query_id": self.qid, **values})

    def ref(self, key, locator=None):
        return json_value(fixed_record(self.fx.records[key], locator))

    def batch(self, key="A.experience", *, suffix=" added by foundation"):
        record = self.fx.records[key]
        permitted = {"schema_version", "owner_id", "kind", "title", "body_markdown", "keywords", "payload", "sources",
                     "provenance_gap", "record_reason", "change_reason", "sensitivity", "discovery"}
        draft = {name: deepcopy(value) for name, value in record.items() if name in permitted}
        draft["body_markdown"] += suffix
        draft["change_reason"] = "SYNTHETIC ONLY：验证固定底层写入"
        return {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": fixture.ACTOR,
                "owner_id": record["owner_id"], "expected_head": self.fx.head(record["owner_id"]),
                "operations": [{"op": "put_record", "record_id": record["record_id"], "expected_revision": record["revision"], "draft": draft}]}

    def all_pages(self, action="list-page", **options):
        ids, cursor, items = [], None, []
        for _ in range(30):
            result = self.call(action, limit=100, cursor=cursor, **options)
            self.assertEqual(result["status"], "ok", result)
            ids.append(result["value"]["page_id"])
            items.extend(result["value"]["items"])
            cursor = result["value"]["next_cursor"]
            if cursor is None:
                return ids, items
        self.fail("分页未终止")

    def test_all_43_methods_have_honest_runtime_ownership(self):
        self.assertEqual(len(METHOD_MAP), 43)
        result = self.foundation.dispatch("capabilities", {})
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(METHOD_MAP["ExecutionControl.reserve"], "reserve")
        self.assertEqual(METHOD_MAP["Reranker.rerank"], "rerank")
        self.assertEqual(self.call("reserve", amount=1)["code"], "VALIDATION")
        self.assertEqual(self.call("invented")["code"], "UNSUPPORTED")

    def test_legacy_definition_aliases_are_versioned_pure_and_usable_by_query(self):
        from material_query import api as query_api
        before = self.fx.head("A")
        for old, current in (("topic_synthesis", "topic"), ("domain_synthesis", "domain")):
            request = {"source_contract_version": "0.1", "key": old, "target_definition_version": "1"}
            result = query_api.dispatch(self.coordinator, "foundation/definition-resolve", request)
            self.assertEqual(result["status"], "ok", result)
            self.assertEqual(result["value"]["definition"], {"key": current, "version": "1"})
            self.assertEqual(result["value"]["source_key"], old)
            self.assertEqual(result["value"]["mapping_version"], "1")
            self.assertEqual(result["value"]["generation"], "draft_only")
            self.assertEqual(result["consumed"]["read_bytes"], 0)
            self.assertFalse(result["value"]["canonical"])
            # Exercise the resulting definition in an actual fixed-material
            # query. The alias must not bypass normal availability checks.
            query = json_value(self.coordinator.store.get(self.qid).request)
            query.update(definition=result["value"]["definition"], question=self.fx.record_ids["A.map"])
            searched = self.coordinator.search(query)
            self.assertIn(searched["status"], {"ok", "partial"}, searched)
            self.assertTrue(searched["value"]["candidates"], searched)
            self.assertEqual(searched["value"]["candidates"][0]["realization"]["definition"], result["value"]["definition"])
            for changed in ({"key": "topic-synthesis"}, {"source_contract_version": "0.2"}, {"target_definition_version": "999"}):
                rejected = query_api.dispatch(self.coordinator, "foundation/definition-resolve", {**request, **changed})
                self.assertEqual(rejected["code"], "UNSUPPORTED", rejected)
        self.assertEqual(before, self.fx.head("A"))
        caps = query_api.dispatch(self.coordinator, "foundation/capabilities", {})["value"]
        self.assertEqual(caps["model_providers"], [])
        self.assertEqual(caps["tokenizers"], [])
        self.assertEqual(self.coordinator.capabilities()["tokenizers"], [])

    def test_public_reservation_settlement_is_bound_and_allowed_after_cancel(self):
        reserved = self.call("reserve", ceiling={"rerank_items": 0, "read_bytes": 100})
        self.assertEqual(reserved["status"], "ok", reserved)
        token = reserved["value"]["reservation"]
        wrong = deepcopy(token)
        wrong["budget_handle"] = "another-query"
        self.assertEqual(self.call("settle", reservation=wrong, actual={})["code"], "DENIED")
        self.coordinator.cancel(self.qid)
        settled = self.call("settle", reservation=token, actual={"read_bytes": 30})
        self.assertEqual(settled["status"], "ok", settled)
        self.assertEqual(settled["value"]["released"]["read_bytes"], 70)
        again = self.call("settle", reservation=token, actual={"read_bytes": 30})
        self.assertEqual(again["value"], settled["value"])
        self.assertEqual(self.call("settle", reservation=token, actual={"read_bytes": 31})["code"], "CONFLICT")

    def test_rerank_only_uses_provided_fixed_slices_and_preserves_evidence(self):
        self.query(question="MQ_A_METHOD_R2", include_keys=("A.event", "A.unit"), budget={"rerank_items": 10})
        candidates = {item["refs"][0]["id"]: item for item in self.search["candidates"]}
        original = [candidates[self.fx.record_ids[key]] for key in ("A.event", "A.unit")]
        read = self.call("read", refs=[self.ref("A.event"), self.ref("A.unit")])
        self.assertEqual(read["status"], "ok", read)
        candidate_refs = {item["refs"][0]["id"] for item in original}
        slice_ids = [item["slice_id"] for item in read["value"]["items"] if item["ref"]["id"] in candidate_refs]
        args = {"candidate_ids": [item["candidate_id"] for item in original], "text_slice_ids": slice_ids,
                "strategy": "term-overlap", "strategy_version": "1"}
        first = self.call("rerank", **args)
        self.assertEqual(first["status"], "ok", first)
        self.assertEqual(first["value"]["candidates"][0], original[1])
        self.assertEqual(first["value"]["candidates"][1], original[0])
        self.assertEqual(first["consumed"]["rerank_items"], 2)
        self.assertEqual(first["consumed"]["model_calls"], 0)
        second = self.call("rerank", **{**args, "strategy": "exact-phrase"})
        self.assertEqual(second["status"], "ok", second)
        self.assertEqual(second["value"]["candidates"], first["value"]["candidates"])
        self.assertEqual(second["consumed"]["rerank_items"], 4)
        self.assertEqual(self.call("rerank", **{**args, "strategy": "unconfigured-model"})["code"], "UNSUPPORTED")
        self.assertEqual(self.call("rerank", **{**args, "text_slice_ids": ["forged-slice"]})["code"], "EXPIRED")
        # The read batch also contains B's required definition. Explicitly
        # adding that third material cannot enlarge the reranker candidate set.
        all_slices = [item["slice_id"] for item in read["value"]["items"]]
        self.assertGreater(len(all_slices), len(slice_ids))
        self.assertEqual(self.call("rerank", **{**args, "text_slice_ids": all_slices})["code"], "DENIED")

    def test_rerank_reports_missing_text_provider_failure_and_zero_budget(self):
        candidate_id = self.search["candidates"][0]["candidate_id"]
        args = {"candidate_ids": [candidate_id], "text_slice_ids": [], "strategy": "term-overlap", "strategy_version": "1"}
        missing = self.call("rerank", **args)
        self.assertEqual(missing["status"], "partial", missing)
        self.assertEqual(missing["value"]["missing_text"], [candidate_id])
        self.assertEqual(missing["consumed"]["rerank_items"], 0)
        read = self.call("read", refs=[self.ref("A.unit")])
        args["text_slice_ids"] = [item["slice_id"] for item in read["value"]["items"] if item["ref"]["id"] == self.fx.record_ids["A.unit"]]
        self.assertEqual(self.call("rerank", **args)["code"], "BUDGET")
        self.query(budget={"rerank_items": 2})
        candidate_id = self.search["candidates"][0]["candidate_id"]
        read = self.call("read", refs=[self.ref("A.unit")])
        def failed_provider(_question, _text):
            raise RuntimeError("SYNTHETIC provider failure")
        self.foundation.rerankers[("term-overlap", "1")] = failed_provider
        result = self.call("rerank", candidate_ids=[candidate_id], text_slice_ids=[item["slice_id"] for item in read["value"]["items"] if item["ref"]["id"] == self.fx.record_ids["A.unit"]],
                           strategy="term-overlap", strategy_version="1")
        self.assertEqual(result["status"], "partial", result)
        self.assertEqual(result["value"]["failed_items"], [candidate_id])
        self.assertEqual(result["consumed"]["rerank_items"], 1)
        self.assertEqual(result["value"]["candidates"][0]["evidence_status"], self.search["candidates"][0]["evidence_status"])

    def test_rerank_cancellation_preserves_completed_scores_and_releases_hold(self):
        self.query(question="MQ_A_METHOD_R2", include_keys=("A.event", "A.unit"), budget={"rerank_items": 2})
        candidate_ids = [item["candidate_id"] for item in self.search["candidates"]]
        read = self.call("read", refs=[self.ref("A.event"), self.ref("A.unit")])
        inputs = {self.fx.record_ids["A.event"], self.fx.record_ids["A.unit"]}
        def stopping_provider(_question, _text):
            self.coordinator.cancel(self.qid)
            return 1.0
        self.foundation.rerankers[("term-overlap", "1")] = stopping_provider
        result = self.call("rerank", candidate_ids=candidate_ids,
            text_slice_ids=[item["slice_id"] for item in read["value"]["items"] if item["ref"]["id"] in inputs],
            strategy="term-overlap", strategy_version="1")
        self.assertEqual(result["status"], "cancelled", result)
        self.assertEqual(result["code"], "CANCELLED", result)
        self.assertEqual(len(result["value"]["scores"]), 1)
        self.assertEqual(result["consumed"]["rerank_items"], 1)
        self.assertEqual(self.coordinator.store.get(self.qid).ledger.held["rerank_items"], 0)

    def test_describe_and_resolve_keep_fixed_revision_and_relation(self):
        before = self.fx.head("A")
        result = self.call("describe", refs=[self.ref("A.unit.r1")])
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["value"]["items"][0]["ref"]["revision"], 1)
        legacy = self.fx.ref("A.unit.r1", "prerequisite")
        legacy["sha256"] = None
        resolved = self.call("resolve", refs=[legacy])
        self.assertEqual(resolved["value"]["links"][0]["relation"], "prerequisite")
        self.assertEqual(resolved["value"]["links"][0]["target"]["sha256"], self.fx.records["A.unit.r1"]["record_hash"])
        self.assertEqual(self.fx.head("A"), before)

    def test_manifest_content_page_survives_missing_search_index(self):
        # Only remove the derived database in this test's owned synthetic clone.
        path = index.database_path(self.fx.root)
        self.assertTrue(path.is_relative_to(self.fx.root))
        path.unlink()
        pages, items = self.all_pages(owner_ids=[self.fx.owner_ids["A"]])
        self.assertTrue(pages)
        self.assertIn(self.fx.record_ids["A.process"], {row["ref"]["id"] for row in items})
        self.assertNotIn("MQ_A_METHOD_R", json.dumps(items, ensure_ascii=False))

    def test_claim_resolver_uses_canonical_container_after_index_loss(self):
        legacy = {"target_kind": "claim", "target_id": self.fx.claims["accepted"], "revision": None,
                  "sha256": None, "locator": "", "relation": "supports"}
        expected = self.call("resolve", refs=[legacy])
        self.assertEqual(expected["status"], "ok", expected)
        index.database_path(self.fx.root).unlink()
        resolved = self.call("resolve", refs=[legacy])
        self.assertEqual(resolved["status"], "ok", resolved)
        self.assertEqual(resolved["value"], expected["value"])

    def test_missing_index_claim_dependency_uses_ceiling_beyond_primary_scope(self):
        self.query("B.experience", owner_ids=[self.fx.owner_ids["B"]],
                   ceiling_owner_ids=[self.fx.owner_ids["A"], self.fx.owner_ids["B"]])
        index.database_path(self.fx.root).unlink()
        _pages, items = self.all_pages(owner_ids=[self.fx.owner_ids["B"]])
        self.assertIn(self.fx.record_ids["B.review.superseded"], {item["ref"]["id"] for item in items})
        self.assertEqual({item["owner_id"] for item in items}, {self.fx.owner_ids["B"]})

    def test_direct_source_read_respects_original_scope_and_formal_purpose(self):
        self.query(source_ids=[self.fx.sources["A"]["source_id"]])
        legacy = self.fx.source_ref("B")
        ref = {"kind": "file", "id": legacy["target_id"], "revision": legacy["revision"],
               "sha256": legacy["sha256"], "locator": legacy["locator"]}
        for action, refs in (("resolve", [legacy]), ("read", [ref])):
            denied = self.call(action, refs=refs)
            self.assertEqual(denied["code"], "DENIED", denied)
            self.assertIsNone(denied["value"])
        self.query("A.event", purpose="formal")
        original = self.fx.source_ref("A")
        ref = {"kind": "file", "id": original["target_id"], "revision": None,
               "sha256": original["sha256"], "locator": original["locator"]}
        rejected = self.call("read", refs=[ref])
        self.assertEqual(rejected["code"], "UNSUPPORTED", rejected)

    def test_formal_candidate_operations_recheck_withdrawn_review(self):
        self.query("A.event", purpose="formal")
        candidate_ids = [self.search["candidates"][0]["candidate_id"]]
        initial = self.call("deduplicate", candidate_ids=candidate_ids)
        self.assertEqual(initial["status"], "ok", initial)
        self.fx.review("A.review.withdrawn.foundation", "A.event", self.fx.claims["accepted"], "retracted")
        for action, extra in (("deduplicate", {}), ("select", {"limit": 1})):
            rejected = self.call(action, candidate_ids=candidate_ids, **extra)
            self.assertEqual(rejected["code"], "STALE", rejected)
            self.assertIsNone(rejected["value"])

    def test_fixed_history_cursor_does_not_shift_when_head_advances(self):
        first = self.call("history", owner_id=self.fx.owner_ids["A"], limit=1, cursor=None)
        self.assertEqual(first["status"], "ok", first)
        cursor = first["value"]["next_cursor"]
        self.fx.revise("A.experience.changed", "A.experience", body_markdown="新 HEAD 的合成变化")
        new_commit = self.fx.head("A")
        second = self.call("history", owner_id=self.fx.owner_ids["A"], limit=1, cursor=cursor)
        self.assertEqual(second["status"], "ok", second)
        self.assertNotIn(new_commit, {row["commit_id"] for row in second["value"]["items"]})
        replay = self.call("history", owner_id=self.fx.owner_ids["A"], limit=1, cursor=None)
        self.assertEqual(replay["value"], first["value"])
        self.assertGreater(replay["consumed"]["read_bytes"], first["consumed"]["read_bytes"])

    def test_source_read_and_representation_build_are_read_only(self):
        before = self.fx.head("A")
        plan = self.call("representation-plan", refs=[self.ref("A.unit.r1", "block:m")], definition={"key": "section", "version": "1"})
        self.assertEqual(plan["status"], "ok", plan)
        built = self.call("representation-build", plan_id=plan["value"]["plan_id"], expected_digest=plan["value"]["plan_digest"])
        self.assertEqual(built["status"], "ok", built)
        text = json.dumps(built["value"], ensure_ascii=False)
        self.assertIn("MQ_A_DEFINITION", text)
        self.assertIn("MQ_A_METHOD_R1", text)
        self.assertNotIn("MQ_A_METHOD_R2", text)
        self.assertNotIn("MQ_A_RESULT_R1", text)
        self.assertFalse(built["value"]["canonical"])
        self.assertEqual(self.fx.head("A"), before)

    def test_validate_apply_binding_cas_and_idempotency(self):
        batch = self.batch()
        validation = self.call("validate", batch=batch, basis_refs=[self.ref("A.experience")])
        self.assertEqual(validation["status"], "ok", validation)
        self.assertEqual(self.fx.head("A"), batch["expected_head"])
        values = {"validation_handle": validation["value"]["validation_handle"], "expected_batch_sha256": validation["value"]["batch_sha256"]}
        rejected = self.call("apply", **{**values, "expected_batch_sha256": "0" * 64})
        self.assertEqual(rejected["code"], "CONFLICT", rejected)
        saved = self.call("apply", **values)
        self.assertEqual(saved["status"], "partial", saved)
        self.assertEqual(saved["value"]["save_status"], "committed", saved)
        self.assertEqual(saved["value"]["index_status"], "pending", saved)
        head = self.fx.head("A")
        again = self.call("apply", **values)
        self.assertEqual(again["value"]["commit_id"], saved["value"]["commit_id"], again)
        self.assertEqual(self.fx.head("A"), head)
        conflict = self.call("commit", batch={**batch, "request_id": str(uuid.uuid4())})
        self.assertEqual(conflict["code"], "CONFLICT", conflict)

    def test_restore_creates_new_revision_and_rejects_later_changes(self):
        arguments = {"owner_id": self.fx.owner_ids["A"], "expected_head": self.fx.head("A"),
            "restore_refs": [self.ref("A.unit.r1")], "current_refs": [self.ref("A.unit.r2")],
            "reason": "SYNTHETIC ONLY 恢复旧参数并保留历史", "request_id": str(uuid.uuid4())}
        restored = self.call("restore", **arguments)
        self.assertEqual(restored["value"]["save_status"], "committed", restored)
        new = api.dispatch(self.fx.service, "inspect", {"owner_id": self.fx.owner_ids["A"], "record_id": self.fx.record_ids["A.unit"]})["record"]
        self.assertEqual(new["revision"], 3)
        self.assertEqual(new["payload"], self.fx.records["A.unit.r1"]["payload"])
        again = self.call("restore", **arguments)
        self.assertEqual(again["value"]["commit_id"], restored["value"]["commit_id"], again)
        conflict = self.call("restore", **{**arguments, "request_id": str(uuid.uuid4()), "expected_head": self.fx.head("A")})
        self.assertEqual(conflict["code"], "CONFLICT", conflict)

    def test_cross_owner_batch_and_hidden_owner_do_not_escape_scope(self):
        batch = self.batch()
        batch["operations"][0]["draft"]["owner_id"] = self.fx.owner_ids["B"]
        self.assertEqual(self.call("validate", batch=batch)["code"], "VALIDATION")
        hidden = self.call("list-page", owner_ids=[self.fx.owner_ids["X"]])
        self.assertEqual(hidden["code"], "DENIED", hidden)
        self.assertNotIn(fixture.HIDDEN_TITLE, json.dumps(hidden, ensure_ascii=False))

    def test_index_plan_requires_contiguous_complete_input_pages(self):
        first = self.call("list-page", owner_ids=[self.fx.owner_ids["A"]], limit=1, cursor=None)
        plan = self.call("index-plan", mode="rebuild", page_ids=[first["value"]["page_id"]])
        self.assertEqual(plan["code"], "VALIDATION", plan)
        second = self.call("list-page", owner_ids=[self.fx.owner_ids["A"]], limit=1, cursor=first["value"]["next_cursor"])
        skipped = self.call("index-plan", mode="rebuild", page_ids=[second["value"]["page_id"]])
        self.assertEqual(skipped["code"], "VALIDATION", skipped)
        wrong = self.call("index-plan", mode="incremental", page_ids=[first["value"]["page_id"]])
        self.assertEqual(wrong["code"], "VALIDATION", wrong)

    def test_index_failure_retries_plan_without_second_content_commit(self):
        commit = self.call("commit", batch=self.batch())
        self.assertEqual(commit["value"]["save_status"], "committed", commit)
        head = self.fx.head("A")
        db = index.connect(self.fx.root, create=False)
        before = [tuple(row) for row in db.execute("SELECT entry_id,title,text FROM memory_fts ORDER BY entry_id")]
        old_vector = tuple(db.execute("SELECT vector_status,vector_generation,encoder_version FROM memory_index_state WHERE owner_id=?", (self.fx.owner_ids["A"],)).fetchone())
        db.close()
        page_ids, _ = self.all_pages("changes", owner_ids=[self.fx.owner_ids["A"]])
        plan = self.call("index-plan", mode="incremental", page_ids=page_ids)
        self.assertEqual(plan["status"], "ok", plan)
        def fault(point):
            if point == "fts_before_commit":
                raise OSError("synthetic controlled transaction fault")
        self.foundation.index_fault = fault
        fields = {"plan_id": plan["value"]["plan_id"], "expected_digest": plan["value"]["plan_digest"]}
        failed = self.call("index-execute", **fields)
        self.assertEqual(failed["status"], "partial", failed)
        self.assertEqual(failed["value"]["index_status"], "pending", failed)
        db = index.connect(self.fx.root, create=False)
        self.assertEqual([tuple(row) for row in db.execute("SELECT entry_id,title,text FROM memory_fts ORDER BY entry_id")], before)
        db.close()
        self.foundation.index_fault = None
        complete = self.call("index-execute", **fields)
        self.assertEqual(complete["status"], "ok", complete)
        self.assertEqual(complete["value"]["index_status"], "indexed", complete)
        self.assertEqual(complete["value"]["pending_events"], [])
        self.assertEqual(self.fx.head("A"), head)
        db = index.connect(self.fx.root, create=False)
        self.assertEqual(tuple(db.execute("SELECT vector_status,vector_generation,encoder_version FROM memory_index_state WHERE owner_id=?", (self.fx.owner_ids["A"],)).fetchone()), old_vector)
        db.close()
        again = self.call("index-execute", **fields)
        self.assertEqual(again["value"]["completed_events"], complete["value"]["completed_events"])
        self.assertEqual(self.fx.head("A"), head)

    def test_full_rebuild_uses_manifest_contents_after_index_loss(self):
        path = index.database_path(self.fx.root)
        path.unlink()
        page_ids, items = self.all_pages(owner_ids=[self.fx.owner_ids["A"]])
        plan = self.call("index-plan", mode="rebuild", page_ids=page_ids)
        self.assertEqual(plan["status"], "ok", plan)
        before = self.fx.head("A")
        done = self.call("index-execute", plan_id=plan["value"]["plan_id"], expected_digest=plan["value"]["plan_digest"])
        self.assertEqual(done["status"], "ok", done)
        db = index.connect(self.fx.root, create=False)
        ids = {row[0] for row in db.execute("SELECT record_id FROM memory_records WHERE owner_id=?", (self.fx.owner_ids["A"],))}
        db.close()
        self.assertTrue({item["ref"]["id"] for item in items} <= ids)
        self.assertEqual(self.fx.head("A"), before)

    def test_repair_rebuild_replace_corrupt_fts_text_without_content_write(self):
        page_ids, _ = self.all_pages(owner_ids=[self.fx.owner_ids["A"]])
        head = self.fx.head("A")
        db = index.connect(self.fx.root, create=False)
        expected = [tuple(row) for row in db.execute("SELECT entry_id,title,text FROM memory_fts ORDER BY entry_id")]
        target = db.execute("SELECT entry_id FROM memory_entries WHERE owner_id=? LIMIT 1", (self.fx.owner_ids["A"],)).fetchone()[0]
        db.close()
        for mode in ("repair", "rebuild"):
            # The owned synthetic database loses text only: entry count, IDs,
            # signatures and watermarks still look ready to a shallow check.
            db = index.connect(self.fx.root, create=False)
            db.execute("UPDATE memory_fts SET text=? WHERE entry_id=?", ("synthetic corrupt FTS text", target))
            db.commit()
            db.close()
            plan = self.call("index-plan", mode=mode, page_ids=page_ids)
            self.assertEqual(plan["status"], "ok", plan)
            done = self.call("index-execute", plan_id=plan["value"]["plan_id"], expected_digest=plan["value"]["plan_digest"])
            self.assertEqual(done["status"], "ok", done)
            db = index.connect(self.fx.root, create=False)
            actual = [tuple(row) for row in db.execute("SELECT entry_id,title,text FROM memory_fts ORDER BY entry_id")]
            db.close()
            self.assertEqual(actual, expected)
            self.assertEqual(self.fx.head("A"), head)

    def test_paths_are_ordered_fixed_and_target_constrained(self):
        self.fx.association("path.bc", "B.experience", "C.no_edge_positive")
        self.query("A.experience")
        result = self.call("paths", candidate_ids=[self.search["candidates"][0]["candidate_id"]],
            target_refs=[self.ref("C.no_edge_positive")], direction="forward", relation_kinds=["similar_structure"], cursor=None, limit=5)
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(len(result["value"]["paths"]), 1)
        path = result["value"]["paths"][0]
        self.assertEqual([ref["id"] for ref in path["refs"]], [self.fx.record_ids[key] for key in ("A.experience", "B.experience", "C.no_edge_positive")])
        edges = {edge["edge_id"]: edge for edge in result["value"]["edges"]}
        self.assertEqual(len(path["edge_ids"]), 2)
        for position, edge_id in enumerate(path["edge_ids"]):
            self.assertEqual(edges[edge_id]["source"], path["refs"][position])
            self.assertEqual(edges[edge_id]["target"], path["refs"][position + 1])
        self.assertTrue(path["conditions"])

    def test_rejected_wrong_connection_preserves_differences_without_becoming_a_path(self):
        # The recorded judgement is explicit synthetic input, not an automatic
        # scientific classifier. Save it through the public association action.
        # Put the endpoint in A explicitly: fixture labels beginning with C
        # name a record, not a third owner (the shared fixture has owners A/B).
        # This leaves the endpoint permitted while the intermediate B is denied.
        target = fixture._draft(self.fx, "A", "experience", "SYNTHETIC 允许的路径终点",
            deepcopy(self.fx.records["C.no_edge_positive"]["payload"]),
            sources=[self.fx.source_ref("A")], body="SYNTHETIC：独立终点，仅验证导航范围。")
        self.fx.commit_draft("wrong.target", target)
        self.fx.association("wrong.bc", "B.experience", "wrong.target")
        original = self.fx.records["edge.current"]
        difference = "SYNTHETIC：对象和延迟不同，不能迁移参数"
        rejection = "SYNTHETIC：同名词不代表同一机制，本连接已判错"

        def save_judgement(status, differences):
            payload = deepcopy(original["payload"])
            payload.update(status=status, differences=differences)
            saved = api.dispatch(self.fx.service, "associations-decide", {
                "request_id": str(uuid.uuid4()), "actor": fixture.ACTOR,
                "owner_id": original["owner_id"], "expected_head": self.fx.head("A"),
                "payload": payload, "title": original["title"], "reason": "SYNTHETIC C17 显式导航审查",
                "discovery": "workspace_summary"})
            self.assertEqual(saved["save_status"], "committed", saved)

        def paths():
            return self.call("paths", candidate_ids=[self.search["candidates"][0]["candidate_id"]],
                target_refs=[self.ref("wrong.target")], direction="forward",
                relation_kinds=["similar_structure"], cursor=None, limit=10)

        save_judgement("accepted", [difference])
        self.query("A.experience")
        accepted = paths()
        self.assertEqual(len(accepted["value"]["paths"]), 1, accepted)
        self.assertIn(difference, accepted["value"]["paths"][0]["differences"])
        save_judgement("rejected", [difference, rejection])
        # A previously paid page cannot keep an accepted edge after a real
        # canonical rejection. A new query may inspect its diagnostic state.
        self.assertEqual(paths()["code"], "STALE")
        self.query("A.experience")
        denied = paths()
        self.assertEqual(denied["status"], "partial", denied)
        self.assertEqual(denied["value"]["paths"], [])
        self.assertEqual(len(denied["value"]["edges"]), 1, denied)
        edge = denied["value"]["edges"][0]
        self.assertEqual(edge["state"], "retracted")
        self.assertEqual(edge["differences"], [difference, rejection])
        self.assertNotEqual(edge["state"], "verified_claim")
        # The rejected B connection is not a bridge to C, even though B→C is a
        # valid, accepted canonical association in the same fixture.
        self.assertNotIn(self.fx.record_ids["wrong.target"], {e["target"]["id"] for e in denied["value"]["edges"]})
        for boundary in ("exclude", "ceiling"):
            self.query("A.experience", ceiling_owner_ids=(self.fx.owner_ids["A"],) if boundary == "ceiling" else None)
            if boundary == "exclude":
                request = json_value(self.coordinator.store.get(self.qid).request)
                request["scope"]["excluded_owner_ids"] = [self.fx.owner_ids["B"]]
                result = self.coordinator.search(request)
                self.search, self.qid = result["value"], result["value"]["query_id"]
            hidden = paths()
            serialized = json.dumps(hidden, ensure_ascii=False)
            self.assertNotIn(self.fx.record_ids["B.experience"], serialized)
            self.assertNotIn(rejection, serialized)
            if hidden["value"] is None:
                # A denied candidate/endpoint may fail the whole operation;
                # fail-closed is also valid, provided no hidden detail escapes.
                self.assertEqual(hidden["code"], "DENIED", hidden)
            else:
                self.assertFalse(hidden["value"]["paths"], hidden)

    def test_dedup_and_selection_keep_original_evidence_status(self):
        self.query("A.experience")
        item = self.search["candidates"][0]
        dedup = self.call("deduplicate", candidate_ids=[item["candidate_id"], item["candidate_id"]])
        self.assertEqual(len(dedup["value"]["candidates"]), 1)
        chosen = self.call("select", candidate_ids=[item["candidate_id"]], limit=1)
        self.assertEqual(chosen["value"]["candidates"][0]["evidence_status"], item["evidence_status"])
        self.assertEqual(chosen["value"]["candidates"][0]["hits"], item["hits"])

    def test_cached_page_rechecks_source_revocation(self):
        first = self.call("list-page", owner_ids=[self.fx.owner_ids["A"]], limit=100, cursor=None)
        self.assertEqual(first["status"], "ok", first)
        with self.fx.source_access("A", enabled=False):
            denied = self.call("list-page", owner_ids=[self.fx.owner_ids["A"]], limit=100, cursor=None)
        self.assertEqual(denied["code"], "DENIED", denied)
        self.assertIsNone(denied["value"])


if __name__ == "__main__":
    unittest.main()
