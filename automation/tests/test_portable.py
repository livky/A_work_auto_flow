"""迁移包边界回归：依赖与历史保留，机器缓存排除。"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("portable", Path(__file__).resolve().parents[1] / "scripts/portable.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PortableTests(unittest.TestCase):
    def test_package_keeps_runtime_and_history_but_omits_caches(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            keep = {".agents/skills/demo/SKILL.md", "services/qdrant/runtime/python.exe",
                    "services/qdrant/models/model.onnx", "retrieval/queries/history.json"}
            omit = {"retrieval/generated/search.sqlite3", "services/qdrant/storage/meta.json",
                    "dist/old.zip", "tmp/copy/readme.md", "automation/__pycache__/cache.pyc"}
            for name in keep | omit:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture", encoding="utf-8")
            self.assertEqual({f.relative_to(root).as_posix() for f in p.inventory(root)}, keep)
