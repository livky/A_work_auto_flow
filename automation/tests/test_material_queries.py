"""真实F1存储/FTS上的应用查询回归；不把接口存在当作功能通过。"""
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import unittest

from material_query_fixture import materialize, SCOPE
from material_query.budget import DEFAULT_BUDGET
from material_query.contracts import AssociationOptions, AssembleRequest, DefinitionRef, QueryRequest, Scope
from material_query.coordinator import Coordinator
from material_query.legacy_adapter import from_legacy
from material_query.wire import json_value


class MaterialQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.fx = materialize(Path(cls.temp.name) / "F1 查询", isolation_root=cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.coordinator = Coordinator(self.fx.root)
        scope = Scope((self.fx.owner_ids["A"],), None, None, None, None, None, None, False, (), (), None, None)
        self.request = QueryRequest(DefinitionRef("unit_digest", "1"), "反馈", (), scope, scope, "exploration",
            AssociationOptions("off", "existing-relations", "1", 2, 0.15, None), DEFAULT_BUDGET,
            "current", 20, "skip", (), "")

    def tearDown(self):
        self.coordinator.close()

    def search(self, request=None):
        return self.coordinator.search(json_value(request or self.request))

    def candidate_result(self):
        result = self.search()
        self.assertIn(result["status"], {"ok", "partial"}, result)
        self.assertTrue(result["value"]["candidates"], result)
        return result

    def test_real_fts_digest_and_selected_assembly(self):
        result = self.candidate_result()
        value = result["value"]
        candidate = value["candidates"][0]
        self.assertIn(candidate["realization"]["state"], {"direct", "assemblable"})
        assembled = self.coordinator.assemble(json_value(AssembleRequest(value["query_id"], (candidate["candidate_id"],), value["request_digest"])))
        self.assertIn(assembled["status"], {"ok", "partial"}, assembled)
        self.assertTrue(assembled["value"]["parts"])
        self.assertFalse(assembled["value"]["canonical"])
        self.assertTrue(assembled["value"]["contributors"])

    def test_empty_scope_is_empty_not_global(self):
        request = replace(self.request, scope=replace(self.request.scope, owner_ids=()))
        result = self.search(request)
        self.assertEqual(result["value"]["candidates"], [])

    def test_exclusion_dominates_include(self):
        ref, _ = from_legacy(self.fx.ref("A.unit"))
        scope = replace(self.request.scope, include_refs=(ref,), excluded_refs=(ref,))
        result = self.search(replace(self.request, scope=scope))
        self.assertNotIn(ref.id, {r["id"] for c in result["value"]["candidates"] for r in c["refs"]})

    def test_foreign_selection_and_digest_are_rejected(self):
        result = self.candidate_result()["value"]
        candidate = result["candidates"][0]["candidate_id"]
        bad = self.coordinator.assemble(json_value(AssembleRequest(result["query_id"], (candidate,), "wrong")))
        self.assertEqual(bad["code"], "CONFLICT")
        bad = self.coordinator.assemble(json_value(AssembleRequest(result["query_id"], ("foreign",), result["request_digest"])))
        self.assertEqual(bad["code"], "CONFLICT")

    def test_source_revocation_blocks_cached_search_and_assembly(self):
        value = self.candidate_result()["value"]
        with self.fx.source_access("A", enabled=False):
            result = self.coordinator.poll(value["query_id"])
            self.assertEqual(result["status"], "rejected", result)
            self.assertIsNone(result["value"])
            assembled = self.coordinator.assemble(json_value(AssembleRequest(value["query_id"], (value["candidates"][0]["candidate_id"],), value["request_digest"])))
            self.assertEqual(assembled["status"], "rejected", assembled)
            self.assertIsNone(assembled["value"])

    def test_zero_read_budget_does_not_open_record_body(self):
        result = self.search(replace(self.request, budget=replace(DEFAULT_BUDGET, read_bytes=0)))
        self.assertLessEqual(result["consumed"]["read_bytes"], 0)
        self.assertFalse(result.get("value") and result["value"]["candidates"])

    def test_cancel_and_expired_identity(self):
        state = self.coordinator._new(self.request)
        cancel = self.coordinator.cancel(state.query_id)
        self.assertEqual(cancel["status"], "cancelled")
        self.coordinator._run_search(state)
        self.assertEqual(state.result["status"], "cancelled")
        self.assertEqual(self.coordinator.poll("not-a-query")["code"], "EXPIRED")

    def test_optional_channel_degradation_survives_packet(self):
        result = self.search(replace(self.request, channels=("identity", "lexical", "sparse")))
        self.assertEqual(result["status"], "partial", result)
        value = result["value"]
        self.assertTrue(value["candidates"])
        assembled = self.coordinator.assemble(json_value(AssembleRequest(value["query_id"], (value["candidates"][0]["candidate_id"],), value["request_digest"])))
        self.assertEqual(assembled["status"], "partial", assembled)
        self.assertTrue(any("sparse" in warning for warning in assembled["warnings"]))
        self.assertFalse(assembled["value"]["complete"])

    def test_pluggable_ranking_keeps_fixed_identities(self):
        base = self.candidate_result()["value"]["candidates"]
        other = self.search(replace(self.request, ranking_strategy="rrf"))["value"]["candidates"]
        self.assertEqual({r["id"] for c in base for r in c["refs"]}, {r["id"] for c in other for r in c["refs"]})

    def test_fixed_old_revision_can_be_selected(self):
        ref, _ = from_legacy(self.fx.ref("A.unit.r1"))
        request = replace(self.request, question=ref.id, channels=("identity",), freshness="fixed",
                          scope=replace(self.request.scope, include_refs=(ref,)),
                          scope_ceiling=replace(self.request.scope_ceiling, owner_ids=(self.fx.owner_ids["A"], self.fx.owner_ids["B"])))
        result = self.search(request)
        self.assertTrue(result["value"]["candidates"], result)
        found = result["value"]["candidates"][0]["refs"][0]
        self.assertEqual(found["revision"], ref.revision)
        self.assertEqual(found["sha256"], ref.sha256)

    def test_formal_exact_claim_never_borrows_other_accepted_claim(self):
        request = replace(self.request, definition=DefinitionRef("full", "1"), purpose="formal", applicability=SCOPE,
                          question=self.fx.claims["unreviewed"], channels=("identity",), missing_policy="reject")
        result = self.search(request)
        self.assertEqual(result["value"]["candidates"], [], result)
        accepted = self.search(replace(request, question=self.fx.claims["accepted"]))
        self.assertTrue(accepted["value"]["candidates"], accepted)
        candidate = accepted["value"]["candidates"][0]
        self.assertEqual([r["id"] for r in candidate["evaluated_claim_refs"]], [self.fx.claims["accepted"]])
        receipt = accepted["value"]
        packet = self.coordinator.assemble(json_value(AssembleRequest(receipt["query_id"], (candidate["candidate_id"],), receipt["request_digest"])))
        self.assertTrue(packet["value"]["parts"], packet)
        statement = self.fx.records["A.event"]["payload"]["claims"][0]["statement"]
        self.assertIn(statement, str(packet["value"]["parts"]))
        self.assertNotIn(self.fx.records["A.event"]["payload"]["claims"][1]["statement"], str(packet["value"]["parts"]))

    def test_zero_output_budget_does_not_leak_unpaid_candidates(self):
        result = self.search(replace(self.request, budget=replace(DEFAULT_BUDGET, output_chars=0)))
        self.assertEqual(result["consumed"]["output_chars"], 0)
        self.assertFalse(result.get("value") and result["value"]["candidates"], result)

    def test_formal_cached_packet_is_rejected_after_real_review_withdrawal(self):
        request = replace(self.request, definition=DefinitionRef("full", "1"), purpose="formal", applicability=SCOPE,
                          question=self.fx.claims["accepted"], channels=("identity",), missing_policy="reject")
        result = self.search(request)
        receipt = result["value"]
        selected = AssembleRequest(receipt["query_id"], (receipt["candidates"][0]["candidate_id"],), receipt["request_digest"])
        self.assertTrue(self.coordinator.assemble(json_value(selected))["value"]["parts"])
        try:
            self.fx.review("A.review.dynamic.withdraw", "A.event", self.fx.claims["accepted"], "retracted")
            self.assertEqual(self.coordinator.poll(receipt["query_id"])["code"], "STALE")
            self.assertEqual(self.coordinator.assemble(json_value(selected))["code"], "STALE")
        finally:
            self.fx.review("A.review.dynamic.restore", "A.event", self.fx.claims["accepted"])

    def test_unregistered_repair_and_tolerance_are_not_ignored(self):
        self.assertEqual(self.search(replace(self.request, allow_index_repair=True))["code"], "UNSUPPORTED")
        self.assertEqual(self.search(replace(self.request, max_staleness_seconds=1.0))["code"], "UNSUPPORTED")

    def test_missing_representation_never_silently_renders_another_type(self):
        # A saved chapter has prose but no authored technical-unit digest. Reject
        # must expose that absence, skip removes it, and only explicit fallback
        # can select full. Use a ceiling which includes its actual prerequisites.
        ref = from_legacy(self.fx.ref("A.report_section.r2"))[0]
        request = replace(self.request, question=ref.id, channels=("identity",), missing_policy="reject",
                          scope_ceiling=replace(self.request.scope_ceiling, owner_ids=(self.fx.owner_ids["A"], self.fx.owner_ids["B"])))
        result = self.search(request)
        receipt = result["value"]
        self.assertEqual(result["status"], "partial", result)
        self.assertEqual(receipt["candidates"][0]["realization"]["state"], "needs_generation")
        packet = self.coordinator.assemble(json_value(AssembleRequest(receipt["query_id"], (receipt["candidates"][0]["candidate_id"],), receipt["request_digest"])))
        self.assertFalse(packet["value"]["complete"])
        self.assertFalse([part for part in packet["value"]["parts"] if part["group"] != "gaps"])
        issue = next(item for item in packet["issues"] if item["code"] == "SOURCE_MISSING")
        self.assertEqual(issue["affected_refs"][0]["id"], ref.id)
        self.assertEqual(issue["retry"], "after_external_change")
        self.assertTrue(packet["basis"]["basis_id"])
        self.assertTrue(packet["basis"]["observed_at"].endswith("Z"))
        self.assertEqual(self.search(replace(request, missing_policy="skip"))["value"]["candidates"], [])
        fallback = self.search(replace(request, missing_policy="fallback", fallback_definitions=(DefinitionRef("full", "1"),)))
        self.assertEqual(fallback["value"]["candidates"][0]["realization"]["definition"]["key"], "full")

    def test_equal_index_watermarks_do_not_hide_an_unindexed_head(self):
        from memory import index
        try:
            old_generation = self.fx.service.inspect(owner_id=self.fx.owner_ids["A"])["head"]["generation"]
            self.fx.revise("A.experience.unindexed", "A.experience", title="新增尚未索引的经验")
            db = index.connect(self.fx.root, create=False)
            with db:
                db.execute("UPDATE memory_index_state SET indexed_generation=?,target_generation=?,fts_status='indexed' WHERE owner_id=?",
                           (old_generation, old_generation, self.fx.owner_ids["A"]))
            db.close()
            result = self.search()
            self.assertIn("索引水位未完整覆盖当前内容", result["warnings"])
            self.assertEqual(result["status"], "partial")
        finally:
            index.reconcile(self.fx.root, vector="off")

    def test_explicit_block_locator_survives_selection_and_keeps_required_definition(self):
        ref = replace(from_legacy(self.fx.ref("A.unit.r2"))[0], locator="block:m")
        request = replace(self.request, definition=DefinitionRef("section", "1"), question=ref.id, channels=("identity",), freshness="fixed",
                          scope=replace(self.request.scope, include_refs=(ref,)),
                          scope_ceiling=replace(self.request.scope_ceiling, owner_ids=(self.fx.owner_ids["A"], self.fx.owner_ids["B"])))
        result = self.search(request)
        receipt = result["value"]
        candidate = receipt["candidates"][0]
        self.assertEqual(candidate["refs"][0]["locator"], "block:m")
        packet = self.coordinator.assemble(json_value(AssembleRequest(receipt["query_id"], (candidate["candidate_id"],), receipt["request_digest"])))
        selectors = [selector for part in packet["value"]["parts"] for selector in part["selectors"]]
        self.assertIn("detail.blocks.m", selectors)
        self.assertIn("detail.blocks.d", selectors)
        self.assertNotIn("detail.blocks.r", selectors)

    def test_retracted_review_filter_is_distinct_from_current_validity(self):
        scope = replace(self.request.scope, owner_ids=(self.fx.owner_ids["B"],), review_states=("retracted",), validities=("invalid",))
        request = replace(self.request, scope=scope, scope_ceiling=scope, definition=DefinitionRef("full", "1"),
                          question=self.fx.claims["retracted"], channels=("identity",), missing_policy="reject")
        result = self.search(request)
        self.assertTrue(result["value"]["candidates"], result)
        candidate = result["value"]["candidates"][0]
        self.assertEqual(candidate["evidence_status"], "retracted")
        self.assertEqual(candidate["evaluated_claim_refs"], [])
        self.assertEqual([r["id"] for r in candidate["unresolved_claim_refs"]], [self.fx.claims["retracted"]])
        denied = self.search(replace(request, scope=replace(scope, validities=("valid",))))
        self.assertEqual(denied["value"]["candidates"], [])

    def test_active_query_rejects_poll_and_resume_without_charging(self):
        result = self.candidate_result()
        state = self.coordinator.store.get(result["value"]["query_id"])
        before = state.ledger.snapshot()
        with state.lock:
            self.assertEqual(self.coordinator.poll(state.query_id)["code"], "CONFLICT")
            self.assertEqual(self.coordinator.resume(state.query_id, "unknown")["code"], "CONFLICT")
        self.assertEqual(state.ledger.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
