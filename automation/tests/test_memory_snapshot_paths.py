"""快照范围的路径枚举优化：验证工作量以及缓存后的路径变更拒绝。"""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import os
import subprocess
import unittest
from unittest.mock import patch

import test_memory_store as fixture
from memory import owners
from memory.errors import MemoryError


class SnapshotPathTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixture.MemoryStoreTests()
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.root, self.store = self.fx.root, self.fx.service.store
        request = fixture.request()
        request["operations"] = []
        for number in range(32):
            draft = fixture.draft()
            draft["title"] = "SYNTHETIC ONLY snapshot item " + str(number)
            request["operations"].append({"op": "put_record", "client_key": str(number), "draft": draft})
        self.receipt = self.fx.service.commit(request)
        self.owner = owners.resolve_owner(self.root, "RES-TEST")

    def test_directory_enumeration_is_linear_and_cache_is_per_snapshot(self):
        # Count actual directory enumerations, not time: slow Windows storage
        # should not make this complexity assertion flaky.
        calls = Counter()
        original = Path.iterdir
        def counted(path):
            calls[path] += 1
            return original(path)
        with patch.object(Path, "iterdir", counted):
            first = self.store.read_snapshot(self.owner)
            first_calls = deepcopy(calls)
            second = self.store.read_snapshot(self.owner)
        self.assertEqual(len(first["records"]), 32)
        self.assertEqual(first, second)
        self.assertTrue(first_calls)
        # One initial enumeration and one final safety recheck per directory,
        # independent of how many records share that directory.
        self.assertTrue(all(count == 2 for count in first_calls.values()), first_calls)
        self.assertEqual(calls, Counter({path: count * 2 for path, count in first_calls.items()}))

    def test_case_change_during_snapshot_is_not_hidden_by_cached_parent(self):
        original = self.store.read_json
        directory = self.root / self.owner["memory_home"] / "commits" / self.receipt["commit_id"] / "records"
        renamed = directory.with_name("RECORDS")
        changed = False
        def changing(path):
            nonlocal changed
            result = original(path)
            if path.parent == directory and not changed:
                directory.rename(renamed)
                changed = True
            return result
        try:
            with patch.object(self.store, "read_json", changing), self.assertRaises(MemoryError) as caught:
                self.store.read_snapshot(self.owner)
            self.assertEqual(caught.exception.code, "UNSAFE_PATH")
        finally:
            if changed:
                renamed.rename(directory)
        self.assertEqual(len(self.store.read_snapshot(self.owner)["records"]), 32)

    @unittest.skipUnless(os.name == "nt", "Windows junction safety boundary")
    def test_junction_inserted_after_cached_parent_is_rejected_before_return(self):
        original = self.store.read_json
        directory = self.root / self.owner["memory_home"] / "commits" / self.receipt["commit_id"] / "records"
        parked = directory.with_name("records-original")
        self.assertTrue(directory.resolve().is_relative_to(self.root))
        self.assertTrue(parked.absolute().is_relative_to(self.root))
        changed = False
        def changing(path):
            nonlocal changed
            result = original(path)
            if path.parent == directory and not changed:
                directory.rename(parked)
                changed = True
                made = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(directory), str(parked)], capture_output=True)
                self.assertEqual(made.returncode, 0, made.stderr)
            return result
        try:
            with patch.object(self.store, "read_json", changing), self.assertRaises(MemoryError) as caught:
                self.store.read_snapshot(self.owner)
            self.assertEqual(caught.exception.code, "UNSAFE_PATH")
        finally:
            if changed:
                if directory.exists():
                    os.rmdir(directory)  # Remove only the junction, never its target tree.
                parked.rename(directory)
        self.assertEqual(len(self.store.read_snapshot(self.owner)["records"]), 32)


if __name__ == "__main__":
    unittest.main()
