"""用合成证据验证正式使用门、撤回传播和版本边界，不伪造业务验收。"""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_retrieval as fixture
from test_retrieval import ROOT, r
import context_engine
import evidence as e
import health
import workspace_cli as cli


class EvidenceTests(unittest.TestCase):
    put = fixture.RetrievalTests.put
    tearDown = fixture.RetrievalTests.tearDown

    def test_fixed_source_relocation_preserves_history_and_rejects_unsafe_mappings(self):
        """A moved file stays usable without rewriting an immutable old Run."""
        target = 'runs/old place/results.txt'
        current = self.put('research/迁移 示例/runs/old place/results.txt', 'frozen result')
        entry = {'source_id': 'SRC-MOVED', 'path': current.relative_to(self.root).as_posix(),
                 'relocated_from': target, 'sha256': e.sha256(current), 'enabled': True}
        registry = self.root / 'retrieval/sources.json'
        def register(items):
            self.put('retrieval/sources.json', json.dumps({'sources': items}))
        register([entry])
        self.assertEqual(e.reference_path(self.root, target), current.resolve())
        self.assertFalse((self.root / target).exists())
        for bad in ({**entry, 'enabled': False}, {**entry, 'sha256': '0' * 64},
                    {**entry, 'sha256': None}, {**entry, 'sensitivity': 'restricted'}):
            with self.subTest(mapping=bad):
                register([bad])
                with self.assertRaises(ValueError):
                    e.reference_path(self.root, target)
        register([entry, {**entry, 'source_id': 'DUPLICATE'}])
        with self.assertRaises(ValueError):
            e.reference_path(self.root, target)
        # A separate denial of the actual destination overrides the alias.
        register([entry, {'path': entry['path'], 'enabled': False}])
        with self.assertRaises(ValueError):
            e.reference_path(self.root, target)
        register([entry])
        self.put(target, 'a later original must take precedence')
        self.assertEqual(e.reference_path(self.root, target), (self.root / target).resolve())

    def setUp(self):
        fixture.RetrievalTests.setUp(self)
        self.put("workspace.json", '{"required_paths": []}')
        self.put("tools/registry.json", '{"tools": []}')
        self.put("retrieval/context-policy.json", (ROOT / "retrieval/context-policy.json").read_text(encoding="utf-8"))
        self.source = self.put("data/catalog/measurement.txt", "合成测量：样例 A = 12")
        self.artifact = self.put("runs/base/value.txt", "合成计算：12")
        self.run_path = self.root / "runs/base/run.json"
        self.run = {"run_id": "RUN-BASE", "title": "合成校准", "status": "succeeded",
                    "inputs": [self.file_ref(self.source)], "artifacts": [self.file_ref(self.artifact)],
                    "code": {"commit": "a" * 40, "dirty": False},
                    "environment": {"python": "3.12", "lock_or_image_digest": "b" * 64},
                    "quality_results": [{"check": "synthetic-rule", "status": "passed"}],
                    "review": self.review(), "claims": [self.claim("CLM-BASE")], "dependencies": []}
        self.save(self.run_path, self.run)
        e.finalize_run(self.root, "RUN-BASE", "bench:A")

    def save(self, path, value):
        # 合成 fixture 显式绑定复核版本；只有新建复核才绑定，修改记录时
        # 保留旧指纹，以便测试发现内容漂移，不能在每次保存时“自动确认”。
        for claim in value.get("claims", []):
            if claim.get("review", {}).get("status") == "accepted" and "content_fingerprint" not in claim["review"]:
                claim["review"].update(content_fingerprint=e.fingerprint(claim), owner_fingerprint=e.owner_fingerprint(value))
        self.put(str(path.relative_to(self.root)), json.dumps(value, ensure_ascii=False))

    def review(self, state="accepted"):
        return {"status": state, "reviewer": "synthetic-fixture", "reason": "合成检查",
                "evidence": "合成证据", "scope": "bench:A", "date": "2026-09-06"}

    def file_ref(self, path):
        return {"path": path.relative_to(self.root).as_posix(), "sha256": e.sha256(path)}

    def claim(self, nid, state="accepted", refs=None):
        ref = {"target": self.source.relative_to(self.root).as_posix(), "sha256": e.sha256(self.source),
               "locator": "line 1", "relation": "supports"}
        return {"claim_id": nid, "statement": "合成校准结果为 12", "scope": "bench:A", "kind": "calculation",
                "evidence_refs": refs if refs is not None else [ref], "review": self.review(state), "review_history": []}

    def reference(self, target, relation="supports"):
        graph = e.EvidenceGraph(self.root)
        return {"target": target, "relation": relation, "sha256": graph.nodes[target]["fingerprint"], "locator": "conclusion"}

    def research(self, dependencies=None, claims=None):
        path = self.root / "research/topic/research.json"
        self.save(path, {"research_id": "RES-TOPIC", "dependencies": dependencies or [], "claims": claims or [], "review": self.review()})
        doc = self.put("research/topic/SYNTHESIS.md", "# 合成校准综合\n未复核正文 SHOULD-NOT-LEAK\n[Run](../../runs/base/run.json)")
        return path, doc

    def test_empty_succeeded_run_is_warned_and_formal_gate_fails(self):
        self.run.update(inputs=[], artifacts=[], quality_results=[])
        self.save(self.run_path, self.run)
        self.assertFalse(e.check_run(self.root, "RUN-BASE", "bench:A")["eligible"])
        _, warnings = cli.validate_workspace(self.root)
        self.assertTrue(any("记录不完整" in w for w in warnings))

    def test_retracted_run_propagates_to_research_then_report(self):
        _, doc = self.research([self.reference("RUN-BASE")], [self.claim("CLM-RESEARCH")])
        report = self.put("reports/sources/report.md", "合成校准报告")
        self.save(report.with_name("report.md.evidence.json"), {"evidence_id": "EVD-REPORT", "document_path": "reports/sources/report.md",
            "dependencies": [self.reference("RES-TOPIC")], "claims": [self.claim("CLM-REPORT")]})
        self.run["review"] = self.review("retracted")
        self.save(self.run_path, self.run)
        graph = e.EvidenceGraph(self.root)
        for path in (doc, report):
            self.assertIn("RUN-BASE", graph.document_state(path)["blocking_evidence_ids"])
            self.assertFalse(graph.document_state(path, scope="bench:A")["formal_eligible"])
        pack = r.assemble(self.root, r.search(self.root, "合成校准"))
        entry = next(s for s in pack["manifest"]["sources"] if s.get("path") == str(doc))
        self.assertIn("RUN-BASE", entry["evidence_state"]["blocking_evidence_ids"])

    def test_background_and_counterevidence_do_not_invalidate_claims(self):
        for relation in ("background", "contradicts"):
            _, doc = self.research([self.reference("RUN-BASE", relation)], [self.claim("CLM-RESEARCH")])
            self.run["review"] = self.review("retracted")
            self.save(self.run_path, self.run)
            graph = e.EvidenceGraph(self.root)
            state = graph.document_state(doc, doc.read_text(encoding="utf-8"), "bench:A")
            self.assertEqual(state["blocking_evidence_ids"], [])
            self.assertTrue(state["formal_eligible"])

    def test_retracting_one_claim_invalidates_consumers_of_whole_run(self):
        _, doc = self.research([self.reference("RUN-BASE")], [self.claim("CLM-RESEARCH")])
        e.review_claim(self.root, "CLM-BASE", "retracted", "tester", "synthetic counterexample")
        graph = e.EvidenceGraph(self.root)
        self.assertIn("CLM-BASE", graph.document_state(doc)["blocking_evidence_ids"])
        self.assertEqual(graph.formal_text(doc, "bench:A")[0], "")

    def test_sidecar_cannot_replace_run_identity_and_missing_document_fails(self):
        with self.assertRaises(ValueError):
            e.EvidenceGraph(self.root).status("runs/base/absent.md", "bench:A")
        self.save(self.root / "knowledge/override.evidence.json", {"evidence_id": "EVD-OVERRIDE", "document_path": "runs/base/run.json", "claims": []})
        graph = e.EvidenceGraph(self.root)
        self.assertTrue(any("不能覆盖" in problem for problem in graph.errors))
        self.assertFalse(graph.status("CLM-BASE", "bench:A")["eligible"])

    def test_empty_formal_context_cli_returns_nonzero_and_keeps_manifest(self):
        with patch.object(cli, "find_workspace_root", return_value=self.root), redirect_stdout(io.StringIO()):
            code = cli.main(["retrieve-context", "合成校准", "--purpose", "formal", "--scope", "bench:B"])
        self.assertEqual(code, 1)
        self.assertTrue(list((self.root / "retrieval/generated").glob("CTX-*.json")))

    def test_legacy_link_to_retracted_run_is_explicitly_unclassified(self):
        _, doc = self.research()
        self.run["review"] = self.review("retracted")
        self.save(self.run_path, self.run)
        state = e.EvidenceGraph(self.root).document_state(doc, doc.read_text(encoding="utf-8"))
        self.assertIn("unclassified-reference:RUN-BASE", state["blocking_evidence_ids"])

    def test_formal_context_emits_only_good_claims_and_preserves_scope(self):
        _, doc = self.research(claims=[self.claim("CLM-GOOD"), self.claim("CLM-BAD", "not-reviewed")])
        self.run["claims"] = []
        self.save(self.run_path, self.run)
        first = context_engine.create(self.root, "合成校准综合", purpose="formal", scope="bench:A", full=[str(doc)])
        text = Path(first["context_path"]).read_text(encoding="utf-8")
        self.assertIn("CLM-GOOD", text)
        self.assertNotIn("CLM-BAD", text)
        self.assertNotIn("SHOULD-NOT-LEAK", text)
        self.assertEqual(text.count("Claim: CLM-GOOD"), 1)
        child = context_engine.feedback(self.root, first["context_id"], "unresolved", "assistant-observation", "需要更多证据")
        self.assertEqual(child["manifest"]["purpose"], "formal")
        self.assertEqual(child["manifest"]["scope"], "bench:A")

    def test_formal_context_never_truncates_claim_and_rejects_wrong_scope(self):
        result = r.search(self.root, "合成校准")
        wrong = r.assemble(self.root, result, purpose="formal", scope="bench:B")
        self.assertFalse(wrong["manifest"]["formal_claim_ids"])
        tiny = r.assemble(self.root, result, budget=500, purpose="formal", scope="bench:A")
        self.assertFalse(tiny["manifest"]["formal_claim_ids"])
        with self.assertRaises(ValueError):
            context_engine.create(self.root, "合成校准", purpose="formal")

    def test_changed_source_digest_blocks_previously_accepted_claim(self):
        self.source.write_text("新数据 99", encoding="utf-8")
        graph = e.EvidenceGraph(self.root)
        self.assertTrue(any("version-changed" in x for x in graph.claim_errors("CLM-BASE", "bench:A")))

    def test_review_changes_do_not_change_content_fingerprint(self):
        initial = e.EvidenceGraph(self.root).nodes["RUN-BASE"]["fingerprint"]
        self.run["review"] = self.review("disputed")
        self.save(self.run_path, self.run)
        self.assertEqual(initial, e.EvidenceGraph(self.root).nodes["RUN-BASE"]["fingerprint"])

    def test_formal_reuse_rechecks_sealed_run_files_beyond_claim_references(self):
        # Claim 只直接引用 source；更换另一个输入或产物不能靠未变的
        # manifest/seal 继续进入正式包，也应阻断下游研究中的结论。
        extra = self.put("data/catalog/auxiliary.txt", "辅助输入")
        updated = e.read(self.run_path)
        updated["inputs"].append(self.file_ref(extra))
        self.save(self.run_path, updated)
        e.review_claim(self.root, "CLM-BASE", "accepted", "tester", "input rechecked", "fixture", "bench:A")
        self.assertTrue(e.finalize_run(self.root, "RUN-BASE", "bench:A")["finalized"])
        _, doc = self.research([self.reference("RUN-BASE")], [self.claim("CLM-RESEARCH")])
        self.assertTrue(e.EvidenceGraph(self.root).formal_text(doc, "bench:A")[0])
        for path in (extra, self.artifact):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_text("被替换的字节", encoding="utf-8")
                graph = e.EvidenceGraph(self.root)
                self.assertEqual(graph.formal_text(self.run_path, "bench:A")[0], "")
                self.assertEqual(graph.formal_text(doc, "bench:A")[0], "")
                self.assertTrue(any("文件版本变化" in error for error in graph.claim_errors("CLM-BASE", "bench:A")))
                path.write_bytes(original)

    def test_missing_and_cyclic_dependencies_fail_without_looping(self):
        self.run["dependencies"] = [{"target": "RUN-MISSING", "relation": "input", "locator": "all", "sha256": "a" * 64}]
        self.save(self.run_path, self.run)
        self.assertFalse(e.check_run(self.root, "RUN-BASE", "bench:A")["eligible"])
        self.run["dependencies"] = [{"target": "CLM-BASE", "relation": "input", "locator": "all", "sha256": e.fingerprint(self.run["claims"][0])}]
        self.save(self.run_path, self.run)
        self.assertTrue(any("dependency-cycle" in b for b in e.EvidenceGraph(self.root).nodes["RUN-BASE"]["blockers"]))

    def test_unregistered_external_reference_is_not_read(self):
        outside = self.root.parent / "do-not-read.txt"
        self.run["claims"][0]["evidence_refs"][0]["target"] = str(outside)
        self.save(self.run_path, self.run)
        with patch.object(e, "sha256", wraps=e.sha256) as hash_spy:
            graph = e.EvidenceGraph(self.root)
            self.assertTrue(any("未逐文件登记" in b for b in graph.nodes["CLM-BASE"]["blockers"]))
            self.assertNotIn(outside, [c.args[0] for c in hash_spy.call_args_list])

    def test_review_claim_preview_history_and_accepted_guards(self):
        before = self.run_path.read_bytes()
        e.review_claim(self.root, "CLM-BASE", "disputed", "tester", "synthetic", dry_run=True)
        self.assertEqual(before, self.run_path.read_bytes())
        e.review_claim(self.root, "CLM-BASE", "retracted", "tester", "synthetic")
        saved = e.read(self.run_path)
        self.assertEqual(saved["status"], "succeeded")
        self.assertEqual(saved["claims"][0]["review_history"][-1]["previous"]["status"], "accepted")
        with self.assertRaises(ValueError):
            e.review_claim(self.root, "CLM-BASE", "accepted", "tester", "synthetic", scope="bench:B")
        e.review_claim(self.root, "CLM-BASE", "accepted", "tester", "synthetic", "checked fixture", "bench:A")
        self.assertEqual(len(e.read(self.run_path)["claims"][0]["review_history"]), 2)

    def test_finalize_preview_change_detection_and_reseal(self):
        before = self.run_path.read_bytes()
        self.assertTrue(e.finalize_run(self.root, "RUN-BASE", "bench:A", True)["eligible"])
        self.assertEqual(before, self.run_path.read_bytes())
        self.assertTrue(e.finalize_run(self.root, "RUN-BASE", "bench:A")["finalized"])
        updated = e.read(self.run_path)
        updated["parameters"] = {"synthetic": 2}
        self.save(self.run_path, updated)
        self.assertFalse(e.check_run(self.root, "RUN-BASE", "bench:A")["eligible"])
        e.review_claim(self.root, "CLM-BASE", "accepted", "tester", "parameters rechecked", "checked fixture", "bench:A")
        self.assertTrue(e.finalize_run(self.root, "RUN-BASE", "bench:A")["finalized"])
        self.assertGreaterEqual(len(e.read(self.run_path)["finalization_history"]), 2)

    def test_editing_claim_does_not_reuse_previous_acceptance(self):
        self.run["claims"][0]["statement"] = "被修改的结论 999"
        self.save(self.run_path, self.run)
        graph = e.EvidenceGraph(self.root)
        self.assertTrue(any("review-content-changed" in error for error in graph.claim_errors("CLM-BASE", "bench:A")))
        self.assertEqual(graph.formal_text(self.run_path, "bench:A")[0], "")

    def test_accepted_but_unfinalized_run_cannot_export_formal_claim(self):
        self.save(self.run_path, self.run)  # 没有 finalization 的原始 fixture
        graph = e.EvidenceGraph(self.root)
        self.assertEqual(graph.formal_text(self.run_path, "bench:A")[0], "")

    def test_skipped_required_check_blocks_finalize(self):
        self.run["quality_results"][0]["status"] = "skipped"
        self.save(self.run_path, self.run)
        self.assertFalse(e.finalize_run(self.root, "RUN-BASE", "bench:A")["finalized"])
        # 损坏的检查项不能在筛选 required 时被静默丢弃。
        self.run["quality_results"] = [{"check": "valid", "status": "passed"}, "malformed required check"]
        self.save(self.run_path, self.run)
        self.assertTrue(any("quality_results" in error for error in e.check_run(self.root, "RUN-BASE", "bench:A")["errors"]))

    def test_duplicate_ids_bad_schema_and_atomic_stale_write(self):
        self.research(claims=[self.claim("CLM-BASE")])
        self.assertTrue(e.EvidenceGraph(self.root).errors)
        with self.assertRaises(ValueError):
            e.replace(self.run_path, {}, "0" * 64)
        self.assertEqual(e.read(self.run_path)["run_id"], "RUN-BASE")


