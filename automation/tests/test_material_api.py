"""真实合成owner/记录上的应用路由与范围分页验证。"""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from material_query_fixture import materialize, HIDDEN_TITLE
from material_query.api import dispatch, response_status
from material_query.contracts import Scope, TreeRequest
from material_query.coordinator import Coordinator
from material_query.wire import json_value


class MaterialApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.fx = materialize(Path(cls.temp.name) / "API 中文分页", isolation_root=cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.app = Coordinator(self.fx.root)
        self.scope = Scope(None, None, None, None, None, None, None, False, (), (), None, None)
        self.tree = TreeRequest(self.scope, None, None, 1, "logical")

    def tearDown(self):
        self.app.close()

    def test_capabilities_definitions_and_unknown_control_fields(self):
        result = dispatch(self.app, "capabilities", {})
        self.assertEqual(response_status(result), 200)
        self.assertEqual(len(dispatch(self.app, "definitions", {})["value"]), 6)
        self.assertEqual(dispatch(self.app, "poll", {"query_id": "x", "access_handle": "admin"})["code"], "VALIDATION")
        self.assertEqual(dispatch(self.app, "missing", {})["code"], "VALIDATION")
        self.assertEqual(response_status(dispatch(self.app, "poll", {"query_id": "x"})), 410)
        foundation = dispatch(self.app, "foundation/capabilities", {})
        self.assertEqual(len(foundation["value"]["methods"]), 43)
        self.assertEqual(dispatch(self.app, "foundation/read", {"query_id": "expired", "refs": []})["code"], "EXPIRED")

    def test_owner_pages_are_bound_to_scope_and_hide_restricted(self):
        seen, request = [], self.tree
        while True:
            result = dispatch(self.app, "structure", json_value(request))
            self.assertEqual(result["status"], "ok", result)
            seen.extend(row["node_id"] for row in result["value"]["nodes"])
            self.assertNotIn(HIDDEN_TITLE, str(result))
            cursor = result["value"]["next_cursor"]
            if not cursor:
                break
            denied = dispatch(self.app, "structure", json_value(replace(request, cursor=cursor, scope=replace(self.scope, owner_ids=()))))
            self.assertEqual(denied["code"], "EXPIRED")
            request = replace(request, cursor=cursor)
        self.assertEqual(len(seen), len(set(seen)))
        self.assertIn(self.fx.owner_ids["A"], seen)

    def test_empty_scope_and_outside_parent_are_denied(self):
        empty = replace(self.scope, owner_ids=())
        result = dispatch(self.app, "structure", json_value(replace(self.tree, scope=empty)))
        self.assertEqual(result["value"]["nodes"], [])
        result = dispatch(self.app, "structure", json_value(replace(self.tree, scope=empty, parent_node_id=self.fx.owner_ids["A"])))
        self.assertEqual(result["code"], "DENIED")

    def test_layers_and_fixed_record_pages(self):
        owner = self.fx.owner_ids["A"]
        request = replace(self.tree, parent_node_id=owner, limit=100)
        layers = dispatch(self.app, "structure", json_value(request))
        self.assertEqual(len(layers["value"]["nodes"]), 6)
        request = replace(request, parent_node_id=owner + "::L1", limit=1)
        result = dispatch(self.app, "structure", json_value(request))
        self.assertEqual(result["status"], "ok", result)
        self.assertTrue(result["value"]["nodes"])
        row = result["value"]["nodes"][0]
        self.assertEqual(row["layer"], "L1")
        self.assertGreater(row["ref"]["revision"], 0)
        self.assertEqual(len(row["ref"]["sha256"]), 64)

    def test_storage_roles_point_to_registered_fixed_locations(self):
        owner = self.fx.owner_ids["A"]
        request = replace(self.tree, parent_node_id=owner, view="storage", limit=100)
        result = dispatch(self.app, "structure", json_value(request))
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual({r["storage_role"] for r in result["value"]["nodes"]},
                         {"canonical", "source_reference", "projection", "temporary"})
        records = dispatch(self.app, "structure", json_value(replace(request, parent_node_id=owner + "::canonical")))
        self.assertTrue(records["value"]["nodes"], records)
        for row in records["value"]["nodes"]:
            self.assertTrue((self.fx.root / row["registered_path"]).is_file())
            self.assertIn("/commits/", row["registered_path"])

    def test_realization_inspection_uses_fixed_material_without_search(self):
        from material_query.legacy_adapter import from_legacy
        ref = from_legacy(self.fx.ref("A.unit.r1"))[0]
        result = dispatch(self.app, "inspect", {"refs": [json_value(ref)], "definition": {"key": "full", "version": "1"}})
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["value"][0]["state"], "direct")
        self.assertEqual(result["value"][0]["refs"][0]["sha256"], ref.sha256)
        self.assertEqual(result["consumed"]["candidates"], 0)

    def test_realization_inspection_reports_changed_original_as_stale(self):
        from material_query.legacy_adapter import from_legacy
        ref = from_legacy(self.fx.ref("A.unit.r1"))[0]
        path = self.fx.root / self.fx.sources["A"]["path"]
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\nSYNTHETIC changed source\n")
            result = dispatch(self.app, "inspect", {"refs": [json_value(ref)], "definition": {"key": "full", "version": "1"}})
            self.assertEqual(result["value"][0]["state"], "stale", result)
        finally:
            path.write_bytes(original)

    def test_public_cli_search_foundation_and_error_codes_in_real_workspace(self):
        import json
        import subprocess
        import sys
        from material_query.legacy_adapter import from_legacy
        root = Path(__file__).resolve().parents[2]
        entry = root / "automation/scripts/workspace_cli.py"
        query = json.loads((root / "automation/tests/fixtures/material-query/query-valid.json").read_text(encoding="utf-8"))[0]["input"]
        query.update(definition={"key": "full", "version": "1"}, question=self.fx.record_ids["A.unit.r2"], keywords=[], channels=["identity"])
        query["association"]["strategy"] = "existing-relations"
        ref = json_value(from_legacy(self.fx.ref("A.unit.r2"))[0])
        path = self.fx.root / "cli-query.json"
        path.write_text(json.dumps(query, ensure_ascii=False), encoding="utf-8")

        def invoke(*args):
            done = subprocess.run([sys.executable, str(entry), "material-query", *args], cwd=self.fx.root,
                                  capture_output=True, text=True, encoding="utf-8", timeout=30)
            return done.returncode, json.loads(done.stdout)

        code, result = invoke("search", "--request", str(path), "--assemble")
        self.assertIn(code, {0, 2})
        self.assertTrue(result["assembly"]["value"]["contributors"], result)
        path.write_text(json.dumps({"query": query, "action": "describe", "request": {"refs": [ref]}}), encoding="utf-8")
        code, result = invoke("foundation", "--request", str(path))
        self.assertEqual(code, 0, result)
        self.assertIn(ref["sha256"], str(result["value"]))
        code, result = invoke("definitions", "--assemble")
        self.assertEqual(code, 2)
        self.assertEqual(result["code"], "VALIDATION")
