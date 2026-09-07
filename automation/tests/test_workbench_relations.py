"""材料关系的边界验证：真实元数据映射、读写隔离、版本与 HTTP 契约。"""
import hashlib
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'automation/scripts'))
import local_test_data
import evidence_view
import workbench
import deployment
from workbench_app import projection, analysis, contracts, web
from workbench_app.service import Service
from workbench_app.storage import Store
from workbench_app.jobs import Jobs


class RelationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.root = local_test_data.build(Path(self.tmp.name) / '关系 测试')
        self.service = Service(self.root, enable_jobs=False)

    def tearDown(self):
        self.service.close()
        self.tmp.cleanup()

    def fingerprints(self):
        return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file() and '.local' not in p.relative_to(self.root).parts}

    def test_projection_contract_direction_and_read_only(self):
        before = self.fingerprints()
        self.service.rebuild()
        graph = self.service.graph
        self.assertEqual(contracts.check_graph(graph), [])
        self.assertEqual(before, self.fingerprints())
        nodes = {n['id']: n for n in graph['nodes']}
        edge = next(e for e in graph['edges'] if e['source'] == 'CLM-SYNTHETIC' and e['type'] == 'input')
        self.assertTrue(nodes[edge['target']]['path'].endswith('.csv'))
        self.assertEqual(edge['original_source'], 'CLM-SYNTHETIC')
        self.assertFalse(edge['candidate'])
        self.assertIn('DATA-SYNTHETIC', nodes)

    def test_development_caches_are_not_business_control_files(self):
        import workspace_cli as cli
        for relative in ('automation/frontend/node_modules/vendor/broken.json', '.local/workbench/server-lease.json'):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('not JSON', encoding='utf-8')
        self.assertEqual(cli.validate_workspace(self.root)[0], [])
        path = self.root / 'knowledge/broken.json'
        path.write_text('not JSON', encoding='utf-8')
        self.assertTrue(any('knowledge' in error for error in cli.validate_workspace(self.root)[0]))

    def test_server_lease_prevents_job_history_clobber(self):
        first = Jobs(Store(self.root))
        try:
            with self.assertRaisesRegex(ValueError, '已有新工作台'):
                Jobs(Store(self.root))
        finally:
            first.close()
        second = Jobs(Store(self.root))
        second.close()

    def test_exclusion_and_summary_are_same_scope(self):
        self.service.rebuild()
        view = self.service.view({'center': 'CLM-SYNTHETIC', 'hops': 2, 'excluded': ['RUN-SYNTHETIC']})
        self.assertNotIn('RUN-SYNTHETIC', [n['id'] for n in view['nodes']])
        self.assertFalse(any('RUN-SYNTHETIC' in (e['source'], e['target']) for e in view['edges']))
        exported = analysis.export_summary(view, '检查温漂')
        self.assertEqual(exported['graph'], view)
        self.assertIn('排除', exported['markdown'])

    def test_stale_preview_refuses_then_rebuild_changes(self):
        self.service.rebuild()
        node = next(n for n in self.service.graph['nodes'] if n['path'].endswith('synthetic-measurement.csv'))
        self.assertIn('temperature_C', self.service.preview(node['id'], node['fingerprint'])['text'])
        path = self.root / node['path']
        path.write_text('sample,temperature_C,offset_ms\n9,99,99\n', encoding='utf-8')
        self.assertTrue(self.service.freshness()['stale'])
        with self.assertRaises(ValueError):
            self.service.preview(node['id'], node['fingerprint'])
        self.service.rebuild()
        self.assertNotEqual(node['fingerprint'], next(n['fingerprint'] for n in self.service.graph['nodes'] if n['id'] == node['id']))

    def test_candidate_history_dry_run_and_no_promotion(self):
        self.service.rebuild()
        graph = self.service.graph
        node = next(n for n in graph['nodes'] if n['id'] == 'CLM-SYNTHETIC')
        proposal = {'kind': 'relation', 'title': '检查共同温度来源', 'explanation': '待用真实材料核对', 'actor': 'test',
                    'refs': [{'id': node['id'], 'fingerprint': node['fingerprint'], 'locator': 'claim'}]}
        before = self.fingerprints()
        self.service.save_candidate(proposal, dry_run=True)
        self.assertEqual(self.service.candidates(), [])
        created = self.service.save_candidate(proposal)
        self.service.resolve_candidate(created['id'], 'handled', 'test', '已另行记录处理过程')
        stored = self.service.candidates()[0]
        self.assertEqual(stored['history'][0]['from'], 'pending')
        self.assertEqual(stored['status'], 'handled')
        self.assertEqual(before, self.fingerprints())

    def test_keyword_pairs_are_candidates_not_dependencies(self):
        self.service.rebuild()
        graph = self.service.graph
        a, b = graph['nodes'][:2]
        a['keywords'] = ['温漂']; b['keywords'] = ['温漂']
        result = self.service.analyze('keywords', [a['id']])
        self.assertTrue(result['edges'])
        self.assertTrue(all(e['candidate'] for e in result['edges']))
        self.assertNotIn('keywords', {e['type'] for e in graph['edges']})
        self.assertEqual(self.service.analyze('keywords', [a['id']], [b['id']])['edges'], [])

    def test_view_path_and_source_boundaries(self):
        self.service.rebuild()
        with self.assertRaises(ValueError): Store(self.root).write('../escape', {})
        with self.assertRaises(ValueError): projection.allowed(self.root, '.local/private.txt')
        with self.assertRaises(ValueError): self.service.preview('../../secret', '')
        with self.assertRaises(ValueError): self.service.view({'shell': 'cmd'})
        with self.assertRaises(ValueError): self.service.analyze('arbitrary', [])

    def test_jobs_failure_cancel_and_restart(self):
        store = Store(self.root)
        store.write('analysis', {'previous': 'keep'})
        jobs = Jobs(store)
        def operation(progress):
            for i in range(100):
                time.sleep(.005); progress(i, 100)
            return {'ok': True}
        job = jobs.submit('test', operation)
        jobs.cancel(job['id']); jobs.close()
        self.assertEqual(jobs.list()[0]['status'], 'cancelled')
        self.assertEqual(store.read('analysis'), {'previous': 'keep'})
        store.write('jobs', {'old': {'id': 'old', 'status': 'running'}})
        jobs = Jobs(store)
        self.assertEqual(jobs.list()[0]['status'], 'interrupted'); jobs.close()

    def test_versioned_http_and_static_manifest(self):
        control = workbench.Controller(self.root)
        server, url = evidence_view.create_server(self.root, controller=control)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        parts = urlsplit(url)
        def request(route, method='GET', value=None, origin=True):
            connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=10)
            headers = {'Content-Type': 'application/json'}
            if origin: headers['Origin'] = f'http://{parts.netloc}'
            connection.request(method, parts.path + route, json.dumps(value) if value is not None else None, headers)
            response = connection.getresponse(); data = response.read(); status = response.status; connection.close()
            return status, data
        try:
            self.assertEqual(request('')[0], 200)
            status, raw = request('api/v1/capabilities')
            self.assertEqual(json.loads(raw)['api_version'], 1)
            self.assertEqual(request('api/v1/jobs', 'POST', {'kind': 'refresh'}, False)[0], 403)
            self.assertEqual(request('api/v1/jobs', 'POST', {'kind': 'shell'})[0], 400)
            self.assertEqual(request('api/v1/jobs', 'POST', {'kind': 'refresh'})[0], 202)
            for _ in range(200):
                if control.app.jobs.list()[0]['status'] not in ('queued', 'running'): break
                time.sleep(.01)
            status, raw = request('api/v1/graph')
            self.assertEqual(status, 200, raw)
            self.assertEqual(contracts.check_graph(json.loads(raw)), [])
            asset = next(n for n in web.asset_manifest()['files'] if n.endswith('.js'))
            self.assertEqual(request(asset)[0], 200)
            self.assertNotEqual(request('assets/../../AGENTS.md')[0], 200)
        finally:
            control.close(); server.shutdown(); server.server_close()

    def test_release_resources_in_upgrade_manifest(self):
        files = deployment.framework_files(ROOT)
        self.assertIn('automation/frontend/package-lock.json', files)
        self.assertTrue(any(p.endswith('.js') and 'workbench-assets' in p for p in files))
        self.assertFalse(any('node_modules' in p for p in files))

    def test_authorization_change_invalidates_cached_projection(self):
        self.service.rebuild()
        registry = self.root / 'retrieval/sources.json'
        registry.write_text('{"sources": [], "note": "读取范围修订"}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '读取范围'):
            self.service.view()

    def test_stale_ai_candidate_is_preserved_and_marked(self):
        self.service.rebuild()
        node = next(n for n in self.service.graph['nodes'] if n['id'] == 'CLM-SYNTHETIC')
        self.service.save_candidate({'kind': 'cluster-name', 'title': 'AI 主题命名', 'explanation': '基于旧版片段',
            'actor': 'AI session', 'refs': [{'id': node['id'], 'fingerprint': '0' * 64, 'locator': 'statement'}]})
        self.assertTrue(self.service.candidates()[0]['stale'])
        self.assertEqual(self.service.candidates()[0]['status'], 'pending')

    @unittest.skipUnless((ROOT / 'services/qdrant/models/multilingual-minilm/model_optimized.onnx').exists(), '缺少本地模型')
    def test_real_semantic_read_only_existing_index(self):
        import retrieval as r
        import socket
        from unittest.mock import patch
        cfg = r.config(self.root)
        cfg['embedding']['path'] = str(ROOT / 'services/qdrant/models/multilingual-minilm')
        cfg['embedding']['manifest'] = str(ROOT / 'services/qdrant/model-manifest.json')
        cfg['vector_store'] = {'provider': 'qdrant-local', 'path': 'services/qdrant/storage'}
        (self.root / 'retrieval/config.json').write_text(json.dumps(cfg), encoding='utf-8')
        with patch.object(socket.socket, 'connect', side_effect=RuntimeError('集成测试禁止联网')):
            r.index(self.root)
            self.service.rebuild()
            node = next(n for n in self.service.graph['nodes'] if n['path'].endswith('synthetic-drift/README.md'))
            before = self.fingerprints()
            result = self.service.analyze('semantic', [node['id']])
            self.assertTrue(result['edges'])
            self.assertTrue(all(edge['candidate'] and edge['model_id'].startswith('workspace_') for edge in result['edges']))
            self.assertIn('sampled_indices', result['coverage']['seeds'][0])
            # Qdrant 本机锁文件/元数据可能被客户库维护；业务源不能改变。
            after = self.fingerprints()
            self.assertEqual({k: v for k, v in before.items() if not k.startswith(('services/', 'retrieval/generated/'))},
                             {k: v for k, v in after.items() if not k.startswith(('services/', 'retrieval/generated/'))})


if __name__ == '__main__':
    unittest.main()
