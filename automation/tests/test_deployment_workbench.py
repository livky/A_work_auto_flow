"""合成业务链、升级恢复、发布排除和本机 HTTP 边界的集成测试。

数据在 TemporaryDirectory 中生成，不读取真实公司材料，不注册真实 PATH。
除了状态码，还检查旧业务字节、来源哈希、下游风险和失败后的保留状态。
"""
import http.client
import json
from pathlib import Path
import shutil
import sys
import os
import subprocess
import tempfile
import threading
import unittest
from contextlib import nullcontext
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'automation/scripts'))
import command_registration as registration
import deployment as deploy
import evidence
import evidence_observer as observer
import evidence_view
import local_test_data as samples
import portable
import retrieval
import workbench
import workspace_cli as cli
import upgrade_fixture


class DeploymentWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='研发 集成-')
        self.base = Path(self.temp.name).resolve()
        self.root = samples.build(self.base / '旧 工作区')

    def tearDown(self):
        self.temp.cleanup()

    def write(self, root, name, text):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        return target

    def new_source(self):
        source = self.base / 'GitHub 新版'
        source.mkdir()
        for name in ('setup.cmd', 'workbench.cmd', 'README.md', 'automation/scripts/updated.py',
                     'retrieval/config.json', 'AGENTS.md', 'context/NOW.md', '.gitignore'):
            self.write(source, name, 'NEW-' + name)
        self.write(source, 'runs/do-not-import/run.json', '{"private":true}')
        self.write(source, '.local/test-workspace/data/catalog/private.csv', 'never release')
        return source

    def test_fixture_covers_modules_and_never_marks_claims_accepted(self):
        marker = json.loads((self.root / 'synthetic-marker.json').read_text())
        self.assertTrue(all((self.root / n).is_dir() for n in marker['modules']))
        graph = evidence.EvidenceGraph(self.root)
        self.assertEqual(graph.errors, [])
        self.assertIn('EVD-SYNTHETIC-REPORT', graph.nodes)
        self.assertFalse(graph.status('CLM-SYNTHETIC', 'synthetic:only')['eligible'])
        self.assertEqual(cli.validate_workspace(self.root)[0], [])

    def test_source_change_reaches_report_and_experiment_completion(self):
        observer.monitor(self.root)
        path = self.root / 'data/catalog/synthetic-measurement.csv'
        path.write_text('sample,temperature_C,offset_ms\n2,30,9.9\n', encoding='utf-8')
        run = self.root / 'runs/synthetic-base/run.json'
        value = json.loads(run.read_text(encoding='utf-8'))
        value['status'] = 'succeeded'
        run.write_text(json.dumps(value), encoding='utf-8')
        observer.monitor(self.root)
        state = observer.load_state(self.root)
        self.assertTrue(any(e['kind'] == 'experiment-finished' for e in state['events']))
        report = evidence_view.data(self.root)['nodes']['EVD-SYNTHETIC-REPORT']
        self.assertEqual(report['state'], 'invalid')
        self.assertEqual(json.loads(run.read_text())['review']['status'], 'not-reviewed')

    def test_keyword_index_and_full_algorithm_context(self):
        summary = retrieval.index(self.root)
        self.assertGreater(summary['updated'], 10)
        result = retrieval.search(self.root, '温漂')
        self.assertTrue(result['results'])
        self.assertNotIn('archive/README.md', [Path(s['path']).relative_to(self.root).as_posix() for s in result['results']])
        self.assertEqual(retrieval.index(self.root)['updated'], 0)

    def test_generate_preview_idempotence_and_isolation(self):
        result = samples.generate(self.root, preview=True)
        self.assertFalse(Path(result['root']).exists())
        result = samples.generate(self.root)
        record = Path(result['root']) / 'runs/synthetic-base/run.json'
        record.write_text('local edited', encoding='utf-8')
        samples.generate(self.root)
        self.assertEqual(record.read_text(), 'local edited')
        self.assertEqual(len(evidence.EvidenceGraph(self.root).nodes), 6)
        self.assertFalse(any('.local' in p.parts for p in cli.iter_small_text_files(self.root)))

    def test_portable_omits_generated_data_and_upgrade_backups(self):
        samples.generate(self.root)
        self.write(self.root, '.local/upgrades/private.json', 'private')
        self.write(self.root, 'services/qdrant/runtime-stage-broken/a.txt', 'incomplete')
        files = list(portable.inventory(self.root))
        self.assertFalse(any('.local' in p.parts or 'runtime-stage-broken' in p.parts for p in files))
        self.assertIn(self.root / 'runs/synthetic-base/run.json', files)

    def test_upgrade_preserves_business_config_rules_and_runtime(self):
        source = self.new_source()
        protected = ['runs/synthetic-base/run.json', 'retrieval/config.json', 'AGENTS.md', 'context/NOW.md']
        before = {n: (self.root / n).read_bytes() for n in protected}
        self.write(self.root, 'services/qdrant/runtime/python.exe', 'old runtime')
        entries = deploy.plan(source, self.root)
        self.assertTrue(entries)
        self.assertFalse((self.root / 'automation').exists())
        backup = deploy.apply_upgrade(source, self.root, entries)
        self.assertTrue((backup / 'receipt.json').is_file())
        for name, content in before.items():
            self.assertEqual((self.root / name).read_bytes(), content)
        self.assertEqual((self.root / 'services/qdrant/runtime/python.exe').read_text(), 'old runtime')
        self.assertFalse((self.root / 'runs/do-not-import').exists())
        self.assertEqual(deploy.plan(source, self.root), [])

    def test_restore_checks_all_conflicts_before_changing_any_file(self):
        source = self.new_source()
        original = (self.root / 'README.md').read_bytes()
        backup = deploy.apply_upgrade(source, self.root, deploy.plan(source, self.root))
        self.write(self.root, 'automation/scripts/updated.py', 'user edit after upgrade')
        with self.assertRaisesRegex(ValueError, '安装后已修改'):
            deploy.rollback(backup)
        self.assertEqual((self.root / 'README.md').read_text(), 'NEW-README.md')
        shutil.copy2(source / 'automation/scripts/updated.py', self.root / 'automation/scripts/updated.py')
        deploy.rollback(backup, preview=True)
        self.assertEqual((self.root / 'README.md').read_text(), 'NEW-README.md')
        deploy.rollback(backup)
        self.assertEqual((self.root / 'README.md').read_bytes(), original)
        self.assertFalse((self.root / 'automation/scripts/updated.py').exists())

    def test_upgrade_rejects_nested_target_and_changed_source(self):
        with self.assertRaises(ValueError):
            deploy.plan(self.root, self.root / 'nested')
        source = self.new_source()
        entries = deploy.plan(source, self.root)
        self.write(source, 'README.md', 'changed while installing')
        with self.assertRaisesRegex(ValueError, '源文件发生变化'):
            deploy.apply_upgrade(source, self.root, entries)
        self.assertTrue((self.root / 'runs/synthetic-base/run.json').is_file())

    def test_corrupt_backup_blocks_restore(self):
        source = self.new_source()
        backup = deploy.apply_upgrade(source, self.root, deploy.plan(source, self.root))
        (backup / 'files/README.md').write_text('corrupted')
        with self.assertRaisesRegex(ValueError, '备份校验失败'):
            deploy.rollback(backup)

    def test_path_registration_is_idempotent_and_preserves_other_entries(self):
        folder = r'C:\Users\示例\AppData\Local\AI-RD-Workspace\bin'
        original = r'C:\Tools;%OTHER_HOME%\bin;;C:\Windows'
        one, added = registration.change_path(original, folder)
        self.assertTrue(added)
        two, added = registration.change_path(one, folder)
        self.assertFalse(added)
        self.assertEqual(one, two)
        result, found = registration.change_path(two, folder, remove=True)
        self.assertTrue(found)
        self.assertEqual(result, original)

    @unittest.skipUnless(os.name == 'nt', 'Windows user registry adapter')
    def test_registration_preview_repeat_and_uninstall_with_isolated_registry(self):
        import winreg
        import ctypes
        original = r'C:\Tools;;%USER_VAR%\bin'
        state = {'path': original}
        folder = self.base / '本机用户'
        self.write(self.root, 'workbench.cmd', '@echo off\n')
        def set_value(key, name, reserved, kind, value):
            state['path'] = value
        with patch.dict(os.environ, LOCALAPPDATA=str(folder)), \
             patch.object(winreg, 'CreateKey', side_effect=lambda *a: nullcontext(None)), \
             patch.object(winreg, 'QueryValueEx', side_effect=lambda *a: (state['path'], winreg.REG_EXPAND_SZ)), \
             patch.object(winreg, 'SetValueEx', side_effect=set_value), \
             patch.object(shutil, 'which', return_value=None), \
             patch.object(ctypes.windll.user32, 'SendMessageTimeoutW'):
            registration.register(self.root, preview=True)
            self.assertFalse(folder.exists())
            registration.register(self.root)
            first = state['path']
            registration.register(self.root)
            self.assertEqual(state['path'], first)
            state['path'] += ';C:\\UserAddedAfterInstall'
            registration.register(self.root, remove=True)
            self.assertEqual(state['path'], original + ';C:\\UserAddedAfterInstall')
            self.assertFalse((folder / 'AI-RD-Workspace/bin/rdwork.cmd').exists())

    def test_controller_start_stop_idempotence_and_errors_are_visible(self):
        control = workbench.Controller(self.root)
        control.interval = 0.02
        control.action('start-monitor')
        worker = control.thread
        control.action('start-monitor')
        self.assertIs(control.thread, worker)
        control.action('stop-monitor')
        control.close()
        self.assertFalse(control.thread.is_alive())
        with patch.object(observer, 'monitor', side_effect=ValueError('坏输入')):
            with self.assertRaises(ValueError):
                control.action('monitor')
        self.assertIn('坏输入', control.status()['error'])
        with self.assertRaises(ValueError):
            control.action('run arbitrary command')

    def test_http_action_origin_whitelist_and_existing_evidence_preview(self):
        control = workbench.Controller(self.root)
        server, url = evidence_view.create_server(self.root, controller=control)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        address = urlsplit(url)
        def request(method, route, body=None, origin=None):
            connection = http.client.HTTPConnection(address.hostname, address.port, timeout=10)
            headers = {'Content-Type': 'application/json'}
            if origin:
                headers['Origin'] = origin
            connection.request(method, address.path + route, body, headers)
            response = connection.getresponse()
            result = response.status, response.read()
            connection.close()
            return result
        try:
            self.assertEqual(request('GET', '')[0], 200)
            self.assertEqual(request('GET', 'evidence')[0], 200)
            self.assertEqual(request('GET', 'api/module?name=reports')[0], 200)
            self.assertEqual(request('GET', 'api/module?name=../../')[0], 400)
            self.assertEqual(request('POST', 'api/action', '{"action":"monitor"}')[0], 403)
            origin = f'http://{address.netloc}'
            self.assertEqual(request('POST', 'api/action', '{"action":"monitor"}', origin)[0], 200)
            self.assertEqual(request('POST', 'api/action', '{"action":"shell"}', origin)[0], 400)
            self.assertEqual(request('POST', 'api/action', '{"action":"monitor","path":"C:/"}', origin)[0], 400)
            self.assertEqual(request('PUT', 'api/action', '{}', origin)[0], 405)
            status, body = request('GET', 'api/source?id=CLM-SYNTHETIC&ref=0')
            self.assertEqual(status, 200)
            self.assertIn('temperature_C,offset_ms', json.loads(body)['text'])
        finally:
            control.close()
            server.shutdown()
            server.server_close()
            thread.join()

    @unittest.skipUnless(os.name == 'nt', 'Windows cmd/PowerShell integration')
    def test_windows_zip_upgrade_entry_and_rollback_preserve_data(self):
        protected = upgrade_fixture.populate(self.root)
        self.assertEqual(cli.validate_workspace(self.root)[0], [])
        # Build a small GitHub-like source tree and invoke the actual .cmd entry in PS 5.1.
        source = self.base / '源码 ZIP'
        source.mkdir()
        files = set(deploy.framework_files(ROOT)) | set(deploy.seed_files(ROOT))
        for name in files:
            dst = source / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, dst)
        keep = (self.root / 'runs/synthetic-base/run.json').read_bytes()
        env = dict(os.environ, CODEX_WORKSPACE_PYTHON=sys.executable)
        preview = subprocess.run(['cmd.exe', '/d', '/c', 'setup.cmd', '--target', str(self.root), '--profile', 'core', '--preview'],
                                 cwd=source, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        upgrade_fixture.assert_preserved(self.root, protected)
        result = subprocess.run(['cmd.exe', '/d', '/c', 'setup.cmd', '--target', str(self.root), '--profile', 'core'],
                                cwd=source, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / 'runs/synthetic-base/run.json').read_bytes(), keep)
        upgrade_fixture.assert_preserved(self.root, protected)
        # 二次升级不能改变业务/登记或产生新的框架替换计划。
        self.assertEqual(deploy.plan(source, self.root), [])
        repeated = subprocess.run(['cmd.exe', '/d', '/c', 'setup.cmd', '--target', str(self.root), '--profile', 'core'],
                                  cwd=source, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        upgrade_fixture.assert_preserved(self.root, protected)
        help_result = subprocess.run(['cmd.exe', '/d', '/c', 'workbench.cmd', '--help'], cwd=self.root, env=env,
                                     capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn('workbench', help_result.stdout)
        # Launch the copied Python application with Node absent from PATH. Read
        # the real homepage and every shipped asset, including the Worker, before
        # rollback. This exercises the new machine's paths rather than ROOT's UI.
        script = "import sys,json,shutil; from pathlib import Path; sys.path.insert(0,str(Path(sys.argv[1])/'automation/scripts')); import workbench; print(json.dumps({'node':shutil.which('node')}),flush=True); workbench.serve(Path(sys.argv[1]),open_browser=False)"
        child = subprocess.Popen([sys.executable, '-c', script, str(self.root)], cwd=self.root,
                                 env=dict(env, PATH=''), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            self.assertIsNone(json.loads(child.stdout.readline())['node'])
            address = urlsplit(json.loads(child.stdout.readline())['url'])
            manifest = json.loads((self.root / 'automation/ui/workbench-assets/asset-manifest.json').read_text())
            for route in ['', *manifest['files']]:
                connection = http.client.HTTPConnection(address.hostname, address.port, timeout=10)
                connection.request('GET', address.path + ('' if route == 'index.html' else route))
                response = connection.getresponse()
                body = response.read()
                connection.close()
                # The public asset route serves JS/CSS/Worker; ancillary license
                # files are distributed for inspection but not browser routes.
                if route == '' or route == 'index.html' or route.startswith('assets/'):
                    self.assertEqual(response.status, 200, route)
                    self.assertTrue(body)
        finally:
            child.terminate()
            child.communicate(timeout=10)
        receipt = next((self.root / '.local/upgrades').glob('*/receipt.json'))
        result = subprocess.run(['cmd.exe', '/d', '/c', 'setup.cmd', '--rollback', str(receipt.parent)],
                                cwd=source, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / 'runs/synthetic-base/run.json').read_bytes(), keep)

        upgrade_fixture.assert_preserved(self.root, protected)

    def test_expanded_workspace_still_rejects_missing_tools_and_bad_business_metadata(self):
        protected = upgrade_fixture.populate(self.root)
        self.assertEqual(cli.validate_workspace(self.root)[0], [])
        registry = self.root / 'tools/registry.json'
        value = json.loads(registry.read_text(encoding='utf-8'))
        value['tools'].append({'tool_id': 'TOOL-MISSING-SYNTHETIC', 'entrypoint': 'tools/packages/nonexistent'})
        registry.write_text(json.dumps(value), encoding='utf-8')
        bad = self.write(self.root, 'knowledge/用户扩展/deeper/invalid.json', '{not JSON')
        errors, _ = cli.validate_workspace(self.root)
        self.assertTrue(any('TOOL-MISSING-SYNTHETIC' in e for e in errors))
        self.assertTrue(any('invalid.json' in e for e in errors))
        self.assertFalse(any('broken.json' in e for e in errors))
        # 负例也必须保留磁盘输入，不允许校验器通过删除坏登记/材料达到成功。
        self.assertTrue(bad.is_file())
        self.assertIn('TOOL-MISSING-SYNTHETIC', registry.read_text())

    def test_environment_missing_or_wrong_versions_is_not_reused(self):
        self.assertFalse(deploy.environment_ready(self.root))
        self.write(self.root, 'services/qdrant/runtime/python.exe', 'fake')
        with patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            self.assertFalse(deploy.environment_ready(self.root))

    def test_module_inventory_is_limited_and_rejects_arbitrary_paths(self):
        control = workbench.Controller(self.root)
        try:
            for i in range(60):
                self.write(self.root, f'knowledge/patterns/demo-{i}.md', 'synthetic')
            self.assertEqual(len(control.module('knowledge')['files']), 40)
            with self.assertRaises(ValueError):
                control.module('../')
        finally:
            control.close()


if __name__ == '__main__':
    unittest.main()
