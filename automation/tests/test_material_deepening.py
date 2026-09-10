"""P3 实际关系/版本/预算回归，使用公开 memory 提交产生的隔离 F1。

每个测试复制自己拥有的合成基线，决策测试走真实公开写入，绝不改 SQLite
投影或冻结夹具来制造成功。这里只证明软件边界，不证明领域机制可迁移。
"""
from copy import copy, deepcopy
from dataclasses import asdict
from pathlib import Path
import json
import shutil
import tempfile
import unittest
import uuid
from unittest.mock import patch

import material_query_fixture as fixture
from memory import api
from memory.service import MemoryService
from material_query import associations, deepening
from material_query.contracts import GraphEdge, Scope
from material_query.coordinator import Coordinator
from material_query.validation import parse
from material_query.wire import json_value


class MaterialDeepeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="material-deepening-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = fixture.materialize(Path(cls.temp.name) / "baseline 中文", isolation_root=cls.temp.name)

    def setUp(self):
        self.fx = copy(self.base)
        self.fx.root = Path(self.temp.name) / self._testMethodName
        shutil.copytree(self.base.root, self.fx.root)
        self.fx.records = deepcopy(self.base.records)
        self.fx.refs = deepcopy(self.base.refs)
        self.fx.record_ids = dict(self.base.record_ids)
        self.fx.receipts = list(self.base.receipts)
        self.fx.service = MemoryService(self.fx.root)
        self.coordinator = Coordinator(self.fx.root)
        self.addCleanup(self.coordinator.executor.shutdown, wait=True)

    def request(self, key, *, scope=None, ceiling=None, association=None, limit=20, budget=None, definition="full", purpose="exploration"):
        empty = json_value(Scope(None, None, None, None, None, None, None, True, (), (), None, None))
        self.request_value = {
            "definition": {"key": definition, "version": "1"}, "question": self.fx.record_ids[key], "keywords": [],
            "scope": scope or deepcopy(empty), "scope_ceiling": ceiling or deepcopy(empty), "purpose": purpose,
            "association": association or {"mode": "off", "strategy": "existing-relations", "strategy_version": "1",
                "max_items": 5, "output_share": 0.25, "supplement_scope": None},
            "budget": {"wall_ms": 30000, "read_bytes": 16 * 1024 * 1024, "output_chars": 40000,
                       "candidates": 300, "graph_nodes": 50, "graph_edges": 100, "graph_hops": 4, "model_tokens": 0,
                       **(budget or {})},
            "freshness": "fixed", "result_limit": limit, "missing_policy": "reject", "fallback_definitions": [],
            "applicability": fixture.SCOPE if purpose == "formal" else "", "channels": ["identity"]}
        result = self.coordinator.search(self.request_value)
        self.assertIn(result["status"], {"ok", "partial"}, result)
        self.assertTrue(result["value"]["candidates"], result)
        self.search = result["value"]
        return result

    def deepen(self, *, mode="bounded_graph", direction="forward", kinds=(), cursor=None, ids=None, strategy="bounded-bfs"):
        return deepening.deepen(self.coordinator, {"query_id": self.search["query_id"],
            "candidate_ids": ids or [self.search["candidates"][0]["candidate_id"]], "mode": mode,
            "relation_kinds": list(kinds), "direction": direction, "strategy": strategy,
            "strategy_version": "1", "cursor": cursor})

    def test_source_mapping_preserves_document_revision_block_and_original(self):
        self.request("A.process")
        result = self.deepen(mode="source_mapping")
        self.assertIn(result["status"], {"ok", "partial"}, result)
        refs = [ref for item in result["value"]["candidates"] for ref in item["refs"]]
        old_units = [ref for ref in refs if ref["id"] == self.fx.record_ids["A.unit"]]
        self.assertTrue(old_units, result)
        self.assertEqual({ref["revision"] for ref in old_units}, {1})
        self.assertIn("block:m", {ref["locator"] for ref in old_units})
        self.assertIn("block:d", {ref["locator"] for ref in old_units})
        self.assertNotIn(None, {ref["locator"] for ref in old_units})
        self.assertTrue(any(ref["kind"] == "file" and ref["id"] == self.fx.sources["A"]["source_id"] for ref in refs))
        self.assertTrue(any(edge["source"]["id"] == self.fx.record_ids["A.process_section.r1"] and
                            edge["target"]["locator"] == "block:m" for edge in result["value"]["edges"]))

    def test_reverse_prerequisite_is_verified_from_canonical_sources(self):
        self.request("B.unit")
        result = self.deepen(direction="reverse", kinds=("depends_on",))
        self.assertIn(result["status"], {"ok", "partial"}, result)
        edges = result["value"]["edges"]
        self.assertTrue(any(edge["source"]["id"] == self.fx.record_ids["A.unit"] and
            edge["target"]["id"] == self.fx.record_ids["B.unit"] and edge["kind"] == "depends_on" and
            edge["proposer"] == "canonical:sources:prerequisite" for edge in edges), result)

    def test_relation_filter_and_direction_do_not_add_reverse_edge(self):
        self.request("B.experience")
        forward = self.deepen(direction="forward", kinds=("similar_structure",))
        self.assertFalse(forward["value"]["edges"], forward)
        reverse = self.deepen(direction="reverse", kinds=("similar_structure",))
        self.assertTrue(any(edge["source"]["id"] == self.fx.record_ids["A.experience"] for edge in reverse["value"]["edges"]), reverse)
        self.request("A.experience")
        filtered = self.deepen(kinds=("depends_on",))
        self.assertTrue(all(edge["kind"] == "depends_on" for edge in filtered["value"]["edges"]), filtered)
        self.assertFalse(any(edge["target"]["id"] == self.fx.record_ids["B.experience"] for edge in filtered["value"]["edges"]), filtered)

    def test_legacy_relations_keep_parallel_edges_and_explicit_evidence_links(self):
        # Commit four different authored relations to the same fixed endpoint.
        # The node is shared, but no relation may be erased by node deduplication
        # or renamed to depends_on merely to fit the newer graph vocabulary.
        kinds = ("references", "input", "same_entity", "mentions")
        self.fx.revise("relations.a", "A.experience", sources=[
            self.fx.source_ref("A"), *(self.fx.ref("B.experience", kind) for kind in kinds)])
        self.request("relations.a")
        result = self.deepen(kinds=kinds)
        self.assertIn(result["status"], {"ok", "partial"}, result)
        edges = [edge for edge in result["value"]["edges"]
                 if edge["source"]["id"] == self.fx.record_ids["relations.a"]
                 and edge["target"]["id"] == self.fx.record_ids["B.experience"]]
        self.assertEqual({edge["kind"] for edge in edges}, set(kinds), result)
        self.assertEqual(len({edge["edge_id"] for edge in edges}), 4)
        self.assertEqual(sum(item["refs"][0]["id"] == self.fx.record_ids["B.experience"]
                             for item in result["value"]["candidates"]), 1)
        for edge in edges:
            self.assertEqual(edge["legacy_relation"], "sources:" + edge["kind"])
            self.assertEqual(edge["evidence_relations"], ["references"])
            self.assertEqual(edge["state"], "accepted_navigation")
            self.assertEqual(parse(edge, GraphEdge).target.sha256, self.fx.ref("B.experience")["sha256"])
        self.assertEqual(self.deepen(kinds=("unregistered_relation",))["code"], "VALIDATION")

    def test_same_title_fixed_entities_are_not_merged_by_navigation(self):
        original = self.fx.records["B.experience"]
        for suffix in ("left", "right"):
            draft = fixture._draft(self.fx, "B", "experience", "同名但不同的合成实体",
                deepcopy(original["payload"]), sources=original["sources"], body=original["body_markdown"])
            self.fx.commit_draft("name." + suffix, draft)
        self.fx.revise("names.a", "A.experience", sources=[self.fx.source_ref("A"),
            self.fx.ref("name.left", "references"), self.fx.ref("name.right", "references")])
        self.request("names.a")
        result = self.deepen(kinds=("references",))
        self.assertIn(result["status"], {"ok", "partial"}, result)
        wanted = {self.fx.record_ids[key] for key in ("name.left", "name.right")}
        nodes = [item for item in result["value"]["candidates"] if item["refs"][0]["id"] in wanted]
        self.assertEqual(len(nodes), 2, result)
        self.assertEqual({item["refs"][0]["id"] for item in nodes}, wanted)
        self.assertEqual(len({item["candidate_id"] for item in nodes}), 2)

    def test_unmapped_canonical_relation_is_a_gap_not_an_invented_dependency(self):
        # background remains a legal old content reference. No registered graph
        # meaning exists for it, so report that limitation without inventing a
        # dependency or leaking the omitted endpoint in the diagnostic.
        self.fx.revise("unmapped.a", "A.experience", sources=[self.fx.source_ref("A"),
            self.fx.ref("B.experience", "background")])
        self.request("unmapped.a")
        result = self.deepen()
        self.assertEqual(result["status"], "partial", result)
        self.assertTrue(any("图关系映射" in text for text in result["warnings"]))
        self.assertFalse(any(edge["target"]["id"] == self.fx.record_ids["B.experience"]
                             and edge["state"] in {"accepted_navigation", "verified_claim"}
                             for edge in result["value"]["edges"]), result)
        self.assertFalse(any(edge["legacy_relation"] == "sources:background"
                             for edge in result["value"]["edges"]), result)

    def test_existing_association_uses_explicit_supplement_scope_and_ceiling(self):
        empty = json_value(Scope(None, None, None, None, None, None, None, True, (), (), None, None))
        main = {**empty, "owner_ids": [self.fx.owner_ids["A"]]}
        supplement = {**empty, "owner_ids": [self.fx.owner_ids["B"]]}
        options = {"mode": "existing_only", "strategy": "existing-relations", "strategy_version": "1",
                   "max_items": 2, "output_share": 0.3, "supplement_scope": supplement}
        result = self.request("A.experience", scope=main, association=options)
        self.assertTrue(any(item["group"] == "association" and item["refs"][0]["id"] == self.fx.record_ids["B.experience"]
                            for item in result["value"]["candidates"]), result)
        limited = self.request("A.experience", scope=main, ceiling=main, association=options)
        self.assertFalse(any(item["group"] == "association" for item in limited["value"]["candidates"]), limited)

    def test_stale_existing_edge_is_gap_and_not_reused(self):
        self.request("A.unit")
        result = self.deepen(direction="both", kinds=("similar_structure",))
        self.assertIn("旧修订", json.dumps(result["warnings"], ensure_ascii=False), result)
        self.assertTrue(result["value"]["edges"], result)
        self.assertTrue(all(edge["state"] == "stale" for edge in result["value"]["edges"]), result)
        self.assertFalse(result["value"]["candidates"], result)

    def test_excluded_node_is_not_a_bridge_or_a_basis_entry(self):
        self.fx.association("excluded.bc", "B.experience", "C.no_edge_positive")
        scope = json_value(Scope(None, None, None, None, None, None, None, True, (), (), None, None))
        scope["exclude_ids"] = [self.fx.record_ids["B.experience"]]
        self.request("A.experience", scope=scope)
        result = self.deepen(direction="both", kinds=("similar_structure",))
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(self.fx.record_ids["B.experience"], serialized)
        self.assertNotIn(self.fx.record_ids["C.no_edge_positive"], serialized)
        self.assertFalse(result["value"]["candidates"], result)

    def test_ceiling_filters_graph_content_and_basis(self):
        ceiling = json_value(Scope((self.fx.owner_ids["A"],), None, None, None, None, None, None, True, (), (), None, None))
        self.request("A.experience", ceiling=ceiling)
        result = self.deepen(kinds=("similar_structure",))
        self.assertNotIn(self.fx.record_ids["B.experience"], json.dumps(result, ensure_ascii=False))
        self.assertFalse(result["value"]["candidates"], result)

    def test_cancel_and_busy_query_reject_without_new_work(self):
        self.request("A.experience")
        state = self.coordinator.store.get(self.search["query_id"])
        before = state.ledger.snapshot()["candidates"]
        with state.lock:
            busy = self.deepen()
        self.assertEqual(busy["code"], "CONFLICT", busy)
        self.coordinator.cancel(self.search["query_id"])
        cancelled = self.deepen()
        self.assertEqual(cancelled["code"], "CANCELLED", cancelled)
        self.assertEqual(cancelled["consumed"]["candidates"], before)

    def test_cycles_diamonds_and_cursor_share_unique_budget(self):
        self.fx.association("cycle.bc", "B.experience", "C.no_edge_positive")
        self.fx.association("diamond.ac", "A.experience", "C.no_edge_positive")
        self.fx.association("cycle.ca", "C.no_edge_positive", "A.conflict")
        self.fx.association("cycle.da", "A.conflict", "A.experience")
        self.request("A.experience", limit=1, budget={"graph_hops": 3})
        pages, cursor, counts = [], None, []
        for _ in range(12):
            result = self.deepen(direction="both", kinds=("similar_structure",), cursor=cursor)
            self.assertIn(result["status"], {"ok", "partial"}, result)
            pages.append(result["value"])
            counts.append(result["consumed"]["graph_nodes"])
            cursor = result["value"]["next_cursor"]
            if cursor is None:
                break
        self.assertIsNone(cursor, "循环图必须终止")
        self.assertEqual(counts, sorted(counts))
        refs = [tuple((ref["id"], ref["revision"], ref["sha256"], ref["locator"])) for page in pages for item in page["candidates"] for ref in item["refs"]]
        self.assertEqual(len(refs), len(set(refs)))
        self.assertEqual(counts[-1], 4)
        before = result["consumed"]
        replay = self.deepen(direction="both", kinds=("similar_structure",))
        self.assertEqual(replay["value"], pages[0])
        self.assertEqual(replay["consumed"]["graph_nodes"], before["graph_nodes"])
        self.assertEqual(replay["consumed"]["graph_edges"], before["graph_edges"])

    def test_new_seed_does_not_reset_cumulative_hop_boundary(self):
        self.fx.association("hop.bc", "B.experience", "C.no_edge_positive")
        self.request("A.experience", budget={"graph_hops": 1})
        first = self.deepen(kinds=("similar_structure",))
        self.assertTrue(first["value"]["candidates"], first)
        second = self.deepen(kinds=("similar_structure",), ids=[first["value"]["candidates"][0]["candidate_id"]])
        self.assertEqual(second["consumed"]["graph_hops"], 1)
        self.assertFalse(second["value"]["candidates"], second)
        self.assertIn("深度边界", json.dumps(second["warnings"], ensure_ascii=False))

    def test_node_budget_exhaustion_is_explicit_and_never_reset(self):
        self.request("A.experience", budget={"graph_nodes": 1})
        first = self.deepen(kinds=("similar_structure",))
        self.assertEqual(first["code"], "BUDGET", first)
        self.assertEqual(first["consumed"]["graph_nodes"], 1)
        self.assertEqual(self.deepen(kinds=("similar_structure",))["code"], "BUDGET")
        second = self.deepen(direction="both", kinds=("similar_structure",))
        self.assertEqual(second["code"], "BUDGET", second)
        self.assertEqual(second["consumed"]["graph_nodes"], 1)

    def test_source_revocation_blocks_cached_cursor_and_hidden_details(self):
        self.request("A.experience", limit=1)
        first = self.deepen(kinds=("similar_structure",))
        self.assertTrue(first["value"]["candidates"], first)
        with self.fx.source_access("B", enabled=False):
            replay = self.deepen(kinds=("similar_structure",))
        self.assertEqual(replay["code"], "DENIED", replay)
        self.assertIsNone(replay["value"])
        self.assertNotIn(self.fx.records["B.experience"]["title"], json.dumps(replay, ensure_ascii=False))
        self.assertNotIn(fixture.HIDDEN_TITLE, json.dumps(replay, ensure_ascii=False))

    def test_decision_retries_are_idempotent_and_never_promote_review(self):
        self.request("A.experience", association={"mode": "existing_only", "strategy": "existing-relations",
            "strategy_version": "1", "max_items": 2, "output_share": 0.3, "supplement_scope": None})
        proposals = associations.discover(self.coordinator, {"query_id": self.search["query_id"],
            "seed_candidate_ids": [self.search["candidates"][0]["candidate_id"]], "profile": None})
        self.assertEqual(proposals["status"], "ok", proposals)
        self.assertEqual(len(proposals["value"]), 1, proposals)
        before = api.dispatch(self.fx.service, "inspect", {"owner_id": self.fx.owner_ids["A"]})["claim_states"]
        request = {"query_id": self.search["query_id"], "proposal_id": proposals["value"][0]["proposal_id"],
                   "decision": "accept_navigation", "reason": "只接受合成导航", "request_id": str(uuid.uuid4())}
        with patch("material_query.associations.api.dispatch", wraps=api.dispatch) as dispatched, patch(
                "memory.index.sync_owner", side_effect=AssertionError("导航决策不能隐式更新索引")):
            first = associations.decide(self.coordinator, request)
        self.assertEqual(dispatched.call_args.args[1], "commit")
        operation = dispatched.call_args.args[2]["operations"][0]
        self.assertEqual(operation["op"], "decide_association")
        self.assertEqual(operation["record_id"], self.fx.record_ids["edge.current"])
        for key in ("from", "to", "relation", "basis_refs", "transfer_limits"):
            self.assertEqual(operation["draft"]["payload"][key], self.fx.records["edge.current"]["payload"][key])
        self.assertEqual(first["status"], "partial", first)
        self.assertIn("关系索引", "".join(first["warnings"]))
        head = self.fx.head("A")
        second = associations.decide(self.coordinator, request)
        self.assertEqual(second["status"], "partial", second)
        self.assertEqual(self.fx.head("A"), head)
        self.assertEqual(first["value"], second["value"])
        after = api.dispatch(self.fx.service, "inspect", {"owner_id": self.fx.owner_ids["A"]})["claim_states"]
        self.assertEqual(before, after)
        conflict = associations.decide(self.coordinator, {**request, "decision": "reject"})
        self.assertEqual(conflict["code"], "CONFLICT", conflict)

    def test_no_model_structural_discovery_has_explicit_skill_entry(self):
        self.request("A.experience")
        result = self.deepen(mode="structural_discovery")
        self.assertEqual(result["code"], "UNSUPPORTED", result)
        self.assertIn("association-exploration/SKILL.md", json.dumps(result["warnings"], ensure_ascii=False))
        self.assertEqual(result["consumed"]["model_tokens"], 0)
        self.assertEqual(result["consumed"]["model_calls"], 0)
        self.assertIsNone(result["value"])

    def test_discover_cannot_bypass_original_off_switch(self):
        self.request("A.experience")
        result = associations.discover(self.coordinator, {"query_id": self.search["query_id"],
            "seed_candidate_ids": [self.search["candidates"][0]["candidate_id"]], "profile": None})
        self.assertEqual(result["code"], "VALIDATION", result)
        self.assertIsNone(result["value"])

    def test_formal_cached_deepening_rechecks_withdrawn_claim(self):
        # Both endpoints have independently reviewed synthetic claims. The
        # navigation itself still supplies no scientific support to either one.
        claim_id = "CLM-MQ-SECOND-REVIEWED"
        self.fx.commit_draft("A.second_event", fixture._draft(self.fx, "A", "event", "第二份合成已复核事件",
            fixture._event(self.fx, "A", [fixture._claim(self.fx, "A", claim_id, "第二份独立合成主张")]), body="第二份合成事件"))
        self.fx.review("A.second_review", "A.second_event", claim_id)
        self.fx.association("edge.two_reviewed", "A.event", "A.second_event")
        scope = json_value(Scope(None, None, None, None, None, ("accepted",), ("valid",), False, (), (), None, None))
        self.request("A.event", scope=scope, purpose="formal", budget={"graph_nodes": 200, "graph_edges": 500, "graph_hops": 6})
        first = self.deepen(kinds=("similar_structure",))
        self.assertIn(first["status"], {"ok", "partial"}, first)
        self.assertTrue(first["value"]["candidates"], first)
        self.assertTrue(any(item["evaluated_claim_refs"] for item in first["value"]["candidates"]), first)
        self.fx.review("A.second_review.withdrawn", "A.second_event", claim_id, "retracted")
        replay = self.deepen(kinds=("similar_structure",))
        self.assertEqual(replay["code"], "STALE", replay)
        self.assertIsNone(replay["value"])

    def test_unknown_strategy_and_foreign_cursor_are_rejected(self):
        self.request("A.experience")
        self.assertEqual(self.deepen(strategy="invented")["code"], "UNSUPPORTED")
        self.assertEqual(self.deepen(cursor=str(uuid.uuid4()))["code"], "EXPIRED")
        bad = self.deepen(mode="anything")
        self.assertEqual(bad["code"], "VALIDATION", bad)


if __name__ == "__main__":
    unittest.main()
