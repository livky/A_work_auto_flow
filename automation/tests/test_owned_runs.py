"""对象内运行的创建、统一发现与失败边界；只使用隔离合成数据。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import workspace_cli
from evidence import EvidenceGraph
from memory import owners


class OwnedRunsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def test_all_owner_types_and_legacy_paths_share_discovery(self):
        specs = [('research/中文 专题/research.json', 'research_id', 'RES-A'),
                 ('projects/大项目/project.json', 'project_id', 'PRJ-A'),
                 ('core-algorithms/算法/module.json', 'module_id', 'MOD-A'),
                 ('runs/原运行/run.json', 'run_id', 'RUN-A'),
                 ('knowledge/分组/经验.evidence.json', 'evidence_id', 'KN-A'),
                 ('reports/sources/报告.evidence.json', 'evidence_id', 'REP-A'),
                 ('data/catalog/输入.dataset.json', 'dataset_id', 'DATA-A')]
        for path, field, oid in specs:
            value = {field: oid, 'title': oid}
            if field == 'evidence_id':
                doc = path.replace('.evidence.json', '.md')
                self.put(doc, 'synthetic')
                value['document_path'] = doc
            self.put(path, value)
        self.put('tools/registry.json', {'tools': [{'tool_id': 'TOOL-A', 'entrypoint': 'tools/worker.py'}]})
        self.put('tools/worker.py', 'synthetic')
        created = []
        for _, _, oid in specs:
            created.append(workspace_cli.create_run(self.root, None, '合成测试', owner_id=oid))
        created.append(workspace_cli.create_run(self.root, None, '工具测试', owner_id='TOOL-A'))
        for directory in created:
            self.assertNotEqual(directory.parent, self.root / 'runs')
            self.assertIsNotNone(json.loads((directory / 'run.json').read_text())['owner_id'])
        self.put('projects/legacy/analysis/runs/old/run.json', {'run_id': 'RUN-OLD'})
        collected = workspace_cli.collect_runs(self.root)
        graph = EvidenceGraph(self.root)
        self.assertFalse(graph.errors)
        self.assertEqual({r['run_id'] for r in collected}, {k for k, v in graph.nodes.items() if v['path'].name == 'run.json'})
        self.assertEqual(len(collected), 10)
        self.assertEqual(len([o for o in owners.list_owners(self.root) if o['owner_type'] == 'run']), 10)

    def test_auto_owner_explicit_override_ambiguity_and_preview(self):
        self.put('research/a/research.json', {'research_id': 'RES-A'})
        self.put('research/b/research.json', {'research_id': 'RES-B'})
        root_run = workspace_cli.create_run(self.root, None, '轻任务')
        self.assertEqual(root_run.parent, self.root / 'runs')
        auto = workspace_cli.create_run(self.root, None, '自动归属', research_ids=['RES-A'])
        self.assertEqual(auto.parent, self.root / 'research/a/runs')
        with self.assertRaisesRegex(ValueError, '歧义'):
            workspace_cli.create_run(self.root, None, '不确定', research_ids=['RES-A', 'RES-B'])
        explicit = workspace_cli.create_run(self.root, None, '共享关联', research_ids=['RES-A', 'RES-B'], owner_id='RES-B')
        self.assertEqual(explicit.parent, self.root / 'research/b/runs')
        before = set(self.root.rglob('*'))
        preview = workspace_cli.create_run(self.root, None, '预览', True, owner_id='RES-A')
        self.assertFalse(preview.exists())
        self.assertEqual(before, set(self.root.rglob('*')))
        with self.assertRaisesRegex(ValueError, '归属解析失败'):
            workspace_cli.create_run(self.root, None, '缺失', owner_id='RES-NOT-FOUND')

    def test_nested_duplicate_and_corrupt_manifests_fail(self):
        self.put('runs/a/run.json', {'run_id': 'RUN-A'})
        duplicate = self.put('research/x/runs/a/run.json', {'run_id': 'RUN-A'})
        with self.assertRaisesRegex(ValueError, '重复'):
            workspace_cli.collect_runs(self.root)
        self.assertTrue(EvidenceGraph(self.root).errors)
        duplicate.write_text(json.dumps({'run_id': 'run-a'}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '重复'):
            workspace_cli.collect_runs(self.root)
        self.assertTrue(EvidenceGraph(self.root).errors)
        duplicate.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            workspace_cli.collect_runs(self.root)
        self.assertTrue(EvidenceGraph(self.root).errors)

    def test_cache_and_memory_are_not_run_sources(self):
        for prefix in ('research/x/node_modules', 'research/x/memory', 'knowledge/a.md.memory', 'data/.local'):
            self.put(prefix + '/run.json', {'run_id': 'RUN-IGNORED'})
        self.assertEqual(workspace_cli.collect_runs(self.root), [])

    def test_owned_run_inherits_restricted_classification(self):
        self.put('research/private/research.json', {'research_id': 'RES-PRIVATE', 'sensitivity': 'restricted'})
        run = workspace_cli.create_run(self.root, None, '受限运行', owner_id='RES-PRIVATE')
        metadata = json.loads((run / 'run.json').read_text())
        self.assertEqual(metadata['sensitivity'], 'restricted')
        self.assertNotIn(metadata['run_id'], {owner['owner_id'] for owner in owners.public_list_owners(self.root)})

    def test_nested_parent_retraction_and_invalid_owner_are_visible(self):
        self.put('research/a/runs/base/run.json', {'run_id': 'RUN-BASE', 'review': {'status': 'retracted'}})
        child = self.put('data/catalog/card.memory.runtime/runs/child/run.json', {
            'run_id': 'RUN-CHILD', 'parent_run_ids': ['RUN-BASE'], 'owner_id': 'DATA-A'})
        results = {r['run_id']: r for r in workspace_cli.search_runs(self.root)}
        self.assertEqual(results['RUN-CHILD']['blocking_run_ids'], ['RUN-BASE'])
        child.write_text(json.dumps({'run_id': 'RUN-CHILD', 'owner_id': []}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'owner_id'):
            workspace_cli.collect_runs(self.root)
        self.assertTrue(EvidenceGraph(self.root).errors)


if __name__ == '__main__':
    unittest.main()
