"""O01/O02/O05：八类对象保留专用字段及新默认四类记忆；平铺移动保留身份。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid

import test_memory_store as fixture
from test_memory_contracts import draft as kind_draft
from memory import migration, owners
from memory.service import MemoryService


class OwnerServiceTests(unittest.TestCase):
    def test_O01_O05_eight_native_types_public_inspect_and_default_v2_kinds(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC 八类对象 ") as temporary:
            root = Path(temporary)
            def put(name, value):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value, encoding="utf-8")
                return path
            cards = [("research/a/research.json", "research_id", "RES-A", "research", "questions", ["SYNTHETIC question"]),
                     ("runs/a/run.json", "run_id", "RUN-A", "run", "parameters", {"synthetic": 1}),
                     ("projects/a/project.json", "project_id", "PRJ-A", "project", "milestones", ["SYNTHETIC milestone"]),
                     ("core-algorithms/a/module.json", "module_id", "MOD-A", "core-algorithm", "equation", "SYNTHETIC x=y"),
                     ("knowledge/a.evidence.json", "evidence_id", "EVD-A", "knowledge", "claims", []),
                     ("reports/manifests/a.json", "report_id", "REP-A", "report", "sections", ["SYNTHETIC section"]),
                     ("data/catalog/a.dataset.json", "dataset_id", "DATA-A", "data", "columns", ["synthetic_column"])]
            expected = {}
            for path, id_field, oid, kind, field, value in cards:
                put(path, {id_field: oid, "title": "SYNTHETIC ONLY", "sensitivity": "internal", field: value})
                expected[oid] = (kind, field, value)
            put("tools/a/runner.py", "# SYNTHETIC ONLY\n")
            put("tools/registry.json", {"tools": [{"tool_id": "TOOL-A", "entrypoint": "tools/a/runner.py", "sensitivity": "internal"}]})
            expected["TOOL-A"] = ("tool", "entrypoint", "tools/a/runner.py")
            source = put("controlled.txt", "SYNTHETIC ONLY original source")
            put("retrieval/sources.json", {"schema_version": 1, "sources": [{"source_id": "SRC-EIGHT", "path": "controlled.txt", "enabled": True, "sensitivity": "internal"}]})
            put("workspace.json", {"schema_version": 1})
            original = fixture.snapshot_files(root)
            directories = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_dir())
            service = MemoryService(root)
            for oid, (kind, field, value) in expected.items():
                with self.subTest(phase="read-only", owner_type=kind):
                    state = service.inspect(oid)
                    self.assertEqual(state["owner"]["owner_type"], kind)
                    self.assertEqual(state["owner"]["native_data"][field], value)
                    self.assertEqual(state["records"], {})
                    self.assertIsNone(state["head"])
                    self.assertEqual(state["policy"]["values"]["mode"], "explore" if kind == "research" else "basic")
            self.assertEqual(fixture.snapshot_files(root), original)
            self.assertEqual(sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_dir()), directories)
            file_ref = {"target_kind": "file", "target_id": "SRC-EIGHT", "revision": None,
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "locator": "lines:1-1", "relation": "input"}
            for oid, (kind, _field, _value) in expected.items():
                with self.subTest(phase="default-v2-kinds", owner_type=kind):
                    operations = []
                    for record_kind in ("source", "event", "experience", "map"):
                        value = kind_draft(record_kind)
                        value.update(owner_id=oid, sources=[deepcopy(file_ref)])
                        if record_kind == "source":
                            value["payload"]["source_ref"] = deepcopy(file_ref)
                        operations.append({"op": "put_record", "client_key": record_kind, "draft": value})
                    response = service.commit({"schema_version": 1, "request_id": str(uuid.uuid4()), "owner_id": oid,
                        "expected_head": None, "actor": {"kind": "workflow", "id": "synthetic-eight-types"}, "operations": operations})
                    self.assertEqual(response["save_status"], "committed")
                    state = service.inspect(oid)
                    # These are newly constructed, unversioned drafts. The v1
                    # request envelope does not opt them into legacy records;
                    # the separate detail document is the new taxonomy's L1.
                    self.assertEqual({record["schema_version"] for record in state["records"].values()}, {2})
                    self.assertEqual({record["kind"]: record["level"] for record in state["records"].values()},
                                     {"source": "L0", "event": "L2", "experience": "L3", "map": "L4"})
                    self.assertEqual(len(state["records"]), 4)
            after = fixture.snapshot_files(root)
            for name, digest in original.items():
                self.assertEqual(after[name], digest, name)

    def test_O02_flat_adoption_repeat_and_mapped_import_keep_obj_and_fixed_ref(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC 平铺迁移 ") as temporary:
            base = Path(temporary)
            root, target = base / "source", base / "target"
            native = root / "knowledge/原始 中文.md"
            native.parent.mkdir(parents=True)
            native.write_bytes("# SYNTHETIC ONLY 原始正文\n".encode("utf-8"))
            target.mkdir()
            original = native.read_bytes()
            view = owners.list_owners(root)[0]
            adopted = owners.adopt_owner(root, view["native_ref"], view["fingerprint"])
            again = owners.adopt_owner(root, view["native_ref"], view["fingerprint"])
            oid = adopted["owner_id"]
            self.assertTrue(oid.startswith("OBJ-"))
            self.assertEqual(again["owner_id"], oid)
            self.assertEqual(len(list(root.rglob("owner.json"))), 1)
            service = MemoryService(root)
            first = service.commit(fixture.request(fixture.draft(oid)))
            rid = first["record_results"][0]["record_id"]
            value = fixture.draft(oid)
            fixed = {"target_kind": "record", "target_id": rid, "revision": 1, "sha256": None, "relation": "background", "locator": "body"}
            value.update(title="SYNTHETIC ONLY fixed reference", sources=[fixed])
            service.commit(fixture.request(value, head=first["commit_id"]))
            snapshot = service.inspect(oid)
            package = root / ".local/flat.zip"
            migration.export_owner(root, oid, package)
            mapped = "knowledge/迁移 后/经验.md"
            plan = migration.preview_import(target, package, {adopted["native_ref"]["path"]: mapped})
            migration.import_package(target, plan)
            moved = MemoryService(target).inspect(oid)
            self.assertEqual(moved["owner"]["owner_id"], oid)
            self.assertEqual(moved["owner"]["native_ref"]["path"], mapped)
            self.assertEqual(moved["records"], snapshot["records"])
            self.assertTrue(any(record["sources"] == [fixed] for record in moved["records"].values()))
            self.assertEqual((target / mapped).read_bytes(), original)
            self.assertEqual(native.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
