"""M05–M07 isolated package/extraction tests; setup tests cover M01–M04/M08+.

No external originals are copied. Destination workspaces contain only synthetic
data and are removed by their TemporaryDirectory owners after verification.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

import test_memory_evidence as fixture
import test_memory_store as store_fixture
from test_memory_contracts import examples
from memory import contracts, migration, owners
from memory.errors import MemoryError
from memory.service import MemoryService


class MemoryMigrationTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixture.MemoryEvidenceTests()
        self.fx.setUp()
        self.root, self.service = self.fx.root, self.fx.service
        self.target_temp = tempfile.TemporaryDirectory(prefix="记忆迁移 目标-")
        self.target = Path(self.target_temp.name).resolve()
        (self.target / "workspace.json").write_text('{"schema_version":1}', encoding="utf-8")
        other_path = self.root / "research/pressure/research.json"
        other_path.parent.mkdir()
        other_path.write_text('{"schema_version":1,"research_id":"RES-PRESSURE","title":"SYNTHETIC ONLY excluded owner"}', encoding="utf-8")
        pressure = self.fx.save(self.fx.value([], "RES-PRESSURE"))
        value = self.fx.value([self.fx.claim("CLM-EXPORT")])
        value["sources"].append(self.fx.record_ref(pressure, "background"))
        self.record = self.fx.save(value)
        self.fx.review("CLM-EXPORT")
        value["body_markdown"] += "\nSYNTHETIC ONLY second revision"
        self.record = self.fx.save(value, self.record)
        self.fx.review("CLM-EXPORT")
        self.owner = owners.resolve_owner(self.root, "RES-TEST")
        self.package = self.root / ".local/thermal-memory.zip"
        self.export = migration.export_owner(self.root, "RES-TEST", self.package)

    def tearDown(self):
        self.target_temp.cleanup()
        self.fx.tearDown()

    def assert_code(self, code, call):
        with self.assertRaises(MemoryError) as caught:
            call()
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_M05_selected_owner_history_review_and_missing_dependencies(self):
        original = self.fx.source.read_bytes()
        with zipfile.ZipFile(self.package) as archive:
            names = archive.namelist()
            self.assertFalse(any("pressure" in name or "synthetic-source.txt" in name for name in names))
            self.assertTrue(any("/commits/" in name for name in names))
        before = store_fixture.snapshot_files(self.target)
        plan = migration.preview_import(self.target, self.package)
        self.assertEqual(before, store_fixture.snapshot_files(self.target))
        self.assertTrue(any(item["ref"]["target_id"] == "SRC-SYN" for item in plan["missing"]))
        result = migration.import_package(self.target, plan)
        self.assertEqual(result["status"], "imported")
        imported = MemoryService(self.target)
        self.assertEqual(imported.inspect("RES-TEST")["records"], self.service.inspect("RES-TEST")["records"])
        self.assertEqual(imported.inspect("RES-TEST", 1, record_id=self.record["record_id"])["record"],
                         self.service.inspect("RES-TEST", 1, record_id=self.record["record_id"])["record"])
        self.assertEqual([owner["owner_id"] for owner in owners.list_owners(self.target)], ["RES-TEST"])
        self.assertEqual(original, self.fx.source.read_bytes())
        self.assertFalse((self.target / self.fx.source.name).exists())

    def test_M05_native_locator_mapping_preserves_immutable_history(self):
        mapping = {self.owner["native_ref"]["path"]: "research/迁移 中文/research.json"}
        plan = migration.preview_import(self.target, self.package, mapping)
        migration.import_package(self.target, plan)
        imported = owners.resolve_owner(self.target, "RES-TEST")
        self.assertEqual(imported["native_ref"]["path"], mapping[self.owner["native_ref"]["path"]])
        self.assertEqual(imported["memory_home"], "research/迁移 中文/memory")
        self.assertEqual(MemoryService(self.target).inspect("RES-TEST")["records"], self.service.inspect("RES-TEST")["records"])

    def test_M05_public_cli_explicit_empty_target_never_uses_parent_workspace(self):
        """An explicit migration destination is a boundary, even without a marker.

        H16 exposed parent traversal when a freshly selected directory did not
        yet contain workspace.json. Use a real CLI subprocess under a marked
        parent: all import bytes and receipts must stay in the exact child,
        while every pre-existing parent file remains byte-for-byte unchanged.
        """
        target = self.target / "空白 迁移目标"
        target.mkdir()
        (self.target / "user-note.txt").write_text("SYNTHETIC ONLY parent user data", encoding="utf-8")
        protected = store_fixture.snapshot_files(self.target)
        cli = Path(__file__).resolve().parents[1] / "scripts/workspace_cli.py"

        def call(action, request=None, args=(), expected_code=0):
            # Requests live outside the protected parent, so its complete hash
            # comparison detects any fallback write instead of masking it.
            arguments = [sys.executable, str(cli), "--root", str(target), "memory", action, *args]
            if request is not None:
                request_path = self.root / ".local" / ("cli-" + action + ".json")
                request_path.write_text(json.dumps(request), encoding="utf-8")
                arguments += ["--request", str(request_path)]
            process = subprocess.run(arguments, cwd=target, capture_output=True,
                                     env={**os.environ, "PYTHONUTF8": "1"}, timeout=60)
            self.assertEqual(process.returncode, expected_code, process.stderr.decode("utf-8", errors="replace") + process.stdout.decode("utf-8", errors="replace"))
            return json.loads(process.stdout.decode("utf-8-sig"))

        rejected = call("migration-preview", {"package": str(self.package)}, expected_code=2)
        self.assertEqual(rejected["save_status"], "not_committed")
        self.assertEqual(rejected["error"]["code"], "INVALID_ARGUMENT")
        self.assertEqual(store_fixture.snapshot_files(self.target), protected)
        (target / "workspace.json").write_text('{"schema_version":1}', encoding="utf-8")
        target_before = store_fixture.snapshot_files(target)
        plan = call("migration-preview", {"package": str(self.package)})
        self.assertEqual(store_fixture.snapshot_files(target), target_before)
        result = call("migration-import", {"plan": plan})
        self.assertEqual(result["status"], "imported")
        self.assertTrue(Path(result["receipt_path"]).resolve().is_relative_to(target.resolve()))
        self.assertTrue((target / self.owner["native_ref"]["path"]).is_file())
        current = call("inspect", args=("RES-TEST",))
        self.assertEqual(current["records"], self.service.inspect("RES-TEST")["records"])
        after = store_fixture.snapshot_files(self.target)
        outside_target = {name: value for name, value in after.items()
                          if not Path(name).is_relative_to(target.relative_to(self.target))}
        self.assertEqual(outside_target, protected)

    def test_M06_corrupt_record_and_zip_slip_rejected_before_writes(self):
        before = store_fixture.snapshot_files(self.target)
        for variant in ("corrupt", "parent", "absolute"):
            package = self.root / ".local" / (variant + ".zip")
            with zipfile.ZipFile(self.package) as source, zipfile.ZipFile(package, "w") as output:
                changed = False
                for name in source.namelist():
                    raw = source.read(name)
                    if variant == "corrupt" and "/records/" in name and not changed:
                        raw += b"corrupt"
                        changed = True
                    output.writestr(name, raw)
                if variant == "parent":
                    output.writestr("../escape.json", b"{}")
                if variant == "absolute":
                    output.writestr("C:/escape.json", b"{}")
            self.assert_code("INTEGRITY_ERROR" if variant == "corrupt" else "UNSAFE_PATH",
                             lambda: migration.preview_import(self.target, package))
            self.assertEqual(before, store_fixture.snapshot_files(self.target))

    def test_M06_same_identity_conflict_and_identical_retry(self):
        plan = migration.preview_import(self.target, self.package)
        migration.import_package(self.target, plan)
        before = store_fixture.snapshot_files(self.target)
        self.assertEqual(migration.import_package(self.target, plan)["status"], "no_change")
        self.assertEqual(before, store_fixture.snapshot_files(self.target))
        native = self.target / self.owner["native_ref"]["path"]
        native.write_text(native.read_text(encoding="utf-8").replace("SYNTHETIC ONLY", "SYNTHETIC ONLY conflicting"), encoding="utf-8")
        before = store_fixture.snapshot_files(self.target)
        self.assert_code("VERSION_CONFLICT", lambda: migration.preview_import(self.target, self.package))
        self.assertEqual(before, store_fixture.snapshot_files(self.target))

    def test_M06_failed_import_recovers_only_created_files(self):
        plan = migration.preview_import(self.target, self.package)
        def fail(point):
            if point == "after_file":
                raise OSError("SYNTHETIC ONLY injected publication failure")
        self.assert_code("STORAGE_ERROR", lambda: migration.import_package(self.target, plan, fault=fail))
        self.assertEqual(owners.list_owners(self.target), [])
        receipts = list((self.target / ".local/memory-migrations").glob("*/receipt.json"))
        self.assertEqual(len(receipts), 1)
        self.assertEqual(json.loads(receipts[0].read_text(encoding="utf-8"))["status"], "rolled_back")
        self.assertEqual(migration.import_package(self.target, migration.preview_import(self.target, self.package))["status"], "imported")

    def test_M06_recovery_refuses_user_modifications(self):
        result = migration.import_package(self.target, migration.preview_import(self.target, self.package))
        native = self.target / self.owner["native_ref"]["path"]
        native.write_bytes(native.read_bytes() + b" ")
        before = store_fixture.snapshot_files(self.target)
        self.assert_code("VERSION_CONFLICT", lambda: migration.recover_import(self.target, result["receipt_path"], dry_run=False))
        self.assertEqual(before, store_fixture.snapshot_files(self.target))

    def test_M06_malformed_manifest_types_fail_closed_before_writes(self):
        # Recompute the manifest seal so these cases exercise structural
        # checks, rather than merely detecting a stale transport fingerprint.
        before = store_fixture.snapshot_files(self.target)
        for field, bad_value in (("native_ref", []), ("memory_home", None),
                                 ("owner_type", "unknown"), ("dependencies", {}),
                                 ("omitted", [{"ref": None, "reason": "bad"}])):
            with self.subTest(field=field):
                package = self.root / ".local" / (field + ".zip")
                with zipfile.ZipFile(self.package) as source, zipfile.ZipFile(package, "w") as output:
                    for name in source.namelist():
                        raw = source.read(name)
                        if name == "manifest.json":
                            manifest = json.loads(raw)
                            manifest[field] = bad_value
                            manifest.pop("manifest_hash")
                            manifest["manifest_hash"] = contracts.canonical_hash(manifest)
                            raw = json.dumps(manifest).encode("utf-8")
                        output.writestr(name, raw)
                self.assert_code("INTEGRITY_ERROR", lambda: migration.preview_import(self.target, package))
                self.assertEqual(before, store_fixture.snapshot_files(self.target))

    def test_M05_legacy_originals_are_declared_without_copying(self):
        native = self.root / self.owner["native_ref"]["path"]
        value = json.loads(native.read_text(encoding="utf-8"))
        value["inputs"] = [{"path": "synthetic-source.txt"}]
        native.write_text(json.dumps(value), encoding="utf-8")
        package = self.root / ".local/legacy-inventory.zip"
        exported = migration.export_owner(self.root, "RES-TEST", package)
        self.assertTrue(any(item.get("legacy_target") == "synthetic-source.txt" for item in exported["omitted"]))
        plan = migration.preview_import(self.target, package)
        self.assertTrue(any(item.get("legacy_target") == "synthetic-source.txt" for item in plan["missing"]))
        with zipfile.ZipFile(package) as archive:
            self.assertFalse(any(name.endswith("/synthetic-source.txt") for name in archive.namelist()))

    def test_M05_export_refuses_revoked_source_access(self):
        registry = self.root / "retrieval/sources.json"
        value = json.loads(registry.read_text(encoding="utf-8"))
        value["sources"][0]["enabled"] = False
        registry.write_text(json.dumps(value), encoding="utf-8")
        destination = self.root / ".local/denied-export.zip"
        self.assert_code("ACCESS_DENIED", lambda: migration.export_owner(self.root, "RES-TEST", destination))
        self.assertFalse(destination.exists())

    def test_M06_successful_recovery_removes_only_imported_bytes(self):
        before = store_fixture.snapshot_files(self.target)
        result = migration.import_package(self.target, migration.preview_import(self.target, self.package))
        preview = migration.recover_import(self.target, result["receipt_path"])
        self.assertGreater(len(preview["would_remove"]), 0)
        self.assertEqual(preview["writes"], 0)
        migration.recover_import(self.target, result["receipt_path"], dry_run=False)
        remaining = store_fixture.snapshot_files(self.target)
        self.assertEqual({name: data for name, data in remaining.items() if not name.startswith(".local/")}, before)
        self.assertEqual(owners.list_owners(self.target), [])

    def test_M07_extraction_stale_preview_unknown_facts_and_idempotency(self):
        value = self.fx.value([])
        value.update(kind="event", payload=examples()["event"])
        initial_head = self.service.inspect("RES-TEST")["head"]["commit_id"]
        request = store_fixture.request(value, head=initial_head)
        source = self.fx.file_ref("background")
        before = store_fixture.snapshot_files(self.root / self.owner["memory_home"])
        plan = migration.preview(self.root, request, source)
        self.fx.source.write_text("SYNTHETIC ONLY new original version", encoding="utf-8")
        self.assert_code("STALE_BASIS", lambda: migration.apply(self.root, plan))
        self.assertEqual(before, store_fixture.snapshot_files(self.root / self.owner["memory_home"]))
        source = self.fx.file_ref("background")
        value["sources"] = [source]
        request = store_fixture.request(value, head=initial_head)
        plan = migration.preview(self.root, request, source)
        original = self.fx.source.read_bytes()
        receipt = migration.apply(self.root, plan)
        saved = self.service.inspect("RES-TEST", record_id=receipt["record_results"][0]["record_id"])["record"]
        self.assertIsNone(saved["payload"]["occurred_at"])
        self.assertEqual(saved["payload"]["observation"]["reason"], "unknown")
        self.assertEqual(saved["sources"], [source])
        self.assertEqual(original, self.fx.source.read_bytes())
        repeated = migration.preview(self.root, store_fixture.request(value, head=receipt["commit_id"]), source)
        self.assertEqual(migration.apply(self.root, repeated)["commit_id"], receipt["commit_id"])
        self.assertEqual(self.service.inspect("RES-TEST")["head"]["commit_id"], receipt["commit_id"])


class MixedVersionMigrationTests(unittest.TestCase):
    """新层级迁移必须保留旧字节，不能以重新生成记录代替历史兼容。"""

    def test_v1_v2_detail_roundtrip_missing_dependencies_retry_and_recovery(self):
        fx = fixture.MemoryEvidenceTests()
        fx.setUp()
        self.addCleanup(fx.tearDown)
        with tempfile.TemporaryDirectory(prefix='混合版本 迁移-') as temporary:
            target = Path(temporary)
            (target / 'workspace.json').write_text('{"schema_version":1}', encoding='utf-8')
            untouched = store_fixture.snapshot_files(target)
            # 真实 v1 记录进入提交链；后续 detail 固定引用它的旧修订。
            legacy_draft = fx.value([])
            legacy_draft['schema_version'] = 1
            legacy = fx.save(legacy_draft)
            legacy_ref = fx.record_ref(legacy, 'background')
            import workspace_cli
            import evidence
            run = workspace_cli.create_run(fx.root, None, 'SYNTHETIC ONLY 混合迁移计算', owner_id='RES-TEST')
            input_path = run / 'inputs/固定 入参.json'
            input_path.parent.mkdir()
            input_path.write_text('{"a":1,"b":2}', encoding='utf-8')
            graph_path = run / 'artifacts/结果 图.svg'
            graph_path.parent.mkdir()
            graph_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text y="16">3</text></svg>', encoding='utf-8')
            registry_path = fx.root / 'retrieval/sources.json'
            registry = json.loads(registry_path.read_text(encoding='utf-8'))
            refs = []
            for path, sid in [(input_path, 'SRC-MIXED-INPUT'), (graph_path, 'SRC-MIXED-FIGURE')]:
                registry['sources'].append({'source_id': sid, 'path': path.relative_to(fx.root).as_posix(),
                    'enabled': True, 'sensitivity': 'internal', 'memory_level': 'L0', 'discovery': 'trace_only'})
                refs.append({'target_kind': 'file', 'target_id': sid, 'revision': None,
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'locator': 'whole-file', 'relation': 'input'})
            registry_path.write_text(json.dumps(registry), encoding='utf-8')
            native_run = json.loads((run / 'run.json').read_text(encoding='utf-8'))
            run_ref = {'target_kind': 'owner', 'target_id': native_run['run_id'], 'revision': None,
                'sha256': evidence.fingerprint(native_run), 'locator': 'run.json', 'relation': 'input'}
            detail_draft = fx.value([])
            detail_draft.update(schema_version=2, kind='detail', title='SYNTHETIC ONLY L1 计算说明',
                body_markdown='# 计算说明\n\n$s=1+2=3$；固定入参、结果图和旧修订依据。',
                sources=[run_ref, *refs, legacy_ref], payload=deepcopy(examples()['detail']))
            detail_draft['payload'].update(run_ref=run_ref, inputs=[refs[0]],
                figures=[{'caption': '合成结果图', 'ref': refs[1]}], results='固定合成结果：1 + 2 = 3。')
            detail = fx.save(detail_draft)
            # 同一旧记录的新修订升级到 v2，不得覆盖 r1 的字段、引用和哈希。
            next_draft = deepcopy(legacy_draft)
            next_draft.update(schema_version=2, body_markdown=legacy_draft['body_markdown'] + '\n新版补充。')
            revised = fx.save(next_draft, legacy)
            self.assertEqual(revised['schema_version'], 2)
            self.assertEqual(fx.service.inspect('RES-TEST', 1, record_id=legacy['record_id'])['record'], legacy)
            owner = owners.resolve_owner(fx.root, 'RES-TEST')
            history_before = store_fixture.snapshot_files(fx.root / owner['memory_home'])
            originals_before = {path: path.read_bytes() for path in (input_path, graph_path, run / 'run.json')}
            package = fx.root / '.local/mixed-version.zip'
            exported = migration.export_owner(fx.root, 'RES-TEST', package)
            self.assertTrue(exported)
            with zipfile.ZipFile(package) as archive:
                names = archive.namelist()
                self.assertFalse(any(name.endswith('/run.json') or '/artifacts/' in name or '/inputs/' in name for name in names))
            mapping = {owner['native_ref']['path']: 'research/迁移 深层/专题/research.json'}
            plan = migration.preview_import(target, package, mapping)
            self.assertEqual(store_fixture.snapshot_files(target), untouched)
            missing = {item['ref']['target_id'] for item in plan['missing'] if 'ref' in item}
            self.assertTrue({native_run['run_id'], 'SRC-MIXED-INPUT', 'SRC-MIXED-FIGURE'} <= missing)
            result = migration.import_package(target, plan)
            self.assertEqual(result['status'], 'imported')
            imported = MemoryService(target)
            self.assertEqual(imported.inspect('RES-TEST')['records'], fx.service.inspect('RES-TEST')['records'])
            self.assertEqual(imported.inspect('RES-TEST', 1, record_id=legacy['record_id'])['record'], legacy)
            imported_detail = imported.inspect('RES-TEST', record_id=detail['record_id'])['record']
            self.assertEqual(imported_detail['sources'], detail['sources'])
            self.assertEqual(imported_detail['record_hash'], detail['record_hash'])
            target_owner = owners.resolve_owner(target, 'RES-TEST')
            target_history = store_fixture.snapshot_files(target / target_owner['memory_home'])
            # owner.json 的原定位允许重映射；其余提交、记录、回执与 HEAD
            # 均应逐文件字节相同，不只比较重新解析后的 JSON 对象。
            self.assertEqual({k: v for k, v in history_before.items() if k != 'owner.json'},
                             {k: v for k, v in target_history.items() if k != 'owner.json'})
            after_import = store_fixture.snapshot_files(target)
            self.assertEqual(migration.import_package(target, plan)['status'], 'no_change')
            self.assertEqual(store_fixture.snapshot_files(target), after_import)
            recovery = migration.recover_import(target, result['receipt_path'])
            self.assertEqual(recovery['writes'], 0)
            self.assertEqual(store_fixture.snapshot_files(target), after_import)
            migration.recover_import(target, result['receipt_path'], dry_run=False)
            self.assertEqual({k: v for k, v in store_fixture.snapshot_files(target).items() if not k.startswith('.local/')}, untouched)
            # 失败恢复再走一次含 v2 记录的真实导入；不得留下半个 owner。
            def fail(point):
                if point == 'after_file':
                    raise OSError('SYNTHETIC ONLY mixed-version publication failure')
            with self.assertRaises(MemoryError) as caught:
                migration.import_package(target, migration.preview_import(target, package, mapping), fault=fail)
            self.assertEqual(caught.exception.code, 'STORAGE_ERROR')
            self.assertEqual(owners.list_owners(target), [])
            self.assertEqual(history_before, store_fixture.snapshot_files(fx.root / owner['memory_home']))
            for path, raw in originals_before.items():
                self.assertEqual(path.read_bytes(), raw)


class MemoryReleaseContractTests(unittest.TestCase):
    def test_release_contains_both_contract_versions_and_detail_example(self):
        import deployment
        root = Path(__file__).resolve().parents[2]
        names = set(deployment.framework_files(root))
        expected = {'automation/schemas/memory-v1.schema.json', 'automation/schemas/memory-v1.d.ts',
                    'automation/schemas/memory-v2.schema.json', 'automation/schemas/memory-v2.d.ts',
                    'automation/schemas/memory-detail-v2.example.json'}
        self.assertTrue(expected <= names, sorted(expected - names))
        self.assertTrue(all((root / name).is_file() for name in expected))


if __name__ == "__main__":
    unittest.main()
