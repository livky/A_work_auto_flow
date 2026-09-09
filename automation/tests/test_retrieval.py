"""用隔离语料验证召回、全文上下文、变更和反馈；不下载模型或访问外部服务。"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("retrieval", ROOT / "automation/scripts/retrieval.py")
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "retrieval").mkdir()
        for name in ("config.json", "sources.json", "eval.json"):
            (self.root / "retrieval" / name).write_bytes((ROOT / "retrieval" / name).read_bytes())
        # 来源登记属于业务数据，可能含生产工作区的绝对路径。隔离测试只能
        # 读取本测试显式登记的材料，不能因用户新增来源而扫描真实研究正文。
        r.write_json(self.root / "retrieval/sources.json", {"sources": []})
        cfg = r.config(self.root)
        cfg["vector_store"] = {"provider": None}
        cfg["ocr_enabled"] = False
        r.write_json(self.root / "retrieval/config.json", cfg)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def register(self, sources):
        r.write_json(self.root / "retrieval/sources.json", {"sources": sources})

    def test_chinese_short_words_identifiers_and_full_related_context(self):
        doc = self.put("projects/demo/models/align.md", "# 时间对齐\n模块 ID：MOD-DEMO-ALIGN\n温漂需先检查采样率。\n[实现](../code/align.py)\n末尾完整说明。")
        code = self.put("projects/demo/code/align.py", "def align_signals(t):\n    return t\n# FULL-CODE-END\n")
        self.assertEqual(r.index(self.root)["updated"], 2)
        for query in ("温漂", "align_signals"):
            result = r.search(self.root, query, limit=1)
            self.assertEqual(len(result["results"]), 1)
            pack = r.assemble(self.root, result, 10000)
            self.assertIn("末尾完整说明", pack["text"])
            self.assertIn("FULL-CODE-END", pack["text"])
            self.assertEqual({e["path"] for e in pack["manifest"]["sources"]}, {str(doc), str(code)})
            self.assertTrue(all(e["mode"] == "full" for e in pack["manifest"]["sources"]))

    def test_incremental_update_removal_and_stale_pack(self):
        path = self.put("knowledge/patterns/a.md", "旧关键字 温漂")
        r.index(self.root)
        self.assertEqual(r.index(self.root)["unchanged"], 1)
        result = r.search(self.root, "温漂")
        path.write_text("新关键字 混叠", encoding="utf-8")
        pack = r.assemble(self.root, result)
        self.assertEqual(pack["manifest"]["sources"][0]["mode"], "omitted")
        self.assertEqual(r.search(self.root, "温漂")["results"], [])
        self.assertEqual(len(r.search(self.root, "混叠")["results"]), 1)
        path.unlink()
        self.assertEqual(r.search(self.root, "混叠")["results"], [])

    def test_budget_only_falls_back_when_full_does_not_fit(self):
        self.put("projects/demo/long.md", "无关开头\n" * 1500 + "温漂证据在结尾，保持定位。\n" * 20)
        result = r.search(self.root, "温漂", limit=1)
        full = r.assemble(self.root, result, 30000)
        self.assertEqual(full["manifest"]["sources"][0]["mode"], "full")
        short = r.assemble(self.root, result, 1700)
        self.assertLessEqual(len(short["text"]), 1700)
        self.assertEqual(short["manifest"]["sources"][0]["mode"], "excerpt")
        self.assertIn("温漂", short["text"])

    def test_run_state_updates_apply_to_results_and_key_output(self):
        base = "projects/demo/analysis/runs/a/"
        path = self.put(base + "run.json", json.dumps({"run_id": "RUN-A", "title": "温漂", "review": {"status": "accepted"}}, ensure_ascii=False))
        self.put(base + "README.md", "# 关键结果\n偏差下降 2 单位。")
        child = self.put("projects/demo/analysis/runs/b/run.json", json.dumps({"run_id": "RUN-B", "title": "温漂下游", "parent_run_ids": ["RUN-A"]}, ensure_ascii=False))
        r.index(self.root)
        run = r.read_json(path)
        run["review"]["status"] = "retracted"
        r.write_json(path, run)
        result = r.search(self.root, "温漂")
        self.assertTrue(all("RUN-A" in h["blocking_run_ids"] for h in result["results"]))
        pack = r.assemble(self.root, result)
        readme = next(e for e in pack["manifest"]["sources"] if e["path"].endswith("README.md"))
        self.assertEqual(readme["review"]["status"], "retracted")
        self.assertIn("RUN-A", readme["blocking_run_ids"])

    def test_feedback_is_append_only_and_alias_changes_are_evaluable(self):
        path = self.put("knowledge/patterns/a.md", "# alignment\n算法说明")
        result = r.search(self.root, "对时")
        self.assertFalse(result["results"])
        a = r.feedback(self.root, result["query_id"], str(path), "missing", "应该找到 alignment", "user")
        b = r.feedback(self.root, result["query_id"], str(path), "missing", "补充别名", "assistant-observation")
        self.assertNotEqual(a["feedback_id"], b["feedback_id"])
        cfg = r.config(self.root)
        cfg["aliases"] = {"对时": ["alignment"]}
        r.write_json(self.root / "retrieval/config.json", cfg)
        r.write_json(self.root / "retrieval/eval.json", {"cases": [{"query": "对时", "expected": ["knowledge/patterns/a.md"]}]})
        before = list((self.root / "retrieval/queries").glob("*.json"))
        evaluation = r.evaluate(self.root, self.root / "retrieval/eval.json")
        self.assertEqual(evaluation["recall_at_k"], 1)
        self.assertEqual(list((self.root / "retrieval/queries").glob("*.json")), before)
        self.assertEqual(len(list((self.root / "retrieval/feedback").glob("*.json"))), 2)

    def test_project_filter_and_literal_query(self):
        self.put("projects/a/note.md", "温漂 唯一项目甲")
        self.put("projects/b/note.md", "温漂 唯一项目乙")
        result = r.search(self.root, '温漂 " OR *', project="b")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["meta"]["project"], "b")

    def test_external_sources_are_explicit_and_links_do_not_expand_scope(self):
        with tempfile.TemporaryDirectory() as ext:
            external = Path(ext) / "algo.py"
            external.write_text("# 外部算法 温漂", encoding="utf-8")
            self.put("projects/demo/a.md", f"# 温漂\n[外部]({external.as_posix()})")
            self.assertEqual(len(r.search(self.root, "温漂")["results"]), 1)
            self.register([{"path": str(external), "project": "demo", "module_ids": ["MOD-X"]}])
            self.assertEqual(len(r.search(self.root, "温漂")["results"]), 2)
            self.assertEqual(external.read_text(encoding="utf-8"), "# 外部算法 温漂")

    def test_unreadable_large_and_disabled_sources_do_not_reuse_old_content(self):
        path = self.put("projects/demo/a.md", "温漂")
        self.assertTrue(r.search(self.root, "温漂")["results"])
        path.write_bytes(b"\xff\xfe\x00")
        result = r.search(self.root, "温漂")
        self.assertFalse(result["results"])
        self.assertTrue(result["index_status"]["unavailable"])
        path.write_text("温漂", encoding="utf-8")
        self.register([{"path": "projects/demo/a.md", "enabled": False}])
        self.assertFalse(r.search(self.root, "温漂")["results"])

    def test_dry_run_and_empty_eval(self):
        self.put("projects/demo/a.md", "温漂")
        self.assertEqual(r.index(self.root, dry_run=True)["count"], 1)
        self.assertFalse((self.root / "retrieval/generated").exists())
        self.assertIsNone(r.evaluate(self.root, self.root / "retrieval/eval.json")["mrr"])

    def test_alias_command_preview_history_and_feedback_report(self):
        before = (self.root / "retrieval/config.json").read_bytes()
        r.add_alias(self.root, "对时", ["alignment"], dry_run=True)
        self.assertEqual(before, (self.root / "retrieval/config.json").read_bytes())
        self.assertFalse((self.root / "retrieval/strategies").exists())
        event = r.add_alias(self.root, "对时", ["alignment"])
        self.assertEqual(event["before"]["aliases"], {})
        self.assertEqual(r.config(self.root)["aliases"]["对时"], ["alignment"])
        result = r.search(self.root, "对时")
        r.feedback(self.root, result["query_id"], "待提供材料", "missing", "未找到", "user")
        self.assertEqual(r.feedback_report(self.root)["labels"], {"missing": 1})

    def test_parent_change_after_search_is_visible_in_child_context(self):
        parent = self.put("projects/demo/analysis/runs/a/run.json", json.dumps({"run_id": "RUN-A", "title": "上游", "review": {"status": "accepted"}}))
        self.put("projects/demo/analysis/runs/b/run.json", json.dumps({"run_id": "RUN-B", "title": "独有标定", "parent_run_ids": ["RUN-A"]}, ensure_ascii=False))
        result = r.search(self.root, "独有标定", limit=1)
        run = r.read_json(parent)
        run["review"]["status"] = "retracted"
        r.write_json(parent, run)
        pack = r.assemble(self.root, result)
        self.assertIn("RUN-A", pack["manifest"]["sources"][0]["blocking_run_ids"])

    def test_docx_extraction_and_bad_run_are_reported(self):
        import zipfile
        target = self.root / "projects/demo/algorithm.docx"
        target.parent.mkdir(parents=True)
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>温漂算法说明</w:t></w:r></w:p></w:body></w:document>')
        self.put("projects/demo/analysis/runs/bad/run.json", "[]")
        result = r.search(self.root, "温漂")
        self.assertEqual(len(result["results"]), 1)
        self.assertTrue(result["index_status"]["unavailable"])

    def test_limit_failure_does_not_remove_previous_index(self):
        self.put("projects/demo/a.md", "温漂")
        result = r.search(self.root, "温漂")
        self.put("projects/demo/b.md", "混叠")
        cfg = r.config(self.root)
        cfg["max_files"] = 1
        r.write_json(self.root / "retrieval/config.json", cfg)
        with self.assertRaises(ValueError):
            r.index(self.root)
        with r.closing(r.connect(self.root)) as db:
            self.assertIn(result["results"][0]["source_id"], r.read_docs(db))

    def test_module_filter_precedes_candidate_limit(self):
        self.put("core-algorithms/other/module.json", json.dumps({"module_id": "MOD-OTHER"}))
        self.put("core-algorithms/other/a.md", "温漂 " * 30)
        self.put("core-algorithms/right/module.json", json.dumps({"module_id": "MOD-RIGHT"}))
        target = self.put("core-algorithms/right/a.md", "温漂")
        cfg = r.config(self.root)
        cfg["candidate_limit"] = 1
        r.write_json(self.root / "retrieval/config.json", cfg)
        result = r.search(self.root, "温漂", module="MOD-RIGHT")
        self.assertEqual(result["results"][0]["path"], str(target))

    def test_crlf_and_run_directory_do_not_inflate_context(self):
        target = self.put("runs/guide.md", "")
        target.write_bytes("# Guide\r\n温漂\r\nEND\r\n".encode())
        self.put("runs/other.md", "UNRELATED-SENTINEL")
        pack = r.assemble(self.root, r.search(self.root, "温漂"))
        self.assertIn("# Guide\n温漂\nEND\n", pack["text"])
        self.assertNotIn("UNRELATED-SENTINEL", pack["text"])


if __name__ == "__main__":
    unittest.main()
