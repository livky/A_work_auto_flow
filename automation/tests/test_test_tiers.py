"""Behavioral tier-runner tests using tiny isolated subprocess suites only."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'automation/testing'))
import catalog as test_catalog
import runner as tiers
import atomic_io


class TieredTestingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tests = self.root / 'automation/tests'
        self.tests.mkdir(parents=True)
        self.tool = self.root / 'automation/testing'
        self.tool.mkdir()
        shutil.copyfile(ROOT / 'automation/testing/worker.py', self.tool / 'worker.py')
        shutil.copyfile(ROOT / 'automation/testing/atomic_io.py', self.tool / 'atomic_io.py')
        self.module = self.tests / 'test_tiny.py'
        self.module.write_text('import unittest, time\nclass Tiny(unittest.TestCase):\n'
            '    def test_ok(self): self.assertEqual(2 + 2, 4)\n'
            '    def test_skip(self): self.skipTest("fixture capability missing")\n'
            '    def test_fail(self): self.assertEqual(1, 2)\n'
            '    def test_slow(self): time.sleep(5)\n', encoding='utf-8')
        entries = []
        for entry in test_catalog.discover(self.root).values():
            entries.append({**entry, 'capability': 'core', 'quick': entry['selector'].endswith('test_ok'),
                            'full': not entry['selector'].endswith('test_slow'), 'requires': [], 'authorization': ['scale'] if entry['selector'].endswith('test_slow') else []})
        self.catalog = {'schema_version': 1, 'revision': 1, 'capabilities': [{'id': 'core', 'title': 'fixture', 'acceptance': 'tiny suite'}], 'tests': entries}
        self.save_catalog()

    def save_catalog(self):
        (self.tool / 'catalog.json').write_text(json.dumps(self.catalog), encoding='utf-8')

    def command(self, *args):
        return tiers.execute(self.root, list(args))

    def prepare(self, *extra, path='.local/selection.json'):
        value, code = self.command('prepare', '--out', path, '--goal', 'synthetic framework acceptance', *extra)
        self.assertEqual(code, 0, value)
        return self.root / path

    def test_catalog_detects_new_missing_and_duplicate_tests(self):
        self.assertEqual(test_catalog.audit(self.root)['status'], 'passed')
        self.module.write_text(self.module.read_text() + '    def test_new(self): pass\n', encoding='utf-8')
        self.assertEqual(test_catalog.audit(self.root)['unclassified'], ['python:test_tiny.Tiny.test_new'])
        value, code = self.command('prepare', '--out', '.local/not-created.json', '--goal', 'new test')
        self.assertNotEqual(code, 0)
        self.assertFalse((self.root / '.local/not-created.json').exists())
        value, code = self.command('register', '--module', 'test_tiny', '--capability', 'core', '--reason', 'classify new behavior')
        self.assertEqual(code, 0, value)
        self.assertTrue(Path(value['previous_catalog']).is_file())
        self.assertEqual(test_catalog.audit(self.root)['status'], 'passed')
        self.module.unlink()
        self.assertTrue(test_catalog.audit(self.root)['missing'])

    def test_selection_updates_keep_prior_bytes_and_require_fresh_discovery(self):
        first = self.prepare('--actual-ai', 'A01')
        original = first.read_bytes()
        self.assertNotEqual(self.command('prepare', '--out', str(first), '--goal', 'overwrite')[1], 0)
        value, code = self.command('update', '--plan', str(first), '--out', '.local/selection-v2.json', '--reason', 'include core behavior', '--capability', 'core')
        self.assertEqual(code, 0, value)
        self.assertEqual(first.read_bytes(), original)
        updated = test_catalog.read_json(self.root / '.local/selection-v2.json')
        self.assertEqual(updated['selection_version'], 2)
        self.assertEqual(updated['actual_ai_scenarios'], ['A01'])
        self.assertNotIn('python:test_tiny.Tiny.test_slow', updated['selected_tests'])
        self.catalog['revision'] += 1
        self.save_catalog()
        self.assertEqual(self.command('validate', '--plan', str(first))[0]['status'], 'failed')

    def test_forged_empty_selection_and_business_output_are_rejected(self):
        plan = self.prepare()
        value = test_catalog.read_json(plan)
        value['selected_tests'] = []
        value['selection_fingerprint'] = test_catalog.digest({k: v for k, v in value.items() if k != 'selection_fingerprint'})
        self.assertEqual(tiers.validate(self.root, value)['status'], 'failed')
        value, code = self.command('prepare', '--out', 'research/new-original.json', '--goal', 'forbidden output')
        self.assertNotEqual(code, 0)
        self.assertFalse((self.root / 'research').exists())
        with self.assertRaises(ValueError):
            tiers.safe_path(self.root, self.root.parent / 'escaped.json', output=True)

    def test_real_subprocess_pass_keeps_command_fingerprints_and_no_overwrite(self):
        plan = self.prepare()
        value, code = self.command('run', '--plan', str(plan), '--out', '.local/attempt-01', '--timeout', '20')
        self.assertEqual(code, 0, value)
        result = test_catalog.read_json(self.root / '.local/attempt-01/results.json')
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['steps'][0]['total'], 1)
        self.assertIsInstance(result['steps'][0]['command'], list)
        self.assertIn('automation/testing/worker.py', result['program_fingerprints'])
        self.assertEqual(result['human_review'], 'not-reviewed')
        self.assertNotEqual(self.command('run', '--plan', str(plan), '--out', '.local/attempt-01')[1], 0)
        self.assertEqual(test_catalog.read_json(self.root / '.local/attempt-01/results.json'), result)

    def test_real_discover_reports_failure_and_skip_without_green_overall(self):
        plan = self.prepare('--tier', 'full')
        value, code = self.command('run', '--plan', str(plan), '--out', '.local/full', '--timeout', '20')
        self.assertNotEqual(code, 0)
        self.assertEqual(value['status'], 'failed')
        raw = test_catalog.read_json(self.root / '.local/full/01-python.json')
        self.assertEqual((raw['total'], raw['failures'], raw['skipped']), (3, 1, 1))
        self.assertEqual({row['status'] for row in raw['tests']}, {'passed', 'failed', 'skipped'})
        process = {'exit_code': 0, 'process_status': 'completed'}
        self.assertEqual(tiers.interpret('python', {'total': 0}, 1, process)['status'], 'failed')
        self.assertEqual(tiers.interpret('python', {'total': 1, 'skipped': 1}, 1, process)['status'], 'incomplete')
        self.assertEqual(tiers.interpret('component', {'numTotalTests': 2, 'numFailedTests': 0}, 1, process)['status'], 'failed')

    def test_scale_needs_explicit_selection_and_authorization(self):
        plan = self.prepare('--add-test', 'python:test_tiny.Tiny.test_slow')
        value, code = self.command('run', '--plan', str(plan), '--out', '.local/no-scale', '--timeout', '20')
        self.assertNotEqual(code, 0)
        self.assertEqual(value['status'], 'incomplete')
        result = test_catalog.read_json(self.root / '.local/no-scale/results.json')
        self.assertEqual(len(result['not_run']), 1)
        self.assertIn('scale', result['not_run'][0]['reason'])
        self.assertEqual(result['steps'][0]['total'], 1)

    def test_timeout_keeps_partial_results_and_does_not_overwrite_selection(self):
        plan = self.prepare('--add-test', 'python:test_tiny.Tiny.test_slow', '--allow-capability', 'scale')
        original = plan.read_bytes()
        value, code = self.command('run', '--plan', str(plan), '--out', '.local/timeout', '--timeout', '0.5')
        self.assertNotEqual(code, 0)
        result = test_catalog.read_json(self.root / '.local/timeout/results.json')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['steps'][0]['status'], 'timed-out')
        self.assertTrue((self.root / '.local/timeout/01-python.log').is_file())
        self.assertTrue((self.root / '.local/timeout/README.md').is_file())
        self.assertEqual(plan.read_bytes(), original)

    def test_component_selection_ignores_filtered_skip_but_rejects_selected_skip_or_wrong_identity(self):
        selected = [{'id': 'component:src/reading.test.tsx::selected'}]
        raw = {'numTotalTests': 2, 'numPendingTests': 1, 'testResults': [{
            'name': 'C:/fixture/automation/frontend/src/reading.test.tsx',
            'assertionResults': [{'title': 'selected', 'status': 'passed'},
                                 {'title': 'deferred scale', 'status': 'skipped'}]}]}
        process = {'exit_code': 0, 'process_status': 'completed'}
        result = tiers.interpret('component', raw, 1, process, selected)
        self.assertEqual((result['status'], result['total'], result['skipped']), ('passed', 1, 0))
        self.assertEqual(result['filtered_out'], ['component:src/reading.test.tsx::deferred scale'])
        raw['testResults'][0]['assertionResults'][0]['status'] = 'skipped'
        self.assertEqual(tiers.interpret('component', raw, 1, process, selected)['status'], 'incomplete')
        raw['testResults'][0]['assertionResults'][1]['status'] = 'passed'
        self.assertEqual(tiers.interpret('component', raw, 1, process, selected)['status'], 'failed')
        raw['testResults'][0]['assertionResults'] = []
        self.assertTrue(tiers.interpret('component', raw, 1, process, selected)['missing'])

    def test_atomic_sharing_retries_preserve_errors_and_pending_payload_on_exhaustion(self):
        path = self.root / '.local/progress.json'
        real_replace = atomic_io.os.replace
        sharing = PermissionError('synthetic Windows reader sharing conflict')
        sharing.winerror = 5
        conflicts = []
        def transient(source, destination):
            if len(conflicts) < 2:
                conflicts.append(True)
                raise sharing
            return real_replace(source, destination)
        with patch.object(atomic_io.os, 'replace', side_effect=transient) as replacing, patch.object(atomic_io.time, 'sleep'):
            tiers.save_progress(path, {'status': 'running'})
        self.assertEqual(replacing.call_count, 3)
        self.assertEqual(test_catalog.read_json(path), {'status': 'running'})
        events = path.with_name(path.name + '.write-events.jsonl')
        self.assertEqual(len(events.read_text(encoding='utf-8').splitlines()), 2)
        with patch.object(atomic_io.os, 'replace', side_effect=sharing) as replacing, patch.object(atomic_io.time, 'sleep'):
            with self.assertRaises(PermissionError):
                tiers.save_progress(path, {'status': 'failed'})
        self.assertEqual(replacing.call_count, 6)
        self.assertTrue(list(path.parent.glob('progress.json.pending-*')))
        # Generic access errors without a Windows transient code are not retried.
        with patch.object(atomic_io.os, 'replace', side_effect=OSError('permanent IO')) as replacing:
            with self.assertRaises(OSError):
                tiers.save_progress(path, {'status': 'failed'})
        self.assertEqual(replacing.call_count, 1)

    def test_receipt_failure_marks_unstarted_stage_failed_and_preserves_final_fallback(self):
        plan = self.prepare()
        original = tiers.save_progress
        calls = []
        def persist(path, value):
            calls.append(path)
            if len(calls) > 1:
                raise PermissionError('receipt remains locked')
            return original(path, value)
        with patch.object(tiers, 'save_progress', side_effect=persist), patch.object(tiers, 'run_process') as launch:
            value, code = self.command('run', '--plan', str(plan), '--out', '.local/locked')
        launch.assert_not_called()
        self.assertNotEqual(code, 0)
        result = test_catalog.read_json(value['fallback_receipt'])
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['steps'][0]['status'], 'failed')
        self.assertEqual(len(result['not_run']), 1)
        self.assertIn('final_persist_error', result)

if __name__ == '__main__':
    unittest.main()
