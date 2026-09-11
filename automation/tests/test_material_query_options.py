"""用户可见范围、旧版本和完整文稿行为，使用真实隔离存储及公开入口。"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import base64
import hashlib
import json
import tempfile
import unittest

from material_query_fixture import materialize, _draft
from material_query.api import dispatch
from material_query.budget import DEFAULT_BUDGET, SERVER_LIMITS
from material_query.contracts import AssociationOptions, DefinitionRef, QueryRequest, Scope
from material_query.coordinator import Coordinator
from material_query.wire import json_value


class MaterialQueryOptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.fx = fx = materialize(Path(cls.temp.name) / "查询选项 中文", isolation_root=cls.temp.name)
        payload = deepcopy(fx.records["A.event"]["payload"])
        payload["claims"] = []
        fx.commit_draft("options.old", _draft(fx, "A", "event", "ONLYPASTTOKEN", payload, body="ONLYPASTTOKEN 旧版结果"))
        fx.revise("options.new", "options.old", title="ONLYCURRENTTOKEN", body_markdown="ONLYCURRENTTOKEN 新版结果",
                  keywords=["合成", "反馈", "增益", "ONLYCURRENTTOKEN"])
        # 独立受控合成图片，验证组包不依赖浏览器另开未计量的原件入口。
        figure_path = fx.root / "packet-figure.png"
        figure_path.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6zAAAAABJRU5ErkJggg=="))
        registry_path = fx.root / "retrieval/sources.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        fx.sources["FIGURE"] = {"source_id": "SRC-MQ-FIGURE", "path": "packet-figure.png", "enabled": True,
                                "sensitivity": "internal", "sha256": hashlib.sha256(figure_path.read_bytes()).hexdigest()}
        registry["sources"].append(fx.sources["FIGURE"])
        registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
        illustrated = deepcopy(fx.records["A.unit"]["payload"])
        illustrated["figures"] = [{"caption": "合成单像素图", "ref": fx.source_ref("FIGURE")}]
        illustrated["blocks"][-1]["markdown"] += "\n\n![合成图](figure:0)"
        fx.commit_draft("options.figure", _draft(fx, "A", "detail", "固定图示正文", illustrated))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.coordinator = Coordinator(self.fx.root)
        scope = Scope(None, None, None, None, None, None, None, False, (), (), None, None)
        self.request = QueryRequest(DefinitionRef("full", "1"), "反馈", (), scope, scope, "exploration",
            AssociationOptions("off", "existing-relations", "1", 0, 0, None),
            replace(DEFAULT_BUDGET, read_bytes=16*1024*1024, output_chars=80000, candidates=300),
            "current", 100, "reject", (), "", content_source="all")

    def tearDown(self):
        self.coordinator.close()

    def search(self, **changes):
        result = self.coordinator.search(json_value(replace(self.request, **changes)))
        self.assertIn(result["status"], {"ok", "partial"}, result)
        self.assertIsNotNone(result["value"], result)
        return result["value"]

    def test_standard_owner_types_filter_tree_and_recall_before_output(self):
        for types, expected in [(('research',), {self.fx.owner_ids['A']}), (('project',), {self.fx.owner_ids['B']}),
                                (('research','project'), {self.fx.owner_ids['A'],self.fx.owner_ids['B']}), ((), set())]:
            scope = replace(self.request.scope, owner_types=types)
            tree = dispatch(self.coordinator, "structure", {"scope": json_value(scope), "parent_ref": None,
                "cursor": None, "limit": 100, "view": "logical"})
            self.assertEqual(tree["status"], "ok", tree)
            self.assertEqual({n["node_id"] for n in tree["value"]["nodes"]}, expected)
            result = self.search(scope=scope, content_source="technical")
            self.assertTrue(all(c["owner_type"] in types for c in result["candidates"]))
            if types:
                self.assertTrue(result["candidates"])
        tree = dispatch(self.coordinator, "structure", {"scope": json_value(self.request.scope), "parent_ref": None,
            "cursor": None, "limit": 100, "view": "logical", "owner_query": "热反馈"})
        self.assertNotIn(self.fx.owner_ids['X'], str(tree))

    def test_all_sources_include_documents_sources_and_native_registered_runs(self):
        # 正文类型不是知识层级上限；显式身份必须能返回不进普通知识FTS的文稿/L0。
        for key in ("A.source", "A.process.r1", "A.process_section.r1"):
            result = self.search(question=self.fx.record_ids[key])
            self.assertTrue(any(c["refs"][0]["id"] == self.fx.record_ids[key] for c in result["candidates"]), result)
        run_id = next(iter(self.fx.run_ids.values()))
        result = self.search(question=run_id)
        native = next(c for c in result["candidates"] if c["refs"][0]["id"] == run_id)
        self.assertEqual(native["refs"][0]["kind"], "owner")
        packet = dispatch(self.coordinator, "assemble", {"query_id": result["query_id"],
            "candidate_ids": [native["candidate_id"]], "expected_request_digest": result["request_digest"]})
        self.assertIn(run_id, str(packet["value"]["parts"]))

    def test_history_is_opt_in_and_old_unique_text_is_retrievable(self):
        current = self.search(question="ONLYPASTTOKEN")
        self.assertNotIn(self.fx.record_ids["options.old"], str(current["candidates"]))
        past = self.search(question="ONLYPASTTOKEN", freshness="allow_stale")
        found = [c for c in past["candidates"] if c["refs"][0]["id"] == self.fx.record_ids["options.old"]]
        self.assertEqual(len(found), 1, past)
        self.assertFalse(found[0]["is_latest"])
        self.assertEqual(found[0]["refs"][0]["revision"], 1)
        packet = dispatch(self.coordinator, "assemble", {"query_id": past["query_id"],
            "candidate_ids": [found[0]["candidate_id"]], "expected_request_digest": past["request_digest"]})
        self.assertIn("旧版结果", str(packet["value"]["parts"]))
        self.assertNotIn("新版结果", str(packet["value"]["parts"]))

    def test_full_documents_deduplicate_hits_and_preserve_authored_text(self):
        scope = replace(self.request.scope, owner_ids=(self.fx.owner_ids['A'],))
        result = self.search(scope=scope, freshness="fixed", content_source="technical")
        # 同一文稿的两个不同命中，来自技术单元和其当前条目；借固定身份查询补第二条。
        selected = result["candidates"][:2]
        if len(selected) < 2:
            result = self.search(scope=scope, freshness="fixed", content_source="all")
            selected = [c for c in result["candidates"] if c["refs"][0]["kind"] == "record"][:2]
        self.assertEqual(len(selected), 2)
        packet = dispatch(self.coordinator, "documents", {"query_id": result["query_id"],
            "candidate_ids": [c["candidate_id"] for c in selected], "expected_request_digest": result["request_digest"]})
        self.assertIn(packet["status"], {"ok", "partial"}, packet)
        self.assertEqual(len(packet["value"]["documents"]), 1, packet)
        doc = packet["value"]["documents"][0]
        self.assertEqual(len(doc["candidate_ids"]), 2)
        self.assertTrue(packet["value"]["parts"])
        self.assertNotIn('"section_refs"', str(packet["value"]["parts"]))

    def test_five_minute_default_supports_documents_with_independent_limits(self):
        self.assertEqual(DEFAULT_BUDGET.wall_ms, 300000)
        self.assertGreaterEqual(SERVER_LIMITS.wall_ms, DEFAULT_BUDGET.wall_ms)
        self.assertEqual(DEFAULT_BUDGET.read_bytes, 16*1024*1024)
        self.assertEqual(DEFAULT_BUDGET.output_chars, 80000)
        self.assertEqual(self.coordinator.capabilities()["default_freshness"], "current")

    def test_latest_policy_rejects_cached_body_after_record_changes(self):
        result = self.search(question="ONLYCURRENTTOKEN")
        chosen = next(c for c in result["candidates"] if c["refs"][0]["id"] == self.fx.record_ids["options.new"])
        request = {"query_id": result["query_id"], "candidate_ids": [chosen["candidate_id"]],
                   "expected_request_digest": result["request_digest"]}
        before = dispatch(self.coordinator, "assemble", request)
        self.assertTrue(before["value"]["parts"])
        self.fx.revise("options.newer", "options.new", body_markdown="ONLYCURRENTTOKEN 新版结果：查询后再次修订")
        after = dispatch(self.coordinator, "assemble", request)
        self.assertEqual(after["code"], "STALE", after)
        self.assertIsNone(after["value"])

    def test_document_reading_from_layer_filter_does_not_exclude_unlayered_document(self):
        scoped = replace(self.request.scope, owner_ids=(self.fx.owner_ids['A'],), levels=("L3",))
        result = self.search(scope=scoped, freshness="fixed", content_source="overview_experience")
        self.assertTrue(result["candidates"])
        packet = dispatch(self.coordinator, "documents", {"query_id": result["query_id"],
            "candidate_ids": [result["candidates"][0]["candidate_id"]], "expected_request_digest": result["request_digest"]})
        self.assertEqual(len(packet["value"]["documents"]), 1, packet)
        self.assertTrue(packet["value"]["parts"])

    def test_embedded_figures_keep_fixed_bytes_and_obey_source_exclusion(self):
        result = self.search(question=self.fx.record_ids["options.figure"], content_source="technical")
        request = {"query_id": result["query_id"], "candidate_ids": [result["candidates"][0]["candidate_id"]],
                   "expected_request_digest": result["request_digest"]}
        packet = dispatch(self.coordinator, "assemble", request)
        figure = packet["value"]["parts"][0]["figures"][0]
        self.assertEqual(figure["ref"]["sha256"], self.fx.sources["FIGURE"]["sha256"])
        actual = base64.b64decode(figure["data_url"].split(",", 1)[1])
        self.assertEqual(hashlib.sha256(actual).hexdigest(), figure["ref"]["sha256"])
        self.assertGreaterEqual(packet["consumed"]["read_bytes"], len(actual))
        excluded = replace(self.request.scope, exclude_ids=(self.fx.sources["FIGURE"]["source_id"],))
        hidden = self.search(question=self.fx.record_ids["options.figure"], scope=excluded, channels=("identity",))
        self.assertFalse(hidden["candidates"])