class HealthTests(unittest.TestCase):
    def test_full_verification_cannot_pass_skipped_tests(self):
        tests = {"status": "completed", "total": 5, "failures": 0, "errors": 0, "skipped": 1}
        with patch.object(health, "doctor", return_value={"eligible": True}), patch.object(health, "worker", return_value=tests):
            self.assertFalse(health.verify(ROOT, "full")["eligible"])
            core = health.verify(ROOT, "core")
            self.assertEqual(core["status"], "passed-with-skips")
            self.assertFalse(core["full_integration_verified"])

    def test_missing_components_are_reported_separately(self):
        with patch.object(health, "available", return_value=False):
            result = health.doctor(ROOT, required=["vector", "ocr"])
        self.assertFalse(result["eligible"])
        self.assertEqual(result["capabilities"]["fts"]["status"], "ready")
        self.assertEqual(set(result["unmet"]), {"vector", "ocr"})

    def test_cli_formal_failure_has_nonzero_exit(self):
        with patch.object(cli, "find_workspace_root", return_value=ROOT), redirect_stdout(io.StringIO()):
            with patch.object(health, "doctor", return_value={"eligible": False}):
                self.assertEqual(cli.main(["doctor", "--require", "vector"]), 1)


if __name__ == "__main__":
    unittest.main()
