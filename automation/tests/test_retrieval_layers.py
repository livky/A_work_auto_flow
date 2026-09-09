"""Knowledge discovery must not scan raw execution or transaction archives.

These tests exercise public indexing as well as enumeration. They use isolated
data and keep the source registry enabled to prove trace permission survives.
"""
import json
from contextlib import closing
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "automation/scripts"))
import retrieval as r


class RetrievalLayerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        cfg = r.read_json(ROOT / "retrieval/config.json")
        cfg.update(include_directories=["research", "projects", "runs", "knowledge", "tools"], ocr_enabled=False)
        cfg["vector_store"] = {"provider": None}
        r.write_json(self.root / "retrieval/config.json", cfg)
        r.write_json(self.root / "retrieval/sources.json", {"sources": []})

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
        return path

    def test_nested_run_raw_artifacts_and_transactions_do_not_enter_index(self):
        base = "research/中文 深层/专题/runs/one/"
        self.put(base + "run.json", {"run_id": "RUN-ONE", "title": "Cancellation summary", "debug": "NOISY_RAW_ONLY"})
        self.put(base + "README.md", "# A readable attempt\nA cancellation observation.")
        raw = self.put(base + "outputs/deep/raw.md", "NOISY_RAW_ONLY")
        self.put(base + "inputs.json", [1, 2, 3])
        self.put("research/中文 深层/专题/memory/owner.json", {})
        transaction = self.put("research/中文 深层/专题/memory/records/old.json", {"body": "NOISY_RAW_ONLY"})
        r.write_json(self.root / "retrieval/sources.json", {"sources": [
            {"source_id": "SRC-RAW", "path": str(raw), "enabled": True},
            {"source_id": "SRC-OLD", "path": str(transaction), "enabled": True}]})
        candidates = r.discover(self.root, r.config(self.root))
        self.assertEqual({Path(x["path"]).name for x in candidates}, {"README.md", "run.json"})
        self.assertTrue(all(x["memory_level"] == "L2" for x in candidates))
        r.index(self.root)
        self.assertEqual(r.search(self.root, "NOISY_RAW_ONLY")["results"], [])
        self.assertTrue(raw.is_file())
        self.assertTrue(all(x["enabled"] for x in r.read_json(self.root / "retrieval/sources.json")["sources"]))

    def test_trace_registry_removes_prior_search_text_without_disabling_source(self):
        doc = self.put("research/topic/source.txt", "uniquetraceoriginal")
        self.assertTrue(r.search(self.root, "uniquetraceoriginal")["results"])
        r.write_json(self.root / "retrieval/sources.json", {"sources": [
            {"path": str(doc), "enabled": True, "memory_level": "L0", "discovery": "trace_only"}]})
        self.assertEqual(r.search(self.root, "uniquetraceoriginal")["results"], [])
        self.assertEqual(doc.read_text(encoding="utf-8"), "uniquetraceoriginal")

    def test_business_memory_folder_is_not_mistaken_for_transaction_home(self):
        self.put("projects/demo/code/memory/model.py", "# readable algorithm")
        self.assertEqual(r.index(self.root, dry_run=True)["count"], 1)

    def test_flat_and_tool_memory_homes_are_trace_only(self):
        for base in ("knowledge/note.md.memory", "tools/memory/TOOL-A"):
            self.put(base + "/owner.json", {})
            raw = self.put(base + "/records/r1.json", {"body": "RAW_HISTORY"})
            registry = r.read_json(self.root / "retrieval/sources.json")
            registry["sources"].append({"path": str(raw), "enabled": True})
            r.write_json(self.root / "retrieval/sources.json", registry)
        self.assertEqual(r.discover(self.root, r.config(self.root)), [])

    def test_deep_owner_sidecar_change_invalidates_cached_association(self):
        self.put("research/a/b/c/research.json", {"research_id": "RES-DEEP", "related_module_ids": ["MOD-A"]})
        doc = self.put("research/a/b/c/method/section/further/note.md", "# DeepNote\nstructured explanation")
        r.index(self.root)
        with closing(r.connect(self.root)) as db:
            before = json.loads(db.execute("SELECT meta FROM docs WHERE path=?", (str(doc),)).fetchone()[0])
        self.assertEqual(before["research_ids"], ["RES-DEEP"])
        self.assertEqual(before["module_ids"], ["MOD-A"])
        self.put("research/a/b/c/research.json", {"research_id": "RES-DEEP", "related_module_ids": ["MOD-B"]})
        r.index(self.root)
        with closing(r.connect(self.root)) as db:
            after = json.loads(db.execute("SELECT meta FROM docs WHERE path=?", (str(doc),)).fetchone()[0])
        self.assertEqual(after["module_ids"], ["MOD-B"])
        self.assertNotEqual(before["signature"], after["signature"])


if __name__ == "__main__":
    unittest.main()
