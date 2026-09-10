"""F1 基线验证：仅调用现有 memory 公共 API，不模拟未来材料查询接口。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import material_query_fixture as fixture
from memory import api, contracts
from memory.errors import MemoryError


class MaterialQueryFixtureTests(unittest.TestCase):
    """共享只读基线；唯一授权故障通过上下文管理器恢复 sources.json 原字节。"""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="material-query-fixture-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.fx = fixture.materialize(Path(cls.temp.name) / "F1 中文 workspace", isolation_root=cls.temp.name)

    def test_fixture_materializes_real_public_receipts_and_all_layers(self):
        fx = self.fx
        manifest = json.loads((fx.root / "material-query-fixture.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["synthetic_only"])
        self.assertEqual(manifest["fixed_refs"], fx.refs)
        for path, expected in manifest["input_files"].items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((fx.root / path).read_bytes()).hexdigest(), expected)
        for alias in ("A", "B"):
            value = api.dispatch(fx.service, "inspect", {"owner_id": fx.owner_ids[alias]})
            self.assertTrue({"L0", "L1", "L2", "L3", "L4"} <= {r["level"] for r in value["records"].values()})
        for saved in fx.receipts:
            self.assertEqual(saved["receipt"]["save_status"], "committed", saved["key"])
            self.assertIn(saved["action"], {"commit", "review", "associations-decide"})
        raw = api.dispatch(fx.service, "raw-materials", {"owner_id": fx.owner_ids["A"]})
        self.assertTrue(any(item["sha256"] == fx.sources["A"]["sha256"] for item in raw["items"]))

    def test_fixed_unit_and_documents_keep_old_bytes_after_r2(self):
        fx = self.fx
        old, new = fx.inspect("A.unit.r1"), fx.inspect("A.unit.r2")
        self.assertEqual(old["record_id"], new["record_id"])
        self.assertEqual((old["revision"], new["revision"]), (1, 2))
        self.assertNotEqual(old["record_hash"], new["record_hash"])
        self.assertIn("MQ_A_METHOD_R1", json.dumps(old, ensure_ascii=False))
        self.assertNotIn("MQ_A_METHOD_R2", json.dumps(old, ensure_ascii=False))
        views = {}
        for key in ("A.process.r1", "A.report.r1", "A.report.r2"):
            record = fx.records[key]
            views[key] = api.dispatch(fx.service, "document", {"owner_id": record["owner_id"],
                        "document_id": record["record_id"], "revision": record["revision"]})
        self.assertIn("MQ_A_METHOD_R1", json.dumps(views["A.process.r1"], ensure_ascii=False))
        self.assertIn("MQ_A_METHOD_R1", json.dumps(views["A.report.r1"], ensure_ascii=False))
        self.assertIn("MQ_A_METHOD_R2", json.dumps(views["A.report.r2"], ensure_ascii=False))
        self.assertNotEqual(fx.record_ids["A.process"], fx.record_ids["A.report"])

    def test_method_expansion_keeps_definitions_and_honors_exclusion(self):
        fx = self.fx
        request = {"owner_id": fx.owner_ids["A"], "document_id": fx.record_ids["A.process"],
                   "section_id": fx.record_ids["A.process_section.r1"], "budget": {"max_chars": 10000}}
        complete = api.dispatch(fx.service, "section-context", request)
        self.assertTrue(complete["manifest"]["complete"])
        self.assertIn("MQ_A_DEFINITION", complete["context_text"])
        self.assertIn("MQ_A_METHOD_R1", complete["context_text"])
        excluded = api.dispatch(fx.service, "section-context", {**request,
            "selection": {"exclude_ids": [fx.record_ids["A.unit.r1"] + "#d"]}})
        self.assertFalse(excluded["manifest"]["complete"])
        self.assertNotIn("MQ_A_METHOD_R1", excluded["context_text"])
        self.assertIn("EXCLUDED", {item["code"] for item in excluded["manifest"]["missing"]})

    def test_review_identity_scope_and_history_are_distinct(self):
        fx = self.fx
        state_a = api.dispatch(fx.service, "inspect", {"owner_id": fx.owner_ids["A"]})["claim_states"]
        self.assertTrue(state_a[fx.claims["accepted"]]["effective_validity"])
        self.assertEqual(state_a[fx.claims["unreviewed"]]["review_state"], "not-reviewed")
        stale = state_a[fx.claims["stale"]]
        self.assertEqual(stale["review_state"], "accepted")
        self.assertFalse(stale["effective_validity"])
        self.assertIn("STALE_BASIS", {item["code"] for item in stale["errors"]})
        self.assertEqual(fx.inspect("B.review.retracted.r1")["payload"]["state"], "accepted")
        self.assertEqual(fx.inspect("B.review.retracted.r2")["payload"]["state"], "retracted")
        self.assertEqual(fx.inspect("B.review.superseded")["payload"]["replacement_claim_id"], fx.claims["accepted"])

    def test_navigation_has_current_and_stale_edges_without_promoting_claims(self):
        fx = self.fx
        for key, expected in (("edge.current", False), ("edge.old_unit", True)):
            result = api.dispatch(fx.service, "associations-view", {"owner_id": fx.owner_ids["A"],
                                  "record_id": fx.record_ids[key]})
            self.assertEqual(result["stale"], expected)
            self.assertEqual(result["record"]["payload"]["relation"], "analogous_to")
        endpoints = {ref["target_id"] for key in ("edge.current", "edge.old_unit")
                     for ref in (fx.records[key]["payload"]["from"], fx.records[key]["payload"]["to"])}
        for key in ("C.no_edge_positive", "D.same_words_negative"):
            self.assertNotIn(fx.record_ids[key], endpoints)
        a = fx.inspect("A.experience")["payload"]
        c = fx.inspect("C.no_edge_positive")["payload"]
        d = fx.inspect("D.same_words_negative")["payload"]
        self.assertIn("反馈", a["problem_structure"])
        self.assertIn("负反馈", c["recommendation"])
        self.assertIn("不是", d["recommendation"])
        # 标注只为后续真实语义比较准备正负例；不调用未来 discover 或伪造其通过。
        self.assertEqual(fx.labels["positive_without_edge"], "C.no_edge_positive")

    def test_source_revocation_blocks_old_refs_without_rewriting_history(self):
        fx = self.fx
        registry = fx.root / "retrieval" / "sources.json"
        original_registry = registry.read_bytes()
        heads = {path.relative_to(fx.root).as_posix(): path.read_bytes() for path in fx.root.rglob("HEAD.json")}
        original_bytes = (fx.root / fx.sources["A"]["path"]).read_bytes()
        with fx.source_access("A", enabled=False):
            with self.assertRaises(MemoryError) as caught:
                fx.inspect("A.unit.r1")
            self.assertEqual(caught.exception.code, "ACCESS_DENIED")
            view = api.dispatch(fx.service, "document", {"owner_id": fx.owner_ids["A"],
                                "document_id": fx.record_ids["A.process"]})
            self.assertNotIn("MQ_A_METHOD_R1", json.dumps(view, ensure_ascii=False))
        self.assertEqual(registry.read_bytes(), original_registry)
        self.assertEqual((fx.root / fx.sources["A"]["path"]).read_bytes(), original_bytes)
        self.assertEqual(heads, {p.relative_to(fx.root).as_posix(): p.read_bytes() for p in fx.root.rglob("HEAD.json")})
        self.assertEqual(fx.inspect("A.unit.r1")["record_hash"], fx.refs["A.unit.r1"]["sha256"])

    def test_restricted_owner_is_denied_and_not_publicly_listed(self):
        fx = self.fx
        with self.assertRaises(MemoryError) as caught:
            api.dispatch(fx.service, "inspect", {"owner_id": fx.owner_ids["X"]})
        self.assertEqual(caught.exception.code, "ACCESS_DENIED")
        listed = json.dumps(api.dispatch(fx.service, "list-owners", {}), ensure_ascii=False)
        self.assertNotIn(fixture.HIDDEN_TITLE, listed)
        self.assertNotIn(fixture.HIDDEN_BODY, listed)

    def test_invalid_cases_remain_uncommitted_and_schema_is_not_weakened(self):
        fx = self.fx
        before = fx.head("A")
        for key, draft in fx.invalid_drafts.items():
            request = {"schema_version": 1, "request_id": fixture._uuid("invalid:" + key), "actor": fixture.ACTOR,
                       "owner_id": fx.owner_ids["A"], "expected_head": before,
                       "operations": [{"op": "put_record", "client_key": key, "draft": deepcopy(draft)}]}
            with self.subTest(key=key), self.assertRaises(MemoryError):
                api.dispatch(fx.service, "validate-draft", request)
        self.assertEqual(fx.head("A"), before)
        self.assertFalse(contracts.validate_record(fx.invalid_drafts["missing_required_field"])["valid"])

    def test_existing_and_business_roots_are_refused_without_mutation(self):
        fx = self.fx
        marker = (fx.root / "SYNTHETIC_ONLY.txt").read_bytes()
        with self.assertRaises(ValueError):
            fixture.materialize(fx.root, isolation_root=self.temp.name)
        with self.assertRaises(ValueError):
            fixture.materialize(fixture.REPOSITORY / "research" / "invalid-fixture", isolation_root=fixture.REPOSITORY)
        self.assertEqual((fx.root / "SYNTHETIC_ONLY.txt").read_bytes(), marker)


if __name__ == "__main__":
    unittest.main()
