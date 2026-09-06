"""验证阅读基线、选择覆盖、受限扩展和原样反馈，不用真实业务材料。"""
import json
from pathlib import Path

import unittest
import test_retrieval as fixture
from test_retrieval import ROOT, r
import context_engine as engine


class ContextEngineTests(unittest.TestCase):
    put = fixture.RetrievalTests.put
    tearDown = fixture.RetrievalTests.tearDown
    def setUp(self):
        fixture.RetrievalTests.setUp(self)
        self.put("retrieval/context-policy.json", (ROOT / "retrieval/context-policy.json").read_text(encoding="utf-8"))
        self.put("core-algorithms/align/module.json", json.dumps({"module_id": "MOD-ALIGN", "aliases": ["对时"]}))
        self.card = self.put("core-algorithms/align/README.md", "# 时间对齐\n设计假设：所有样本等间隔。\n算法关键说明。")
        self.code = self.put("core-algorithms/align/code/align.py", "def align_signal(x):\n    # 实现允许不等间隔，需要核对设计差异\n    return x\n\ndef irrelevant_app():\n    pass\n" + "# unrelated\n" * 1200)
        self.app = self.put("core-algorithms/align/apps/ui.py", "APP-ONLY-SENTINEL")

    def test_algorithm_baseline_and_function_scope(self):
        pack = engine.create(self.root, "align_signal", module="MOD-ALIGN")
        loaded = {s["path"]: s for s in pack["manifest"]["sources"]}
        self.assertEqual(loaded[str(self.card)]["mode"], "full")
        self.assertEqual(loaded[str(self.code)]["code_unit"], "align_signal")
        self.assertTrue(loaded[str(self.code)]["code_unit_complete"])
        text = Path(pack["context_path"]).read_text(encoding="utf-8")
        self.assertIn("不等间隔", text)
        self.assertNotIn("APP-ONLY-SENTINEL", text)
        self.assertFalse(pack["manifest"]["required_not_full"])

    def test_software_functions_do_not_become_core_algorithm_evidence(self):
        """工具即使关联 MOD-ID 也不是核心实现；规则页和辅助说明不作算法基线。"""
        for relative in ("tools/scripts/plot.py", "automation/scripts/index.py", "core-algorithms/align/apps/ui.py", "core-algorithms/align/code/utils/io.py"):
            doc = {"path": str(self.root / relative), "meta": {"kind": "code", "module_ids": ["MOD-ALIGN"]}}
            self.assertEqual(engine.role(self.root, doc), "application-code")
        for relative in ("core-algorithms/AGENTS.md", "core-algorithms/align/apps/README.md"):
            doc = {"path": str(self.root / relative), "meta": {"module_ids": ["MOD-ALIGN"]}}
            self.assertEqual(engine.role(self.root, doc), "document")
        external = {"path": str(self.root / "external/core.py"), "meta": {"kind": "code", "context_role": "core-code", "module_ids": ["MOD-ALIGN"]}}
        self.assertEqual(engine.role(self.root, external), "core-code")

    def test_user_choices_persist_and_can_be_reversed(self):
        pack = engine.create(self.root, "align_signal", module="MOD-ALIGN", exclude=[str(self.code)], full=[str(self.app)])
        self.assertNotIn(str(self.code), [s["path"] for s in pack["manifest"]["sources"]])
        child = engine.feedback(self.root, pack["context_id"], "unresolved", "assistant-observation", "需要核对代码与文档", include=[str(self.code)], exclude=[str(self.app)])
        self.assertEqual(child["status"], "expanded")
        self.assertEqual(child["stage"], "investigate")
        self.assertIn(str(self.code), [s["path"] for s in child["manifest"]["sources"]])
        self.assertNotIn(str(self.app), [s["path"] for s in child["manifest"]["sources"]])
        self.assertTrue((self.root / "retrieval/sessions" / (pack["context_id"] + ".json")).exists())

    def test_expansion_searches_cross_module_but_keeps_budget_and_stops(self):
        cross = self.put("knowledge/alternative.md", "align_signal 可能受到标定版本影响。")
        first = engine.create(self.root, "align_signal", module="MOD-ALIGN", budget=8000)
        second = engine.feedback(self.root, first["context_id"], "conflict", "assistant-observation", "文档与实现假设冲突")
        third = engine.feedback(self.root, second["context_id"], "unresolved", "assistant-observation", "需要跨模块反证")
        self.assertEqual(third["stage"], "wide")
        self.assertIn(str(cross), [s["path"] for s in third["manifest"]["sources"]])
        self.assertLessEqual(third["manifest"]["used_chars"], 8000)
        last = engine.feedback(self.root, third["context_id"], "unresolved", "assistant-observation", "仍缺原始测量")
        self.assertIn("expansion-limit", last["status"])
        self.assertEqual(len(list((self.root / "retrieval/sessions").glob("*.json"))), 3)

    def test_large_run_brief_and_excluded_required_are_explicit(self):
        run = self.put("runs/r/run.json", json.dumps({"run_id": "RUN-A", "title": "align_signal result", "related_module_ids": ["MOD-ALIGN"], "conclusion": "观察到偏差，尚未复核", "review": {"status": "disputed"}, "debug": "noise" * 10000}, ensure_ascii=False))
        pack = engine.create(self.root, "align_signal result", module="MOD-ALIGN", exclude=[str(self.card)])
        loaded = {s["path"]: s for s in pack["manifest"]["sources"]}
        self.assertEqual(loaded[str(run)]["mode"], "brief")
        self.assertTrue(pack["manifest"]["required_not_full"])
        text = Path(pack["context_path"]).read_text(encoding="utf-8")
        self.assertIn("disputed", text)
        self.assertNotIn("noisenoisenoise", text)

    def test_preferences_and_unindexed_file_boundaries(self):
        policy = engine.policy(self.root)
        policy["preferences"]["modules"]["MOD-ALIGN"] = {"exclude": [str(self.code)]}
        r.write_json(self.root / "retrieval/context-policy.json", policy)
        pack = engine.create(self.root, "align_signal", module="MOD-ALIGN")
        self.assertNotIn(str(self.code), [s["path"] for s in pack["manifest"]["sources"]])
        with self.assertRaises(ValueError):
            engine.create(self.root, "align_signal", include=["outside/unregistered.py"])
        with self.assertRaises(ValueError):
            engine.create(self.root, "align_signal", include=[str(self.app)], exclude=[str(self.app)])

    def test_solved_feedback_does_not_expand_or_change_truth(self):
        pack = engine.create(self.root, "align_signal", module="MOD-ALIGN")
        result = engine.feedback(self.root, pack["context_id"], "solved", "user", "已找到需要检查的函数")
        self.assertEqual(result["status"], "recorded; no expansion")
        self.assertEqual(len(list((self.root / "retrieval/sessions").glob("*.json"))), 1)

    def test_required_budget_gap_and_missing_algorithm_are_visible(self):
        self.card.write_text("算法基线必须核对。" * 1000, encoding="utf-8")
        pack = engine.create(self.root, "align_signal", module="MOD-ALIGN", budget=600)
        self.assertTrue(pack["manifest"]["required_not_full"])
        self.assertLessEqual(pack["manifest"]["used_chars"], 600)
        absent = engine.create(self.root, "align_signal", module="MOD-MISSING")
        self.assertEqual(absent["manifest"]["module_algorithm_missing"], ["MOD-MISSING"])

    def test_source_keywords_and_role_override(self):
        self.put("retrieval/sources.json", json.dumps({"sources": [{"path": str(self.app), "keywords": ["uniquemapping"], "context_role": "core-code", "consistency": "mismatch"}]}))
        pack = engine.create(self.root, "uniquemapping", module="MOD-ALIGN")
        entries = {i["path"]: i for i in pack["manifest"]["sources"]}
        self.assertEqual(entries[str(self.app)]["role"], "core-code")
        self.assertEqual(entries[str(self.app)]["consistency"], "mismatch")
