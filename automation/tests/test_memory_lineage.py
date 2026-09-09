"""Native Run/claim provenance through the actual public CLI, never a fake MEM."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from memory_fixture import materialize, snapshot, REPOSITORY
from memory.service import MemoryService


class NativeLineageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="memory-native-lineage-")
        self.base = Path(self.temporary.name)
        self.fixture = materialize(self.base / "中文 旧对象", isolation_root=self.base)
        self.root = self.fixture.root

    def tearDown(self):
        self.temporary.cleanup()

    def public_lineage(self, ids):
        request = self.base / "lineage-request.json"
        request.write_text(json.dumps({"target_ids": ids}), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(REPOSITORY / "automation/scripts/workspace_cli.py"),
             "--root", str(self.root), "memory", "source-lineage", "--request", str(request)],
            capture_output=True, encoding="utf-8", timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def test_native_run_and_claim_share_one_registered_source_without_writes(self):
        # A planned native Run is readable provenance; no invented accepted
        # review, successful experiment, or duplicate MEM event is required.
        before = snapshot(self.root)
        result = self.public_lineage(["RUN-SYN-THERMAL", "CLM-SYN-THERMAL"])
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["sources"][0]["source_ids"], ["SRC-SYN-THERMAL"])
        self.assertEqual(result["missing"], [])
        self.assertIsNone(result["scientific_support_count"])
        self.assertEqual(snapshot(self.root), before)

    def test_memory_to_native_run_follows_existing_evidence_and_revocation(self):
        service = MemoryService(self.root)
        saved = service.commit(self.fixture.request(["MEM-EXP-THERMAL"]))
        rid = saved["record_results"][0]["record_id"]
        result = self.public_lineage([rid])
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["missing"], [])
        self.assertIn("RUN-SYN-THERMAL", result["sources"][0]["paths"][0])
        registry = self.root / "retrieval/sources.json"
        data = json.loads(registry.read_text(encoding="utf-8"))
        for source in data["sources"]:
            if source["source_id"] == "SRC-SYN-THERMAL":
                source["enabled"] = False
        registry.write_text(json.dumps(data), encoding="utf-8")
        after_revoke = snapshot(self.root)
        denied = self.public_lineage([rid])
        self.assertEqual(denied["source_count"], 0)
        self.assertTrue(denied["missing"])
        self.assertEqual(snapshot(self.root), after_revoke)

    def test_changed_original_is_not_rebound_to_a_new_hash(self):
        original = self.root / self.fixture.sources["SRC-SYN-THERMAL"]["path"]
        original.write_bytes(original.read_bytes() + b"\nSYNTHETIC changed after binding.\n")
        before = snapshot(self.root)
        result = self.public_lineage(["CLM-SYN-THERMAL"])
        self.assertEqual(result["source_count"], 0)
        self.assertTrue(result["missing"])
        self.assertEqual(snapshot(self.root), before)


if __name__ == "__main__":
    unittest.main()
