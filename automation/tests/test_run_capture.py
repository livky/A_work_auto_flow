"""Exercise real child execution and the L0 reader, including rejected histories."""
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import unittest
import test_memory_research as fixture
import evidence
import run_capture
from memory.api import dispatch
from memory import owners
from manifest_discovery import manifests
import retrieval
import workspace_cli


class RunCaptureTests(unittest.TestCase):
    setUp = fixture.ResearchTests.setUp
    put = fixture.ResearchTests.put

    def setup_run(self, script='print("hello")'):
        self.put('runs/attempt/run.json', {'run_id': 'RUN-R', 'owner_id': 'RES-R',
            'status': 'planned', 'claims': [], 'inputs': [], 'artifacts': []})
        self.put('scripts/实验 程序.py', script)
        self.request = {'script': 'scripts/实验 程序.py', 'timeout_seconds': 10}
        self.card = self.root / 'runs/attempt/run.json'

    def test_c01_execute_auto_register_and_l0_read_without_source(self):
        self.setup_run('from pathlib import Path\nimport sys\nPath("结果.txt").write_text(Path(sys.argv[1]).read_text()+"!", encoding="utf-8")\nprint("done")')
        self.put('data/输入.txt', 'synthetic')
        self.request.update(inputs=['data/输入.txt'], args=['{input0}'])
        before = self.card.read_bytes()
        preview = run_capture.execute(self.root, 'RUN-R', self.request, True)
        self.assertEqual(preview['canonical_writes'], 0)
        self.assertEqual(before, self.card.read_bytes())
        self.assertFalse((self.card.parent / '.run-captures').exists())
        result = run_capture.execute(self.root, 'RUN-R', self.request)
        self.assertEqual(result['execution_status'], 'succeeded')
        listing = dispatch(self.service, 'raw-materials', {'owner_id': 'RES-R'})
        row = next(x for x in listing['items'] if x['path'].endswith('结果.txt'))
        content = dispatch(self.service, 'raw-material', {'owner_id': 'RES-R', 'material_id': row['material_id']})
        self.assertEqual(content['text'], 'synthetic!')
        self.assertFalse(self.service.inspect('RUN-R')['records'])
        second = run_capture.execute(self.root, 'RUN-R', self.request)
        self.assertNotEqual(result['output_dir'], second['output_dir'])
        self.assertTrue((self.root / row['path']).is_file())

    def test_c02_failed_and_timeout_preserve_logs_and_partial_output(self):
        self.setup_run('from pathlib import Path\nimport sys\nPath("partial.txt").write_text("partial")\nprint("bad",file=sys.stderr)\nsys.exit(7)')
        result = run_capture.execute(self.root, 'RUN-R', self.request)
        self.assertEqual(result['exit_code'], 7)
        self.assertEqual(result['execution_status'], 'failed')
        self.assertTrue(any(x['path'].endswith('partial.txt') for x in evidence.read(self.card)['artifacts']))
        self.put('scripts/timeout.py', 'import time\ntime.sleep(10)')
        timeout = run_capture.execute(self.root, 'RUN-R', {'script':'scripts/timeout.py', 'timeout_seconds': 0.1})
        self.assertEqual(timeout['execution_status'], 'failed')
        self.assertIn('TimeoutExpired', str(timeout['errors']))

    def test_c03_register_idempotent_and_rollback_conflict(self):
        self.setup_run()
        self.put('data/original.txt', 'before')
        before_bytes = self.card.read_bytes()
        before = evidence.read(self.card)
        result = run_capture.register(self.root, 'RUN-R', ['data/original.txt'])
        self.assertEqual(run_capture.register(self.root, 'RUN-R', ['data/original.txt'])['status'], 'unchanged')
        self.assertEqual(run_capture.rollback(self.root, result['receipt'], True)['status'], 'preview')
        after = evidence.read(self.card)
        self.put('runs/attempt/run.json', {**after, 'title': 'new change'})
        with self.assertRaisesRegex(ValueError, '新修改'):
            run_capture.rollback(self.root, result['receipt'])
        self.put('runs/attempt/run.json', after)
        run_capture.rollback(self.root, result['receipt'])
        self.assertEqual(evidence.read(self.card), before)
        self.assertEqual(self.card.read_bytes(), before_bytes)
        self.assertEqual((self.root / 'data/original.txt').read_text(), 'before')

    def test_c04_changed_version_revoked_source_and_invalid_request(self):
        self.setup_run()
        self.put('data/original.txt', 'first')
        run_capture.register(self.root, 'RUN-R', ['data/original.txt'])
        self.put('data/original.txt', 'second')
        before = self.card.read_bytes()
        with self.assertRaisesRegex(ValueError, '版本变化'):
            run_capture.register(self.root, 'RUN-R', ['data/original.txt'])
        self.assertEqual(before, self.card.read_bytes())
        self.put('retrieval/sources.json', {'sources':[{'path':'scripts/实验 程序.py','enabled':False}]})
        with self.assertRaisesRegex(ValueError, '禁用'):
            run_capture.execute(self.root, 'RUN-R', self.request)
        for request in ({}, {'script': 'x', 'args':'bad'}, {'script':'x','timeout_seconds':True}):
            with self.assertRaises(ValueError):
                run_capture.execute(self.root, 'RUN-R', request)

    def test_c05_input_mutation_and_concurrent_card_change_fail_closed(self):
        self.setup_run('from pathlib import Path\nimport sys\nPath(sys.argv[1]).write_text("changed")')
        self.put('data/input.txt', 'original')
        result = run_capture.execute(self.root, 'RUN-R', {**self.request, 'inputs':['data/input.txt'], 'args':['{input0}']})
        self.assertEqual(result['execution_status'], 'failed')
        self.assertIn('输入版本变化', str(result['errors']))
        # A separate writer must not have its newer Run metadata overwritten.
        original_replace = evidence.replace
        def competing(path, data, expected):
            self.put('runs/attempt/run.json', {**evidence.read(path), 'title':'concurrent'})
            return original_replace(path, data, expected)
        with patch.object(evidence, 'replace', side_effect=competing):
            with self.assertRaisesRegex(ValueError, '检查后变化'):
                run_capture.register(self.root, 'RUN-R', artifacts=['scripts/实验 程序.py'])
        self.assertEqual(evidence.read(self.card)['title'], 'concurrent')

    def test_c06_output_business_names_are_materials_not_objects(self):
        self.setup_run('from pathlib import Path\nPath("run.json").write_text("this is raw output, not metadata")')
        result = run_capture.execute(self.root, 'RUN-R', self.request)
        self.assertEqual(result['execution_status'], 'succeeded')
        self.assertEqual(manifests(self.root, {'run.json'}), [self.card])
        self.assertEqual(len([x for x in owners.list_owners(self.root) if x['owner_type']=='run']), 1)
        output = self.root / result['output_dir'] / 'run.json'
        self.assertNotIn(output, list(workspace_cli.control_files(self.root)))
        self.assertIsNone(retrieval._knowledge_source(self.root, output, {'enabled': True}, {}))

    def test_c07_public_cli_exit_codes_and_actual_material_registration(self):
        self.setup_run('import sys\nprint("failed attempt")\nsys.exit(4)')
        self.put('workspace.json', {})
        request = self.put('request.json', self.request)
        cli = Path(__file__).resolve().parents[1] / 'scripts/workspace_cli.py'
        def call(*args):
            return subprocess.run([sys.executable, str(cli), *args], cwd=self.root,
                                  capture_output=True, text=True, encoding='utf-8', timeout=30)
        result = call('run-execute', 'RUN-R', '--request', str(request))
        self.assertEqual(result.returncode, 1, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['exit_code'], 4)
        self.assertTrue((self.root / receipt['receipt']).is_file())
        missing = call('run-register', 'RUN-NOT-FOUND', '--input', self.request['script'])
        self.assertEqual(missing.returncode, 2)
        self.assertNotIn('Traceback', missing.stderr)
        restored = call('run-registration-rollback', '--receipt', receipt['receipt'])
        self.assertEqual(restored.returncode, 0, restored.stderr)

    def test_c08_restricted_input_and_self_reference_do_not_write(self):
        self.setup_run()
        self.put('research/private/research.json', {'research_id':'RES-PRIVATE','sensitivity':'restricted'})
        self.put('research/private/input.txt', 'restricted synthetic')
        before = self.card.read_bytes()
        for item in ('research/private/input.txt', 'runs/attempt/run.json'):
            with self.assertRaises(ValueError):
                run_capture.register(self.root, 'RUN-R', [item])
        self.assertEqual(self.card.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
