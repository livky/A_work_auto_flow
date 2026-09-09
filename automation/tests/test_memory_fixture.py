"""SYNTHETIC ONLY：W00 隔离与冻结资产的可执行断言。"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from memory_fixture import (FIXTURES, REPOSITORY, FixedClock, FixedIds, FaultInjector,
                            materialize, snapshot, workspace_cli, build_verified_legacy, evidence)


class MemoryFixtureTests(unittest.TestCase):
    def test_b01_frozen_plan_self_test_leaves_assets_unchanged(self):
        """直接执行冻结计划的正反例自检；不以此冒充产品验收。"""
        before = snapshot(FIXTURES)
        spec = importlib.util.spec_from_file_location("memory_verify_plan", FIXTURES / "verify_plan.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(["--self-test"]), 0)
        self.assertEqual(snapshot(FIXTURES), before)

    def test_b03_materialize_preserves_formal_data_and_frozen_sources(self):
        """比较全部正式业务文件/空目录和登记，不只抽查少量哨兵。"""
        areas = ["research", "runs", "knowledge", "core-algorithms", "retrieval"]
        before = {name: snapshot(REPOSITORY / name) for name in areas}
        frozen = snapshot(FIXTURES)
        with tempfile.TemporaryDirectory() as temporary:
            result = materialize(Path(temporary) / "中文 合成工作区", isolation_root=temporary)
            self.assertEqual(len(result.owners), 23)
            self.assertEqual(len({x["owner_type"] for x in result.owners.values()}), 8)
            self.assertEqual(len(result.drafts), 48)
            # 新合成对象遵循配方分类，不能意外继承真实材料模板的
            # restricted 默认值，从而混淆权限正反例的输入条件。
            for owner in result.owners.values():
                if owner["owner_type"] == "knowledge":
                    continue  # 旧平铺 Markdown 无原生分类字段，由适配器处理。
                native = json.loads((result.root / owner["path"]).read_text(encoding="utf-8"))
                if owner["owner_type"] == "tool":
                    native = native["tools"][0]
                self.assertEqual(native["sensitivity"], owner.get("sensitivity", "internal"))
            self.assertIn("SYNTHETIC ONLY", (result.root / "SYNTHETIC_ONLY.txt").read_text(encoding="utf-8"))
            errors, _ = workspace_cli.validate_workspace(result.root)
            self.assertEqual(errors, [])
            for source in result.sources.values():
                self.assertEqual(snapshot(result.root)["files"][source["path"]], source["sha256"])
            for draft in result.drafts:
                self.assertNotIn("occurred_at", draft)
                self.assertNotIn("source_id", draft["payload"])
                self.assertNotIn("keywords", draft["payload"])
            for run in (result.root / "runs").glob("*/run.json"):
                raw = json.loads(run.read_text(encoding="utf-8"))
                self.assertEqual(raw["status"], "planned")
                self.assertTrue(all(c["review"]["status"] == "not-reviewed" for c in raw["claims"]))
            with self.assertRaises(ValueError):
                materialize(result.root, isolation_root=temporary)
        self.assertEqual(snapshot(FIXTURES), frozen)
        self.assertEqual({name: snapshot(REPOSITORY / name) for name in areas}, before)

    def test_rejects_business_roots_escape_and_existing_target_without_writes(self):
        with self.assertRaises(ValueError):
            materialize(REPOSITORY / "research/synthetic-forbidden", isolation_root=REPOSITORY / "research")
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                materialize(Path(temporary).parent / "escape", isolation_root=temporary)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_fixed_inputs_and_fault_injection_are_explicit(self):
        self.assertEqual(FixedClock()(), "2026-01-01T00:00:00Z")
        ids = FixedIds(["MEM-SYN-1", "MEM-SYN-2"])
        self.assertEqual([ids(), ids()], ["MEM-SYN-1", "MEM-SYN-2"])
        with self.assertRaises(StopIteration):
            ids()
        fault = FaultInjector("before_head")
        fault("after_stage")
        with self.assertRaises(OSError):
            fault("before_head")
        fault("before_head")
        self.assertTrue(fault.fired)

    def test_real_legacy_execution_review_and_finalize(self):
        """真的运行合成代码、检查数值，再调用复核和封存；不是复制 accepted。"""
        with tempfile.TemporaryDirectory() as temporary:
            receipt = build_verified_legacy(Path(temporary) / "已验证 合成", isolation_root=temporary)
            self.assertEqual(receipt["exit_code"], 0)
            self.assertAlmostEqual(json.loads(receipt["stdout"])["offset_ms"], 1.4)
            self.assertTrue(receipt["finalization"]["finalized"])
            root = Path(receipt["root"])
            self.assertTrue(evidence.check_run(root, "RUN-SYNTHETIC", "synthetic:only")["eligible"])
            raw = evidence.read(root / "runs/synthetic-base/run.json")
            self.assertEqual(len(raw["claims"][0]["review_history"]), 1)
            self.assertEqual(raw["claims"][0]["review"]["status"], "accepted")
            self.assertIn("SYNTHETIC ONLY", raw["claims"][0]["review"]["reason"])

    def test_recipe_source_submits_through_real_service(self):
        """由冻结配方转换请求，服务分配正式身份并按回执读取固定版本。"""
        from memory.service import MemoryService
        with tempfile.TemporaryDirectory() as temporary:
            fixture = materialize(Path(temporary) / "服务合成", isolation_root=temporary)
            service = MemoryService(fixture.root, clock=fixture.clock)
            request = fixture.request(["MEM-SRC-THERMAL"])
            receipt = service.commit(request)
            self.assertIsNotNone(receipt)
            state = service.inspect("RES-SYN-THERMAL")
            self.assertEqual(len(state["records"]), 1)
            record = next(iter(state["records"].values()))
            self.assertEqual(record["kind"], "source")
            self.assertEqual(record["revision"], 1)
            self.assertEqual(record["payload"]["source_ref"]["sha256"], fixture.sources["SRC-SYN-THERMAL"]["sha256"])

    def test_source_release_without_git_uses_explicit_source_snapshot(self):
        """发行源码无 Git 仍执行真实计算，绝不把 SHA256 标注成 Git 提交。"""
        import memory_fixture
        import shutil
        with tempfile.TemporaryDirectory() as temporary:
            release = Path(temporary) / "发行源码"
            (release / "automation/scripts").mkdir(parents=True)
            shutil.copyfile(REPOSITORY / "automation/scripts/local_test_data.py", release / "automation/scripts/local_test_data.py")
            self.assertFalse((release / ".git").exists())
            with patch.object(memory_fixture, "REPOSITORY", release):
                receipt = build_verified_legacy(Path(temporary) / "执行输出", isolation_root=temporary)
            raw = evidence.read(Path(receipt["root"]) / "runs/synthetic-base/run.json")
            self.assertIsNone(raw["code"]["git_commit"])
            self.assertEqual(raw["code"]["version_kind"], "source-snapshot-sha256")
            self.assertEqual(raw["code"]["commit"], raw["code"]["generator_sha256"])
            self.assertTrue(receipt["finalization"]["finalized"])


if __name__ == "__main__":
    unittest.main()
