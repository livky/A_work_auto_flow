"""在真实合成存储/FTS上验证内容来源和固定展开，不生成业务材料。"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest

from material_query_fixture import materialize, _draft
from material_query.api import dispatch
from material_query.budget import DEFAULT_BUDGET
from material_query.contracts import AssociationOptions, DefinitionRef, QueryRequest, Scope
from material_query.coordinator import Coordinator
from material_query.wire import json_value
from memory.contracts import validate_record


class ContentQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.fx = fx = materialize(Path(cls.temp.name) / "内容来源 中文", isolation_root=cls.temp.name)
        technical = fx.ref("A.unit")
        technical["locator"] = "block:r"
        common = {"claims": [], "process_refs": [], "technical_refs": [technical], "experience_refs": [], "limitations": ["仅合成"]}
        narrative = _draft(fx, "A", "narrative", "反馈研究经过", {
            **common, "question": "如何控制反馈", "stages": [{"situation": "反馈振荡", "action": "降低增益",
                "reason": "检查延迟作用", "outcome": "保留边界", "evidence_refs": [fx.ref("A.unit")]}]}, body="反馈研究经过：尝试、失败和选择原因。")
        narrative["schema_version"] = 4
        fx.commit_draft("content.process", narrative)
        overview = _draft(fx, "A", "overview", "反馈研究概览", {**common, "process_refs": [fx.ref("content.process")],
            "question": "如何控制反馈", "methods": ["增益比较"], "results": ["仅合成"],
            "current_stage": "软件验证", "open_questions": ["现实模型未验证"]}, body="反馈研究概览：目标、阶段与未解决问题。")
        overview["schema_version"] = 4
        fx.commit_draft("content.overview", overview)
        fx.association("content.current-supplement", "A.unit", "B.experience")
        cls.draft = overview

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.coordinator = Coordinator(self.fx.root)
        scope = Scope((self.fx.owner_ids["A"],), None, None, None, None, None, None, False, (), (), None, None)
        # The A unit explicitly depends on B; the source closure must remain
        # inside an authorized ceiling even when only A is recalled.
        ceiling = replace(scope, owner_ids=(self.fx.owner_ids["A"], self.fx.owner_ids["B"]))
        self.request = QueryRequest(DefinitionRef("full", "1"), "反馈", (), scope, ceiling, "exploration",
            AssociationOptions("off", "existing-relations", "1", 0, 0, None), DEFAULT_BUDGET,
            "fixed", 20, "reject", (), "", content_source="overview_experience")

    def tearDown(self):
        self.coordinator.close()

    def search(self, request=None):
        result = self.coordinator.search(json_value(request or self.request))
        self.assertIn(result["status"], {"ok", "partial"}, result)
        return result["value"]

    def expand(self, receipt, target="technical", **overrides):
        chosen = next(c for c in receipt["candidates"] if c["refs"][0]["id"] == self.fx.record_ids["content.overview"])
        return dispatch(self.coordinator, "expand", {"query_id": receipt["query_id"],
            "candidate_ids": [chosen["candidate_id"]], "expected_request_digest": receipt["request_digest"],
            "target": target, **overrides})

    def test_source_is_separate_from_hard_scope_and_old_kinds(self):
        for source, kinds in [("overview_experience", {"overview", "experience"}), ("process", {"narrative"}), ("technical", {"detail"})]:
            result = self.search(replace(self.request, content_source=source))
            self.assertTrue(result["candidates"])
            for item in result["candidates"]:
                ref = item["refs"][0]
                record = next(r for r in self.fx.records.values() if r["record_id"] == ref["id"] and r["revision"] == ref["revision"])
                self.assertIn(record["kind"], kinds)
                self.assertIn(item["realization"]["state"], {"direct", "assemblable"})

    def test_direct_fixed_technical_block_and_process_expansion(self):
        receipt = self.search()
        for target in ("process", "technical"):
            result = self.expand(receipt, target)
            self.assertEqual(result["status"], "ok", result)
            self.assertEqual(len(result["value"]["candidates"]), 1)
            candidate = result["value"]["candidates"][0]
            if target == "technical":
                self.assertEqual(candidate["refs"][0]["locator"], "block:r")
            packet = self.coordinator.assemble({"query_id": receipt["query_id"], "candidate_ids": [candidate["candidate_id"]],
                                                "expected_request_digest": receipt["request_digest"]})
            self.assertTrue(packet.get("value") and packet["value"]["parts"], packet)

    def test_expand_keeps_exclusions_budget_and_query_digest(self):
        scope = replace(self.request.scope, levels=("L4",))
        result = self.expand(self.search(replace(self.request, scope=scope)))
        self.assertEqual(result["value"]["candidates"], [])
        excluded = replace(self.request.scope, exclude_ids=(self.fx.record_ids["A.unit"],))
        hidden = self.search(replace(self.request, scope=excluded))
        self.assertNotIn(self.fx.record_ids["content.overview"], [c["refs"][0]["id"] for c in hidden["candidates"]])
        receipt = self.search(replace(self.request, budget=replace(DEFAULT_BUDGET, graph_hops=0)))
        self.assertEqual(self.expand(receipt)["code"], "BUDGET")
        self.assertEqual(self.expand(receipt, expected_request_digest="wrong")["code"], "CONFLICT")

    def test_expansion_returns_complete_blocks_required_context_and_existing_supplement(self):
        request = replace(self.request, association=replace(self.request.association, mode="existing_only", max_items=5,
                          output_share=0.4, supplement_scope=self.request.scope_ceiling))
        receipt = self.search(request)
        result = self.expand(receipt, include_packet=True)
        self.assertIn(result["status"], {"ok", "partial"}, result)
        packet = result["value"]["packet"]
        self.assertEqual(packet["query_id"], receipt["query_id"])
        required = [p for p in packet["parts"] if p["group"] == "required_context"]
        self.assertIn("MQ_A_DEFINITION", str(required))
        self.assertIn("MQ_B_DEFINITION", str(required))
        associations = [p for p in packet["parts"] if p["group"] == "association"]
        self.assertIn(self.fx.record_ids["B.experience"], str(associations))
        self.assertFalse(packet["canonical"])

    def test_v4_requires_fixed_authored_links_and_real_narrative(self):
        draft = deepcopy(self.draft)
        draft["payload"]["technical_refs"][0]["sha256"] = None
        self.assertFalse(validate_record(draft)["valid"])
        draft = deepcopy(self.draft)
        wrong = lambda ref: {"kind": "event", "payload": {}}
        self.assertFalse(validate_record(draft, {"resolve_ref": wrong})["valid"])
        draft = deepcopy(self.draft)
        draft["body_markdown"] = ""
        self.assertFalse(validate_record(draft)["valid"])

    def test_source_filter_precedes_bounded_fts_window(self):
        result = self.search(replace(self.request, content_source="process", result_limit=1,
                                    budget=replace(DEFAULT_BUDGET, candidates=1)))
        self.assertEqual([c["refs"][0]["id"] for c in result["candidates"]], [self.fx.record_ids["content.process"]])

    def test_cli_failed_expansion_does_not_assemble_original_page(self):
        from argparse import Namespace
        from material_query.cli import execute
        # Exercise the real CLI action runner and store. A zero-hop budget
        # permits search but forbids the requested fixed technical expansion.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "query.json"
            request = replace(self.request, budget=replace(DEFAULT_BUDGET, graph_hops=0))
            path.write_text(json.dumps(json_value(request)), encoding="utf-8")
            result, code = execute(self.fx.root, Namespace(action="search", request=path,
                                                         expand="technical", assemble=True))
            self.assertEqual(code, 2)
            self.assertEqual(result["expansion"]["code"], "BUDGET")
            self.assertNotIn("assembly", result)


class NativeClaimContentTests(unittest.TestCase):
    """真实浏览器发现的旧 Run claim 来源故障；保留原指纹和拒绝边界。"""
    @classmethod
    def setUpClass(cls):
        from memory_fixture import materialize as legacy_fixture
        from memory.service import MemoryService
        from memory import index, owners
        cls.temp = tempfile.TemporaryDirectory()
        cls.fx = legacy_fixture(Path(cls.temp.name) / "旧结论 中文", isolation_root=cls.temp.name)
        cls.service = MemoryService(cls.fx.root)
        cls.service.commit(cls.fx.request(["MEM-SRC-THERMAL", "MEM-EXP-THERMAL"]))
        index.rebuild(cls.fx.root, vector="off")
        owner = owners.resolve_owner(cls.fx.root, "RUN-SYN-THERMAL")
        cls.native_path = cls.fx.root / owner["native_ref"]["path"]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_existing_experience_reads_native_claim_and_rechecks_revocation_and_hash(self):
        scope = Scope(None, None, None, None, None, None, None, False, (), (), None, None)
        request = QueryRequest(DefinitionRef("full", "1"), "预热", (), scope, scope, "exploration",
            AssociationOptions("off", "existing-relations", "1", 0, 0, None), DEFAULT_BUDGET,
            "fixed", 20, "reject", (), "", content_source="overview_experience")
        coordinator = Coordinator(self.fx.root)
        original = self.native_path.read_bytes()
        registry_path = self.fx.root / "retrieval/sources.json"
        registry_bytes = registry_path.read_bytes()
        try:
            result = coordinator.search(json_value(request))
            self.assertTrue(result.get("value") and result["value"]["candidates"], result)
            query_id = result["value"]["query_id"]
            raw = json.loads(original)
            raw["claims"][0]["statement"] += "（已修改）"
            self.native_path.write_text(json.dumps(raw), encoding="utf-8")
            self.assertEqual(coordinator.poll(query_id)["code"], "STALE")
            self.native_path.write_bytes(original)
            registry = json.loads(registry_bytes)
            for source in registry["sources"]:
                source["enabled"] = False
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            self.assertEqual(coordinator.poll(query_id)["code"], "DENIED")
            registry_path.write_bytes(registry_bytes)
            denied = coordinator.search(json_value(replace(request,
                scope_ceiling=replace(scope, owner_ids=("RES-SYN-THERMAL",)))))
            self.assertFalse(denied.get("value") and denied["value"]["candidates"], denied)
        finally:
            self.native_path.write_bytes(original)
            registry_path.write_bytes(registry_bytes)
            coordinator.close()


if __name__ == "__main__":
    unittest.main()
