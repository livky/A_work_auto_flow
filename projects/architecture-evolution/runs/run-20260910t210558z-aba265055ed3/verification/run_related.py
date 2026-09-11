"""在隔离 Python 运行时显式发现选定模块，避免依赖被忽略的 PYTHONPATH。"""
from pathlib import Path
import sys
import unittest

tests = Path.cwd() / "automation/tests"
sys.path.insert(0, str(tests))
suite = unittest.TestSuite()
for pattern in ("test_material_scope.py", "test_material_assembly.py",
                "test_material_queries.py", "test_material_deepening.py",
                "test_install_workspace_skills.py"):
    suite.addTests(unittest.defaultTestLoader.discover(str(tests), pattern=pattern))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
