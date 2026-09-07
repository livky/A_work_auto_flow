"""workspace_cli 的关键安全与可复现行为测试。"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPOSITORY_ROOT / "automation" / "scripts" / "workspace_cli.py"
SPEC = importlib.util.spec_from_file_location("workspace_cli", MODULE_PATH)
assert SPEC and SPEC.loader
workspace_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workspace_cli)


class WorkspaceCliTests(unittest.TestCase):
    """用临时目录验证创建命令，避免把测试对象写进真实工作区。"""

    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)

        # 只复制测试需要的最小控制平面；真实工作区的其他内容不会影响结果。
        shutil.copy2(REPOSITORY_ROOT / "workspace.json", self.root / "workspace.json")
        shutil.copytree(REPOSITORY_ROOT / "projects" / "_template", self.root / "projects" / "_template")
        shutil.copytree(REPOSITORY_ROOT / "research" / "_template", self.root / "research" / "_template")
        shutil.copytree(REPOSITORY_ROOT / "core-algorithms" / "_template", self.root / "core-algorithms" / "_template")
        (self.root / "context" / "generated").mkdir(parents=True)
        (self.root / "data" / "catalog").mkdir(parents=True)
        (self.root / "knowledge" / "decisions").mkdir(parents=True)
        (self.root / "knowledge" / "incidents").mkdir(parents=True)
        (self.root / "knowledge" / "patterns").mkdir(parents=True)
        (self.root / "tools").mkdir(parents=True)
        (self.root / "tools" / "registry.json").write_text(
            json.dumps({"schema_version": 1, "tools": []}), encoding="utf-8"
        )

        # 上下文构建需要的全局入口使用最小哨兵文本，方便精确断言。
        (self.root / "AGENTS.md").write_text("ROOT-SENTINEL\n", encoding="utf-8")
        (self.root / "ARCHITECTURE.md").write_text("ARCH-SENTINEL\n", encoding="utf-8")
        (self.root / "context" / "START_HERE.md").write_text("START-SENTINEL\n", encoding="utf-8")
        (self.root / "context" / "NOW.md").write_text("NOW-SENTINEL\n", encoding="utf-8")
        (self.root / "context" / "SYSTEM_MAP.md").write_text("MAP-SENTINEL\n", encoding="utf-8")
        (self.root / "context" / "GLOSSARY.md").write_text("GLOSSARY-SENTINEL\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_slugify_rejects_non_ascii_only_identifier(self) -> None:
        """显示标题可用中文，但机器 slug 必须保持跨工具安全。"""

        self.assertEqual(workspace_cli.slugify(" Demo_Project 01 "), "demo-project-01")
        with self.assertRaises(ValueError):
            workspace_cli.slugify("纯中文标题")

    def test_tool_registry_accepts_files_and_directories_but_rejects_missing_paths(self):
        """复现旧工作区登记包/脚本目录时，升级 validate 误报入口不存在。"""
        baseline_errors, _ = workspace_cli.validate_workspace(self.root)
        entries = ['tools/packages/example_library', 'tools/scripts/example_tools', 'tools/scripts/example.py']
        for name in entries[:2]:
            (self.root / name).mkdir(parents=True)
        (self.root / entries[2]).write_text('# Synthetic CLI\n', encoding='utf-8')
        tools = [{'tool_id': f'TOOL-TEST-{i}', 'entrypoint': name} for i, name in enumerate(entries)]
        registry = self.root / 'tools/registry.json'
        registry.write_text(json.dumps({'schema_version': 1, 'tools': tools}), encoding='utf-8')
        before = registry.read_bytes()
        errors, _ = workspace_cli.validate_workspace(self.root)
        # 共用 fixture 是最小工作区，保留其原有缺失项，只比较此次登记的增量。
        self.assertEqual(errors, baseline_errors)
        self.assertEqual(registry.read_bytes(), before)
        # 对同一批真实路径制造缺失，确保修复没有把存在性校验整体跳过。
        (self.root / entries[0]).rmdir()
        (self.root / entries[2]).unlink()
        errors, _ = workspace_cli.validate_workspace(self.root)
        failures = [e for e in errors if '工具入口不存在' in e]
        self.assertEqual(len(failures), 2)
        self.assertTrue(any('TOOL-TEST-0' in e for e in failures))
        self.assertTrue(any('TOOL-TEST-2' in e for e in failures))
        self.assertFalse(any('TOOL-TEST-1' in e for e in failures))
        self.assertTrue(all(str(self.root) in e for e in failures))

    def test_global_modules_runs_and_optional_projects(self):
        module = workspace_cli.create_module(self.root, "align", "对齐", source_document="公司测校项文档 TEST-ALIGN")
        self.assertEqual(module.parent, self.root / "core-algorithms")
        self.assertEqual({p.name for p in module.iterdir()}, {"module.json", "README.md"})
        context = workspace_cli.build_context(self.root, module="align", task="检查全局模块")
        self.assertIn("MOD-ALIGN", context.read_text(encoding="utf-8"))
        run = workspace_cli.create_run(self.root, None, "独立分析", module_ids=["MOD-ALIGN"], research_ids=["RES-TEST"])
        self.assertEqual(run.parent, self.root / "runs")
        self.assertIsNone(json.loads((run / "run.json").read_text(encoding="utf-8"))["project_id"])
        self.assertEqual(len(workspace_cli.search_runs(self.root, "MOD-ALIGN")), 1)
        index, _ = workspace_cli.refresh_index(self.root)
        self.assertIn("MOD-ALIGN", index.read_text(encoding="utf-8"))
        project = workspace_cli.create_project(self.root, "view", "可选视图")
        self.assertFalse((project / "models").exists())
        self.assertFalse((project / "analysis").exists())

    def test_core_algorithm_requires_document_even_for_legacy_command(self):
        """缺来源时在写入前拒绝；旧命令不能绕过新的业务对象边界。"""
        for source in (None, "", "   "):
            with self.assertRaises(ValueError):
                workspace_cli.create_module(self.root, "helper", "辅助函数", source_document=source)
        self.assertFalse((self.root / "core-algorithms/helper").exists())
        parser = workspace_cli.build_parser()
        for command in ("new-core-algorithm", "new-module"):
            with self.assertRaises(SystemExit):
                parser.parse_args([command, "helper", "--title", "辅助函数"])
            args = parser.parse_args([command, "align", "--title", "对齐", "--source-document", "DOC-ALIGN"])
            self.assertEqual(args.source_document, "DOC-ALIGN")
        reference = '公司文档 "测校项" C:\\受控资料\\算法.docx'
        target = workspace_cli.create_module(self.root, "align", "对齐", source_document=reference)
        metadata = json.loads((target / "module.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["source_document"], reference)
        self.assertEqual(metadata["entity_kind"], "core-algorithm")
        self.assertEqual(metadata["source_reading_status"], "registered-only")
        metadata["source_document"] = ""
        (target / "module.json").write_text(json.dumps(metadata), encoding="utf-8")
        errors, _ = workspace_cli.validate_workspace(self.root)
        self.assertTrue(any("核心算法缺少公司文档引用" in e for e in errors))
        workspace_cli.create_module(self.root, "preview", "预览", dry_run=True, source_document="DOC-TEST")
        self.assertFalse((self.root / "core-algorithms/preview").exists())

    def test_legacy_run_path_still_supports_review(self):
        directory = self.root / "projects/legacy/analysis/runs/old"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"run_id": "RUN-OLD", "title": "旧记录", "project_id": "PRJ-LEGACY"}), encoding="utf-8")
        workspace_cli.review_run(self.root, "RUN-OLD", "disputed", "用户", "待核对")
        self.assertTrue(workspace_cli.search_runs(self.root, project="legacy")[0]["needs_revalidation"])

    def test_project_and_run_creation_preserve_traceability(self) -> None:
        project_dir = workspace_cli.create_project(self.root, "demo-project", "演示项目")
        metadata = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project_id"], "PRJ-DEMO-PROJECT")
        self.assertNotIn("{{project_id}}", (project_dir / "README.md").read_text(encoding="utf-8"))

        run_dir = workspace_cli.create_run(self.root, "demo-project", "signal check")
        run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(run["project_id"], "PRJ-DEMO-PROJECT")
        self.assertEqual(run["status"], "planned")
        self.assertIn("inputs", run)
        self.assertIn("environment", run)
        self.assertTrue((run_dir / "lineage.jsonl").is_file())

    def test_refresh_index_and_bounded_context(self) -> None:
        workspace_cli.create_project(self.root, "demo", "演示")
        index_path, warnings = workspace_cli.refresh_index(self.root)
        self.assertEqual(warnings, [])
        self.assertIn("PRJ-DEMO", index_path.read_text(encoding="utf-8"))

        context_path = workspace_cli.build_context(
            self.root, project="demo", task="验证上下文边界"
        )
        context = context_path.read_text(encoding="utf-8")
        self.assertIn("ROOT-SENTINEL", context)
        self.assertIn("PRJ-DEMO", context)
        self.assertIn("验证上下文边界", context)

    def test_existing_destination_is_never_overwritten(self) -> None:
        workspace_cli.create_project(self.root, "demo", "第一次")
        with self.assertRaises(FileExistsError):
            workspace_cli.create_project(self.root, "demo", "第二次")

    def test_titles_preserve_quotes_paths_and_literal_template_tokens(self):
        """真实材料标题常含引号/路径，创建后必须仍是有效 JSON 且原文不变。"""
        title = '算法 "A"：C:\\models\\new\n字面量 {{date}}'
        project = workspace_cli.create_project(self.root, "quoted", title)
        research = workspace_cli.create_research(self.root, "quoted", title)
        for directory, filename in ((project, "project.json"), (research, "research.json")):
            self.assertEqual(json.loads((directory / filename).read_text(encoding="utf-8"))["title"], title)

    def test_bad_metadata_is_reported_and_generated_reports_are_excluded(self):
        """坏元数据不应导致索引 traceback，生成报告不参与正式源文本检查。"""
        path = self.root / "data/catalog/bad.dataset.json"
        path.write_text("[]", encoding="utf-8")
        _, warnings = workspace_cli.refresh_index(self.root)
        self.assertTrue(any("对象元数据" in warning for warning in warnings))
        report = self.root / "reports/generated/example.md"
        report.parent.mkdir(parents=True)
        report.write_text("generated", encoding="utf-8")
        self.assertNotIn(report, list(workspace_cli.iter_small_text_files(self.root)))

    def test_angle_bracket_links_with_spaces_are_checked(self):
        """尖括号只是 Markdown 路径包裹，不能借此绕过坏链接检查。"""
        (self.root / "link.md").write_text("[missing](<missing file.md>)", encoding="utf-8")
        _, warnings = workspace_cli.validate_workspace(self.root)
        self.assertTrue(any("missing file.md" in warning for warning in warnings))

    def make_run(self, title="漂移分析", parents=()):
        """在临时项目建立可查询证据，避免测试依赖真实项目或公司数据。"""
        if not (self.root / "projects/demo/project.json").exists():
            workspace_cli.create_project(self.root, "demo", "演示")
        directory = workspace_cli.create_run(self.root, "demo", title, keywords=["温漂", "alignment"])
        path = directory / "run.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record.update(status="succeeded", conclusion="本批次观测到漂移", parent_run_ids=list(parents))
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return path, record

    def test_chinese_titles_search_and_old_manifest(self):
        path, first = self.make_run()
        _, second = self.make_run()
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(len(workspace_cli.search_runs(self.root, "温漂 alignment", "demo")), 2)
        self.assertEqual(workspace_cli.search_runs(self.root, "不存在"), [])
        # 旧记录不需要迁移即可按标题与结论检索。
        first.pop("keywords")
        first.pop("review_history")
        path.write_text(json.dumps(first), encoding="utf-8")
        self.assertEqual(len(workspace_cli.search_runs(self.root, "漂移")), 2)
        workspace_cli.refresh_index(self.root)
        index = json.loads((self.root / "context/generated/run-index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(index), 2)
        self.assertIn(first["run_id"], (self.root / "context/generated/workspace-index.md").read_text(encoding="utf-8"))

    def test_review_history_retraction_and_transitive_impact(self):
        path, original = self.make_run()
        _, child = self.make_run("下游", [original["run_id"]])
        _, grandchild = self.make_run("再下游", [child["run_id"]])
        workspace_cli.review_run(self.root, original["run_id"], "accepted", "用户", "核对完毕", "原始记录", "本批次")
        result = workspace_cli.review_run(self.root, original["run_id"], "retracted", "用户", "对齐错误")
        self.assertEqual(set(result["affected_run_ids"]), {child["run_id"], grandchild["run_id"]})
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "succeeded")
        self.assertEqual(saved["conclusion"], original["conclusion"])
        self.assertEqual(saved["review_history"][-1]["previous"]["status"], "accepted")
        self.assertEqual(len(saved["review_history"]), 2)
        self.assertTrue(all(r["needs_revalidation"] for r in workspace_cli.search_runs(self.root)))
        # 不依赖 refresh-index，纠错后即时查询也必须看到当前状态。
        workspace_cli.review_run(self.root, original["run_id"], "accepted", "用户", "撤回误判", "新核对记录", "本批次")
        self.assertFalse(any(r["needs_revalidation"] for r in workspace_cli.search_runs(self.root)))

    def test_review_guards_dry_run_and_supersession(self):
        path, original = self.make_run()
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            workspace_cli.review_run(self.root, original["run_id"], "accepted", "用户", "可以")
        with self.assertRaises(ValueError):
            workspace_cli.review_run(self.root, original["run_id"], "superseded", "用户", "换了", replacement="missing")
        workspace_cli.review_run(self.root, original["run_id"], "disputed", "用户", "疑点", dry_run=True)
        self.assertEqual(before, path.read_bytes())
        _, replacement = self.make_run("纠正对齐")
        workspace_cli.review_run(self.root, original["run_id"], "superseded", "用户", "已重做", replacement=replacement["run_id"])
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["review"]["replacement_run_id"], replacement["run_id"])

    def test_missing_parent_and_duplicate_id_are_visible(self):
        _, original = self.make_run(parents=["RUN-MISSING"])
        self.assertIn("RUN-MISSING", workspace_cli.search_runs(self.root)[0]["blocking_run_ids"])
        path, other = self.make_run("重复ID")
        other["run_id"] = original["run_id"]
        path.write_text(json.dumps(other), encoding="utf-8")
        with self.assertRaises(ValueError):
            workspace_cli.search_runs(self.root)

    def test_cross_project_impact_and_cyclic_dependencies_terminate(self):
        path, first = self.make_run()
        workspace_cli.create_project(self.root, "other", "其他项目")
        other_dir = workspace_cli.create_run(self.root, "other", "跨项目复用")
        other_path = other_dir / "run.json"
        other = json.loads(other_path.read_text(encoding="utf-8"))
        other["parent_run_ids"] = [first["run_id"]]
        other_path.write_text(json.dumps(other), encoding="utf-8")
        # 环形关系可能来自历史手工登记；检索不能无限递归，也不能漏报失效源。
        first["parent_run_ids"] = [other["run_id"]]
        path.write_text(json.dumps(first), encoding="utf-8")
        workspace_cli.review_run(self.root, first["run_id"], "retracted", "用户", "输入有误")
        matches = workspace_cli.search_runs(self.root, project="other")
        self.assertEqual(len(matches), 1)
        self.assertIn(first["run_id"], matches[0]["blocking_run_ids"])

    def test_recent_navigation_is_bounded_but_full_index_is_complete(self):
        path, first = self.make_run()
        # 制造一批历史 manifest，验证导航不会随着全量历史无限膨胀。
        for number in range(25):
            record = {**first, "run_id": f"RUN-HISTORY-{number:02d}"}
            target = path.parent.parent / f"history-{number}" / "run.json"
            target.parent.mkdir()
            target.write_text(json.dumps(record), encoding="utf-8")
        index_path, _ = workspace_cli.refresh_index(self.root)
        index = json.loads((self.root / "context/generated/run-index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(index), 26)
        navigation = index_path.read_text(encoding="utf-8").split("## Run（最近 20 项）")[1]
        self.assertEqual(navigation.count("| `RUN-"), 20)
        self.assertEqual(len(workspace_cli.search_runs(self.root, limit=30)), 26)

    def test_workflow_sources_have_valid_minimal_skill_metadata(self) -> None:
        """工作流源保持可迁移格式；技能入口只引用源，不限制可扩展的总数量。"""

        workflow_root = REPOSITORY_ROOT / "automation" / "workflows"
        skill_paths = sorted(workflow_root.glob("*/SKILL.md"))
        self.assertTrue({"workspace-context", "context-maintenance"}.issubset({p.parent.name for p in skill_paths}))

        for path in skill_paths:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), path)
            parts = text.split("---\n", 2)
            self.assertEqual(len(parts), 3, path)
            frontmatter = parts[1]

            # 这些源当前只使用单行 name/description，不需要宽松解析完整 YAML。
            # 若以后加入复杂 metadata，应改用官方 skill-creator 校验器。
            name_match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", frontmatter, re.MULTILINE)
            description_match = re.search(r"^description:\s*(\S.*)$", frontmatter, re.MULTILINE)
            self.assertIsNotNone(name_match, path)
            self.assertIsNotNone(description_match, path)
            self.assertEqual(name_match.group(1), path.parent.name)
            self.assertGreater(len(description_match.group(1)), 20)


if __name__ == "__main__":
    unittest.main()
