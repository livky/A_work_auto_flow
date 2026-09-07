"""合成证据与本机 HTTP 验证；只读、变更时间、重复不晋升及迁移边界。"""
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import test_evidence as fixture
import evidence as e
import evidence_observer as o
import evidence_view as v
import install_workspace_skills as skill_install


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixture.EvidenceTests()
        self.fx.setUp()
        self.root = self.fx.root

    def tearDown(self):
        self.fx.tearDown()

    def test_view_explains_review_and_report_claim_dependency_without_writes(self):
        report = self.fx.put("reports/sources/result.md", "合成报告")
        self.fx.save(report.with_name("result.md.evidence.json"), {"evidence_id": "EVD-REPORT", "document_path": "reports/sources/result.md",
            "claims": [self.fx.claim("CLM-REPORT", refs=[self.fx.reference("CLM-BASE")])]})
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        payload = v.data(self.root)
        node = payload["nodes"]["CLM-BASE"]
        self.assertTrue(node["formal_eligible"])
        self.assertEqual(node["review"]["reviewer"], "synthetic-fixture")
        self.assertEqual(node["record_reason"], "未记录保存理由")
        self.assertEqual(node["reports"][0]["id"], "EVD-REPORT")
        self.assertEqual(node["reports"][0]["chain"], ["CLM-BASE", "CLM-REPORT"])
        self.assertTrue(payload["nodes"]["RUN-BASE"]["assets"][0]["version_matches"])
        self.assertIn("合成计算", v.source(self.root, "RUN-BASE", 0, "artifacts")["text"])
        with self.assertRaises(ValueError):
            v.source(self.root, "RUN-BASE", 0, "../private")
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_initial_baseline_then_change_without_duplicate_events(self):
        initial = o.monitor(self.root)
        self.assertTrue(initial["baseline_created"])
        self.assertEqual(initial["new_events"], 0)
        self.assertEqual(o.monitor(self.root)["new_events"], 0)
        self.fx.source.write_text("new bytes", encoding="utf-8")
        changed = o.monitor(self.root)
        self.assertTrue(any(x["kind"] == "material-changed" for x in changed["changes"]))
        self.assertTrue(any(x["kind"] == "dependency-risk" for x in changed["changes"]))
        count = len(o.load_state(self.root)["events"])
        self.assertEqual(o.monitor(self.root)["new_events"], 0)
        self.assertEqual(len(o.load_state(self.root)["events"]), count)

    def test_terminal_transition_is_observed_not_accepted(self):
        run = e.read(self.fx.run_path)
        run["status"] = "running"
        run["review"] = {"status": "not-reviewed"}
        self.fx.save(self.fx.run_path, run)
        o.monitor(self.root)
        run["status"] = "succeeded"
        self.fx.save(self.fx.run_path, run)
        observed = o.monitor(self.root)
        self.assertTrue(any(x["kind"] == "experiment-finished" for x in observed["changes"]))
        self.assertEqual(e.read(self.fx.run_path)["review"]["status"], "not-reviewed")

    def test_retraction_and_restoration_preserve_observation_history(self):
        o.monitor(self.root)
        e.review_claim(self.root, "CLM-BASE", "retracted", "tester", "synthetic counterevidence")
        o.monitor(self.root)
        state = o.load_state(self.root)
        first_seen = state["invalid_since"]["CLM-BASE"]
        o.monitor(self.root)
        self.assertEqual(o.load_state(self.root)["invalid_since"]["CLM-BASE"], first_seen)
        e.review_claim(self.root, "CLM-BASE", "accepted", "tester", "checked again", "fixture", "bench:A")
        result = o.monitor(self.root)
        self.assertTrue(any(x["kind"] == "risk-cleared-observed" for x in result["changes"]))
        self.assertNotIn("CLM-BASE", o.load_state(self.root)["invalid_since"])
        self.assertTrue(any(x["kind"] == "dependency-risk" for x in o.load_state(self.root)["events"]))

    def test_duplicates_remain_candidates_without_promotion(self):
        path, _ = self.fx.research(claims=[self.fx.claim("CLM-A", "not-reviewed"), self.fx.claim("CLM-B", "not-reviewed")])
        before = path.read_bytes()
        o.monitor(self.root)
        o.monitor(self.root)
        candidates = o.load_state(self.root)["candidates"]
        comparisons = [c for c in candidates.values() if c["kind"] == "compare-claims"]
        self.assertEqual(len(comparisons), 1)
        self.assertEqual(comparisons[0]["status"], "pending")
        self.assertEqual(path.read_bytes(), before)

    def test_background_reference_does_not_inherit_retraction(self):
        self.fx.research(dependencies=[self.fx.reference("RUN-BASE", "background")], claims=[self.fx.claim("CLM-RESEARCH")])
        o.monitor(self.root)
        run = e.read(self.fx.run_path)
        run["review"]["status"] = "retracted"
        self.fx.save(self.fx.run_path, run)
        o.monitor(self.root)
        self.assertEqual(o.load_state(self.root)["snapshot"]["nodes"]["CLM-RESEARCH"]["risks"], [])

    def test_dry_run_and_failed_scan_do_not_replace_baseline(self):
        o.monitor(self.root, dry_run=True)
        self.assertFalse((self.root / "context/monitor").exists())
        o.monitor(self.root)
        path = self.root / o.STATE
        before = path.read_bytes()
        with patch.object(o, "collect", side_effect=ValueError("partial scan")):
            with self.assertRaises(ValueError):
                o.monitor(self.root)
        self.assertEqual(path.read_bytes(), before)
        with e.locked(path):
            with self.assertRaises(ValueError):
                o.monitor(self.root)
        self.assertEqual(path.read_bytes(), before)

    def test_corrupt_state_requires_explicit_recovery(self):
        self.fx.put(o.STATE, '{"schema_version":999}')
        with self.assertRaises(ValueError):
            o.monitor(self.root)
        self.assertEqual((self.root / o.STATE).read_text(), '{"schema_version":999}')

    def test_relocated_workspace_keeps_relative_baseline(self):
        o.monitor(self.root)
        with tempfile.TemporaryDirectory() as temp:
            moved = Path(temp) / "中文 空格 副本"
            shutil.copytree(self.root, moved)
            self.assertEqual(o.monitor(moved)["new_events"], 0)

    def test_oversized_file_keeps_previous_state(self):
        o.monitor(self.root)
        old = (self.root / o.STATE).read_bytes()
        cfg = e.read(self.root / "retrieval/config.json")
        cfg["max_file_bytes"] = 1
        self.fx.save(self.root / "retrieval/config.json", cfg)
        with self.assertRaises(ValueError):
            o.monitor(self.root)
        self.assertEqual((self.root / o.STATE).read_bytes(), old)

    def test_html_escapes_untrusted_content_and_preview_is_bounded(self):
        payload = v.data(self.root)
        attack = '</script><img src=x onerror="alert(1)"> __LIVE_MODE__'
        payload["nodes"]["CLM-BASE"]["title"] = attack
        html = v.render(payload)
        self.assertNotIn(attack, html)
        self.assertIn("\\u003c/script\\u003e", html)
        self.assertIn("__LIVE_MODE__", html)  # 不能把材料中的同名文本当模板占位符改写。
        self.assertNotIn("innerHTML", html)
        self.fx.source.write_text("x" * 70000)
        result = v.source(self.root, "CLM-BASE", 0)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["text"]), 65536)
        with self.assertRaises(ValueError):
            v.source(self.root, "../../AGENTS.md")
        with self.assertRaises(ValueError):
            v.source(self.root, "CLM-BASE", 0, expected_fingerprint="stale-page")

    def test_local_output_cannot_redirect_into_source_material(self):
        before = self.fx.source.read_bytes()
        with patch.object(e, "inside", return_value=self.fx.source):
            with self.assertRaises(ValueError):
                o.monitor(self.root)
            with self.assertRaises(ValueError):
                v.export(self.root)
        self.assertEqual(self.fx.source.read_bytes(), before)

    def test_http_is_loopback_readonly_and_rejects_unknown_paths(self):
        server, url = v.create_server(self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
            with urlopen(url + "api/state", timeout=10) as response:
                self.assertIn("CLM-BASE", json.load(response)["nodes"])
            with urlopen(url + "api/source?id=CLM-BASE&ref=0", timeout=10) as response:
                self.assertIn("合成测量", json.load(response)["text"])
            for request, expected in [(Request(url, method="POST"), 405), (url + "../AGENTS.md", 404),
                                      (Request(url, headers={"Host": "evil.example"}), 404), (url + "api/source?id=unknown", 400)]:
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=10)
                self.assertEqual(caught.exception.code, expected)
                caught.exception.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_selective_skill_upgrade_preserves_existing_local_edits(self):
        old = self.fx.put(".agents/skills/context-maintenance/SKILL.md", "local custom skill")
        self.fx.put("automation/workflows/evidence-inspection/SKILL.md", "---\nname: evidence-inspection\ndescription: 查看证据\n---\n方法")
        with patch.object(skill_install, "ROOT", self.root):
            skill_install.install(True, ["evidence-inspection"])
            skill_install.install(True, ["evidence-inspection"])
            with self.assertRaises(ValueError):
                skill_install.install(True, ["../../bad"])
        self.assertEqual(old.read_text(), "local custom skill")
        self.assertIn("../../../automation/workflows/evidence-inspection/SKILL.md", (self.root / ".agents/skills/evidence-inspection/SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()
