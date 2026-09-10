"""W03 合成对象契约检查；不代替历史生成、迁移或业务结论验收。"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from memory import owners, policy
from memory.errors import MemoryError


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content, encoding='utf-8')
        return path

    def test_eight_types_read_only_and_nested_identity(self):
        cards = [('research/中文 空格/深层/research.json', 'research_id', 'RES-1'),
                 ('runs/x/run.json', 'run_id', 'RUN-1'), ('projects/x/project.json', 'project_id', 'PRJ-1'),
                 ('core-algorithms/x/module.json', 'module_id', 'MOD-1'),
                 ('knowledge/x.evidence.json', 'evidence_id', 'EVD-1'),
                 ('reports/manifests/x.json', 'report_id', 'REP-1'),
                 ('data/catalog/x.dataset.json', 'dataset_id', 'DATA-1')]
        for path, key, oid in cards:
            self.put(path, {key: oid, 'title': '同名标题', 'project_id': 'PRJ-1'})
        self.put('tools/local tool/main.py', '# synthetic')
        self.put('tools/registry.json', {'tools': [{'tool_id': 'TOOL-1', 'entrypoint': 'tools/local tool'}]})
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        found = owners.list_owners(self.root)
        self.assertEqual(set(owners.ROOT_TYPES.values()), {v['owner_type'] for v in found})
        self.assertEqual(len(found), 8)
        self.assertEqual(owners.resolve_owner(self.root, 'RES-1')['memory_home'], 'research/中文 空格/深层/memory')
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertFalse(any(p.name == 'memory' for p in self.root.rglob('*')))
        with self.assertRaises(MemoryError) as ctx:
            owners.resolve_owner(self.root, 'PRJ-DOES-NOT-EXIST')
        self.assertEqual(ctx.exception.code, 'NOT_FOUND')

    def test_adopt_document_stable_id_alias_and_hash_guard(self):
        path = self.put('knowledge/中文 空格/经验.md', '# 经验证据\n原件不变')
        original = path.read_bytes()
        view = owners.list_owners(self.root)[0]
        adopted = owners.adopt_owner(self.root, view['native_ref'], view['fingerprint'])
        again = owners.adopt_owner(self.root, view['native_ref'], view['fingerprint'])
        self.assertTrue(adopted['owner_id'].startswith('OBJ-'))
        self.assertEqual(again['owner_id'], adopted['owner_id'])
        self.assertEqual(owners.resolve_owner(self.root, view['owner_id'])['owner_id'], adopted['owner_id'])
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(list(self.root.rglob('owner.json'))), 1)
        with self.assertRaises(MemoryError) as ctx:
            owners.adopt_owner(self.root, view['native_ref'], '0' * 64)
        self.assertEqual(ctx.exception.code, 'STALE_BASIS')

    def test_ensure_owner_preserves_run_and_claims(self):
        path = self.put('runs/base/run.json', {'run_id': 'RUN-1', 'status': 'succeeded',
                        'review': {'state': 'accepted'}, 'claims': [{'claim_id': 'CLM-1'}]})
        original = path.read_bytes()
        owner = owners.resolve_owner(self.root, 'RUN-1')
        result = owners.ensure_owner(self.root, owner, {'kind': 'ai', 'id': 'test'})
        self.assertTrue(result['persisted'])
        self.put('runs/base/memory/commits/synthetic/records/run.json', 'broken memory transaction is outside native scan')
        view = owners.run_adapter(self.root, 'RUN-1')
        self.assertEqual(view['event_id'], 'RUN-1')
        self.assertEqual(view['claims'][0]['claim_id'], 'CLM-1')
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(owners.ensure_owner(self.root, owner)['owner_id'], 'RUN-1')

    def test_bad_business_json_and_missing_tool_not_ignored(self):
        bad = self.put('research/层级/普通业务/bad.json', '{')
        self.put('research/.local/bad.json', '{')
        with self.assertRaises(MemoryError) as ctx:
            owners.list_owners(self.root)
        self.assertIn('普通业务', str(ctx.exception.details))
        bad.write_text('{}', encoding='utf-8')
        self.assertEqual(owners.list_owners(self.root), [])
        self.put('tools/registry.json', {'tools': [{'tool_id': 'TOOL-1', 'entrypoint': 'tools/missing'}]})
        with self.assertRaises(MemoryError) as ctx:
            owners.list_owners(self.root)
        self.assertEqual(ctx.exception.details['path'], 'tools/missing')

    def test_duplicate_ids_and_double_claim_rejected(self):
        self.put('runs/one/run.json', {'run_id': 'RUN-1'})
        other = self.put('runs/two/run.json', {'run_id': 'run-1'})
        with self.assertRaises(MemoryError):
            owners.list_owners(self.root)
        other.write_text('{"run_id":"RUN-2"}', encoding='utf-8')
        owner = owners.ensure_owner(self.root, owners.resolve_owner(self.root, 'RUN-1'))
        self.put('knowledge/false.md.memory/owner.json', json.loads((self.root / owner['memory_home'] / 'owner.json').read_text()))
        with self.assertRaises(MemoryError):
            owners.list_owners(self.root)

    def test_path_windows_boundaries_and_casing(self):
        for path in ['../outside', '/absolute', 'C:\\outside', 'runs/CON/run.json',
                     'runs/a./x', 'runs/a:stream', 'runs//x', 'runs/../x']:
            with self.subTest(path=path), self.assertRaises(MemoryError):
                owners.safe_path(self.root, path)
        self.put('Runs/a.txt', 'text')
        with self.assertRaises(MemoryError):
            owners.safe_path(self.root, 'runs/a.txt')

    def test_manual_move_is_not_silently_reidentified(self):
        path = self.put('knowledge/old.md', '# source')
        view = owners.list_owners(self.root)[0]
        owners.adopt_owner(self.root, view['native_ref'], view['fingerprint'])
        path.rename(path.with_name('new.md'))
        with self.assertRaises(MemoryError) as ctx:
            owners.list_owners(self.root)
        self.assertEqual(ctx.exception.code, 'NOT_FOUND')

    def test_policy_priority_explicit_false_and_type_mode(self):
        owner = {'owner_type': 'research', 'workspace_defaults': {'auto_summary': True},
                 'type_defaults': {'checkpoint': False}, 'policy': {'mode': 'accumulate', 'overrides': {'auto_summary': False}}}
        result = policy.resolve(owner, {'checkpoint': True})
        self.assertFalse(result['values']['auto_summary'])
        self.assertTrue(result['values']['checkpoint'])
        self.assertEqual(result['sources']['auto_summary'], 'owner')
        self.assertEqual(result['sources']['checkpoint'], 'request')
        self.assertEqual(policy.resolve({'owner_type': 'research'})['values']['mode'], 'explore')
        research_policy = policy.resolve({'owner_type': 'research'})
        self.assertEqual(research_policy['values']['retain'], ['L0', 'L1', 'L2', 'L3', 'L4'])
        self.assertEqual(research_policy['values']['granularity'], 'fine')
        self.assertTrue(research_policy['values']['auto_summary'])
        self.assertEqual(research_policy['sources']['retain'], 'type')
        # Explicit scope always overrides defaults; the policy advises the AI,
        # never grants permission to run experiments or accept conclusions.
        overridden = policy.resolve({'owner_type': 'research'}, {'retain': ['L1'], 'auto_summary': False})
        self.assertEqual(overridden['values']['retain'], ['L1'])
        self.assertFalse(overridden['values']['auto_summary'])
        for kind in ['run', 'project']:
            self.assertEqual(policy.resolve({'owner_type': kind})['values']['mode'], 'basic')
        with self.assertRaises(MemoryError):
            policy.resolve(owner, {'auto_deepen': 'false'})
        for override in ({'retain': True}, {'granularity': 'key_events'}, {'retain': [False]}, []):
            with self.subTest(override=override), self.assertRaises(MemoryError):
                policy.resolve(owner, override)
        defaults = policy.resolve({'owner_type': 'run'})['values']
        self.assertEqual(defaults['retain'], [])
        self.assertEqual(defaults['granularity'], 'normal')
        defaults['retain'].append('不应污染下次解析')
        self.assertEqual(policy.resolve({'owner_type': 'run'})['values']['retain'], [])

    def test_saved_frozen_policy_resolves_retain_and_false_via_inspect(self):
        from copy import deepcopy
        from memory_fixture import materialize
        from memory.service import MemoryService
        from upgrade_fixture import policy_request
        fixture = materialize(self.root / 'policy-fixture', isolation_root=self.root)
        draft = deepcopy(next(item for item in fixture.drafts if item['kind'] == 'policy'))
        draft.pop('record_id')
        draft.pop('actor', None)
        owner_id = draft['owner_id']
        request = policy_request(owner_id)
        request['operations'][0]['draft'] = draft
        service = MemoryService(fixture.root)
        receipt = service.commit(request)
        self.assertEqual(receipt['save_status'], 'committed')
        inspected = service.inspect(owner_id)
        actual = inspected['policy']
        self.assertEqual(actual['values']['retain'], ['失败边界'])
        self.assertFalse(actual['values']['auto_summary'])
        self.assertEqual(actual['sources']['retain'], 'owner')
        self.assertEqual(actual['sources']['auto_summary'], 'owner')
        self.assertEqual(actual['values']['granularity'], 'fine')
        self.assertEqual(actual['sources']['granularity'], 'type')
        saved = next(iter(inspected['records'].values()))
        self.assertIn('missing_refs', saved['payload'])
        self.assertNotIn('missing_refs', actual['values'])

    def test_frozen_fixture_all_declared_native_objects_are_readable(self):
        from memory_fixture import materialize, snapshot
        fixture = materialize(self.root / 'fixture', isolation_root=self.root)
        before = snapshot(fixture.root)
        found = owners.list_owners(fixture.root)
        by_id = {v['owner_id']: v for v in found}
        for oid, seed in fixture.owners.items():
            if seed['owner_type'] == 'knowledge':
                self.assertTrue(any(v['native_ref']['path'] == seed['path'] for v in found))
            else:
                self.assertIn(oid, by_id)
                self.assertEqual(by_id[oid]['owner_type'], seed['owner_type'])
        self.assertEqual(before, snapshot(fixture.root))

    def test_adopt_and_policy_commit_preserve_verified_legacy_evidence(self):
        import uuid
        from test_memory_contracts import draft as memory_draft
        from memory_fixture import build_verified_legacy
        from memory.service import MemoryService
        from upgrade_fixture import policy_request
        import evidence
        import workspace_cli
        from workbench_app import projection
        receipt = build_verified_legacy(self.root / 'verified', isolation_root=self.root)
        root = Path(receipt['root'])
        before = evidence.EvidenceGraph(root)
        status = before.status('CLM-SYNTHETIC', 'synthetic:only')
        self.assertTrue(status['eligible'])
        native = {node['path']: node['path'].read_bytes() for node in before.nodes.values()}
        search_before = workspace_cli.search_runs(root, '合成')
        projection_before = {node['id']: node for node in projection.collect(root)['nodes']}
        def review_commands():
            # Use the same public functions as review-run/review-claim in
            # preview mode, preserving the original accepted review history.
            values = [workspace_cli.review_run(root, 'RUN-SYNTHETIC', 'accepted', 'synthetic-compatibility',
                        'SYNTHETIC ONLY compatibility', evidence='synthetic fixture evidence', scope='synthetic:only', dry_run=True),
                      evidence.review_claim(root, 'CLM-SYNTHETIC', 'accepted', 'synthetic-compatibility',
                        'SYNTHETIC ONLY compatibility', evidence='synthetic fixture evidence', scope='synthetic:only', dry_run=True)]
            for value in values:
                value['review'].pop('date')  # Invocation time is intentionally not an identity field.
            return values
        reviews_before = review_commands()
        for oid in ('RUN-SYNTHETIC', 'RES-SYNTHETIC'):
            owner = owners.resolve_owner(root, oid)
            owners.adopt_owner(root, owner['native_ref'], owner['fingerprint'])
            saved = MemoryService(root).commit(policy_request(oid))
            self.assertEqual(saved['save_status'], 'committed')
            self.assertEqual(saved['index_status'], 'pending')
            goal, checkpoint = memory_draft('goal'), memory_draft('checkpoint')
            goal['owner_id'] = checkpoint['owner_id'] = oid
            checkpoint['payload']['goal_ref'] = {'client_key': 'goal', 'relation': 'references', 'locator': 'goal'}
            prepared = {'schema_version': 1, 'request_id': str(uuid.uuid4()), 'owner_id': oid,
                'expected_head': saved['commit_id'], 'actor': {'kind': 'workflow', 'id': 'synthetic-compatibility'},
                'operations': [{'op': 'put_record', 'client_key': 'goal', 'draft': goal},
                               {'op': 'save_checkpoint', 'client_key': 'checkpoint', 'draft': checkpoint}]}
            written = MemoryService(root).commit(prepared)
            self.assertEqual(written['save_status'], 'committed')
            self.assertEqual({row['kind'] for row in MemoryService(root).inspect(oid)['records'].values()},
                             {'policy', 'goal', 'checkpoint'})
        after = evidence.EvidenceGraph(root)
        self.assertEqual(status, after.status('CLM-SYNTHETIC', 'synthetic:only'))
        self.assertEqual(set(before.nodes), set(after.nodes))
        self.assertEqual(native, {path: path.read_bytes() for path in native})
        self.assertEqual(search_before, workspace_cli.search_runs(root, '合成'))
        self.assertEqual(reviews_before, review_commands())
        projected = projection.collect(root)['nodes']
        for oid in ('RUN-SYNTHETIC', 'CLM-SYNTHETIC', 'EVD-SYNTHETIC-KNOWLEDGE'):
            matches = [node for node in projected if node['id'] == oid]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0], projection_before[oid])
        # 对旧参数的真实修改仍使 owner_fingerprint 失配；记忆不能屏蔽失效。
        run = root / 'runs/synthetic-base/run.json'
        raw = json.loads(run.read_text(encoding='utf-8'))
        raw['parameters'] = {'synthetic_changed_parameter': 1}
        run.write_text(json.dumps(raw, ensure_ascii=False), encoding='utf-8')
        self.assertFalse(evidence.EvidenceGraph(root).status('CLM-SYNTHETIC', 'synthetic:only')['eligible'])

    def test_trusted_extension_validate_resolve_commit_and_inspect(self):
        from memory.service import MemoryService
        from memory import index, search
        from test_memory_index import draft, request
        from upgrade_fixture import policy_request
        self.put('simulations/中文 空格/model.json', {'simulation_id': 'SIM-SYNTHETIC', 'title': 'Synthetic simulation'})
        view = {'schema_version': 1, 'owner_id': 'SIM-SYNTHETIC', 'owner_type': 'simulation',
                'native_ref': {'path': 'simulations/中文 空格/model.json', 'id_field': 'simulation_id', 'id_value': 'SIM-SYNTHETIC'},
                'memory_home': 'simulations/中文 空格/model.json.memory', 'adapter_version': 1}
        class Adapter:
            def list_owners(self, root):
                return [dict(view)]
        spec = {'owner_type': 'simulation', 'schema_version': 1, 'adapter_version': 1,
                'schema': {'type': 'object', 'required': ['owner_type'], 'properties': {'owner_type': {'const': 'simulation'}}}}
        with patch.dict(owners._EXTENSIONS, {}, clear=True):
            before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
            # A native file is not permission to invent an unregistered owner.
            with self.assertRaises(MemoryError) as unknown:
                MemoryService(self.root).commit(policy_request('SIM-SYNTHETIC'))
            self.assertEqual(unknown.exception.code, 'NOT_FOUND')
            self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
            with self.assertRaises(MemoryError):
                owners.register_type({**spec, 'schema': {'unsupported': True}}, Adapter())
            with self.assertRaises(MemoryError):
                owners.register_type({**spec, 'schema_version': 2}, Adapter())
            owners.register_type(spec, Adapter())
            self.assertEqual(owners.resolve_owner(self.root, 'SIM-SYNTHETIC')['owner_type'], 'simulation')
            service = MemoryService(self.root)
            receipt = service.commit(policy_request('SIM-SYNTHETIC'))
            self.assertEqual(receipt['save_status'], 'committed')
            inspect = service.inspect('SIM-SYNTHETIC')
            self.assertEqual(inspect['head']['commit_id'], receipt['commit_id'])
            self.assertEqual(inspect['owner']['owner_type'], 'simulation')
            self.assertTrue(inspect['owner']['persisted'])
            # The extension must pass the same real SQLite indexing/search path
            # as built-in owners; an adapter-only lookup is not the C06 loop.
            value = draft('SIM-SYNTHETIC', title='SYNTHETIC ONLY 扩展仿真入口', body='仿真独立检索记号')
            saved = service.commit(request(value, head=receipt['commit_id']))
            index.sync_owner(self.root, 'SIM-SYNTHETIC', vector='off')
            result = search.search(self.root, {'query': '仿真独立检索记号', 'vector': 'off',
                'purpose': 'exploration', 'owner_id': 'SIM-SYNTHETIC'}, record=False)
            self.assertIn(saved['record_results'][0]['record_id'], [r['canonical_id'] for r in result['candidates']])
            # 已登记 schema 仍约束后续发现，不能只在 register 时形式检查。
            view['owner_type'] = 'unregistered'
            with self.assertRaises(MemoryError):
                owners.list_owners(self.root)


if __name__ == '__main__':
    unittest.main()
