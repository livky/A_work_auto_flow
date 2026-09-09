"""影响/问题/沿袭的身份输出必须遵守当前来源授权，不能借图路径泄漏。"""
import json
import unittest

import test_memory_evidence as fixture
import test_memory_store as store_fixture
from test_memory_contracts import examples
from memory import impact, lineage
from memory.evidence_adapter import EvidenceAdapter
from memory.errors import MemoryError


class ImpactVisibilityTests(unittest.TestCase):
    def test_restricted_owner_records_are_absent_from_impact_paths_and_heads(self):
        fx = fixture.MemoryEvidenceTests()
        fx.setUp()
        self.addCleanup(fx.tearDown)
        source = fx.save(fx.value([]))
        native = fx.root / "research/private/research.json"
        native.parent.mkdir()
        native.write_text(json.dumps({"research_id": "RES-PRIVATE", "title": "SYNTHETIC ONLY hidden", "sensitivity": "internal"}), encoding="utf-8")
        private = fx.value([], "RES-PRIVATE")
        private["sources"] = [fx.record_ref(source, "supports")]
        dependent = fx.save(private)
        question = fx.value([], "RES-PRIVATE")
        question.update(kind="question", payload=examples()["question"])
        question = fx.save(question)
        visible_before = impact.reverse_dependencies(fx.root, [source["record_id"]], service=fx.service)
        self.assertIn(dependent["record_id"], {item["canonical_id"] for item in visible_before["affected"]})
        data = json.loads(native.read_text(encoding="utf-8"))
        data["sensitivity"] = "restricted"
        native.write_text(json.dumps(data), encoding="utf-8")
        before = store_fixture.snapshot_files(fx.root)
        result = impact.reverse_dependencies(fx.root, [source["record_id"]], service=fx.service)
        text = json.dumps(result)
        self.assertNotIn("RES-PRIVATE", text)
        self.assertNotIn(dependent["record_id"], text)
        self.assertNotIn(question["record_id"], text)
        adapter = EvidenceAdapter(fx.service)
        formal = adapter.formal_projection([source["record_id"]], "synthetic:A")
        self.assertNotIn("RES-PRIVATE", formal["source_heads"])
        self.assertIn("RES-TEST", formal["source_heads"])
        self.assertIn("RES-PRIVATE", adapter.source_heads)
        self.assertTrue(any(check.get("owner_id") == "RES-PRIVATE" for check in adapter.basis_checks))
        for action in (lambda: impact.reverse_dependencies(fx.root, [dependent["record_id"]], service=fx.service),
                       lambda: impact.question_resolution_validity(fx.root, question["record_id"], service=fx.service)):
            with self.assertRaises(MemoryError) as caught:
                action()
            self.assertEqual(caught.exception.code, "ACCESS_DENIED")
            self.assertEqual(caught.exception.details, {})
        projected = lineage.project(fx.service, [dependent["record_id"]])
        self.assertEqual(projected["source_count"], 0)
        self.assertEqual(projected["missing"][0]["code"], "ACCESS_DENIED")
        self.assertEqual(store_fixture.snapshot_files(fx.root), before)


if __name__ == "__main__":
    unittest.main()
