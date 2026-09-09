"""Subprocess-only unittest adapter with incremental machine-readable results."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomic_io import replace_with_retry


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def run(root, identities, output, discover=False, all_identities=None):
    sys.path.insert(0, str(root / 'automation/tests'))
    sys.path.insert(0, str(root / 'automation/scripts'))
    if not identities or len(identities) != len(set(identities)):
        raise ValueError('选择不能为空或重复')
    if discover:
        all_tests = list(flatten(unittest.defaultTestLoader.discover(str(root / 'automation/tests'))))
        mapping = {test.id(): test for test in all_tests}
        if all_identities is not None and set(mapping) != set(all_identities):
            raise ValueError('运行时discover与登记目录不一致（含继承或加载错误）: ' + str(sorted(set(mapping) ^ set(all_identities))))
        if not set(identities).issubset(mapping):
            raise ValueError('运行时discover未发现冻结测试: ' + str(sorted(set(identities) - set(mapping))))
        suite = unittest.TestSuite(mapping[identity] for identity in identities)
    else:
        suite = unittest.defaultTestLoader.loadTestsFromNames(identities)
    discovered = [test.id() for test in flatten(suite)]
    if sorted(discovered) != sorted(identities):
        raise ValueError('实际加载测试与冻结ID不一致: ' + str(discovered))
    events = []
    class Result(unittest.TextTestResult):
        def startTest(self, test):
            self.started = time.monotonic()
            self.outcome = 'passed'
            self.detail = ''
            super().startTest(test)
        def addFailure(self, test, err):
            self.outcome, self.detail = 'failed', self._exc_info_to_string(err, test)
            super().addFailure(test, err)
        def addError(self, test, err):
            self.outcome, self.detail = 'error', self._exc_info_to_string(err, test)
            super().addError(test, err)
        def addSkip(self, test, reason):
            self.outcome, self.detail = 'skipped', reason
            super().addSkip(test, reason)
        def addUnexpectedSuccess(self, test):
            self.outcome = 'unexpected-success'
            super().addUnexpectedSuccess(test)
        def addExpectedFailure(self, test, err):
            # Expected failures are an unresolved test boundary, not a green
            # acceptance criterion in this product-level execution report.
            self.outcome, self.detail = 'expected-failure', self._exc_info_to_string(err, test)
            super().addExpectedFailure(test, err)
        def addSubTest(self, test, subtest, err):
            if err is not None:
                self.outcome, self.detail = 'failed', self._exc_info_to_string(err, test)
            super().addSubTest(test, subtest, err)
        def stopTest(self, test):
            super().stopTest(test)
            events.append({'id': test.id(), 'status': self.outcome, 'reason': self.detail,
                           'elapsed_seconds': round(time.monotonic() - self.started, 4)})
            self.save()
        def save(self):
            value = {'total': self.testsRun, 'failures': len(self.failures) + len(self.unexpectedSuccesses),
                     'errors': len(self.errors), 'skipped': len(self.skipped) + len(self.expectedFailures), 'tests': events}
            temporary = output.with_suffix('.pending')
            temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
            replace_with_retry(temporary, output)
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    # Include setUpClass/tearDownClass errors, which may occur outside stopTest.
    result.save()
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--ids', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--discover', action='store_true')
    parser.add_argument('--all-ids', type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('不覆盖已有测试结果')
    return run(args.root, json.loads(args.ids.read_text(encoding='utf-8-sig')), args.out, args.discover,
               json.loads(args.all_ids.read_text(encoding='utf-8-sig')) if args.all_ids else None)

if __name__ == '__main__':
    raise SystemExit(main())
