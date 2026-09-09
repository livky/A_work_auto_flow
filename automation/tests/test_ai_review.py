"""Mechanical recording tests, explicitly not evidence that actual-AI tasks ran."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("ai_review", Path(__file__).parents[1] / "testing" / "ai_review.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class ActualAIRecorderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.attempt = review.initialize(self.root, "A01", actor="mechanical-test")

    def tearDown(self):
        self.tmp.cleanup()

    def test_failure_then_success_preserves_unique_receipts(self):
        first, fail = review.capture_call(self.attempt, [sys.executable, "-c", "print('first'); raise SystemExit(7)"])
        second, ok = review.capture_call(self.attempt, [sys.executable, "-c", "print('second')"])
        self.assertNotEqual(first, second)
        self.assertEqual(fail["exit_code"], 7)
        self.assertEqual(ok["exit_code"], 0)
        self.assertIn("first", (first / "stdout.txt").read_text())
        self.assertEqual(ok["ai_assessment"], "not-reviewed")

    def test_timeout_is_not_success(self):
        path, receipt = review.capture_call(self.attempt, [sys.executable, "-c", "import time; time.sleep(2)"], timeout=0.01)
        self.assertEqual(receipt["status"], "timeout")
        self.assertIsNone(receipt["exit_code"])
        self.assertTrue((path / "result.json").is_file())

    def test_read_archives_exact_snapshot_with_declared_partial_coverage(self):
        source = self.root / "response.json"
        source.write_text('{"text":"实际正文"}', encoding="utf-8")
        event = self.root / "event.json"
        review.write_new(event, {"actor": "test", "origin": {"call_id": "known-call"},
            "capture_path": str(source), "locator": "text", "coverage": "partial", "observation": "只读text字段"})
        saved = review.record_read(self.attempt, event)
        self.assertEqual((saved / "capture.snapshot.txt").read_bytes(), source.read_bytes())
        self.assertEqual(review.read_json(saved / "event.json")["coverage"], "partial")

    def test_assessment_requires_all_observations_and_refuses_human_acceptance(self):
        value = {"actor": "mechanical-test", "comparisons": []}
        path = self.root / "assessment.json"
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            review.record_assessment(self.attempt, path)
        value["comparisons"] = [{"expectation_id": f"A01-E{i}", "status": "cannot-assess",
            "observation": "This is a recorder test, no product usage", "evidence_refs": ["test-only"]} for i in range(1, 4)]
        value["human_review"] = "accepted"
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            review.record_assessment(self.attempt, path)
        value["human_review"] = "pending"
        path.write_text(json.dumps(value))
        saved = review.record_assessment(self.attempt, path)
        self.assertEqual(review.read_json(saved)["human_review"], "pending")

    def test_render_without_reading_never_invents_pass(self):
        page = review.render(self.root)
        self.assertIn("未自查", page.read_text(encoding="utf-8"))
        self.assertIn("待审查", page.read_text(encoding="utf-8"))
        self.assertIsNone(review.read_json(self.attempt / "manifest.json")["model"])
        newer = review.render(self.root)
        self.assertNotEqual(page, newer)
        self.assertTrue(page.is_file())

    def test_report_links_are_relative_and_external_artifacts_are_rejected(self):
        review.capture_call(self.attempt, [sys.executable, "-c", "print('recording only')"])
        index = review.render(self.root)
        page = next(p for p in index.parent.glob("A01-*.md"))
        text = page.read_text(encoding="utf-8")
        self.assertIn("../../A01/attempt-", text)
        self.assertNotIn(self.root.as_posix(), text)
        value = {"actor": "mechanical-test", "comparisons": [
            {"expectation_id": f"A01-E{i}", "status": "cannot-assess", "observation": "No actual AI ran",
             "evidence_refs": ["test-only"]} for i in range(1, 4)],
             "readable_artifacts": [{"title": "outside", "path": str(Path(__file__).resolve())}]}
        path = self.root / "external-assessment.json"
        path.write_text(json.dumps(value))
        review.record_assessment(self.attempt, path)
        with self.assertRaises(ValueError):
            review.render(self.root)


if __name__ == "__main__":
    unittest.main()
