"""真实 F1 依赖上的输出范围、读取硬上限及用户排除回归。

A.unit 的 sources 合法固定引用 B.unit 为 prerequisite。探针包装实际
MeteredStore._record，不替换内容或鉴权；因此“零 B 调用”能证明拒绝发生
在 B 正文读取之前，而不是读取后仅从返回 JSON 中过滤掉它。
"""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from material_query_fixture import materialize
from material_query.budget import DEFAULT_BUDGET
from material_query.contracts import AssociationOptions, AssembleRequest, DefinitionRef, QueryRequest, Scope
from material_query.coordinator import Coordinator
from material_query.legacy_adapter import from_legacy
from material_query.reader import MeteredStore
from material_query.wire import json_value


class MaterialScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.fx = materialize(Path(cls.temp.name) / "范围上限 中文 F1", isolation_root=cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.app = Coordinator(self.fx.root)
        self.a, self.b = self.fx.owner_ids["A"], self.fx.owner_ids["B"]
        self.scope = Scope((self.a,), None, None, None, None, None, None, False, (), (), None, None)
        self.request = QueryRequest(DefinitionRef("full", "1"), self.fx.record_ids["A.unit"], (),
            self.scope, replace(self.scope, owner_ids=(self.a, self.b)), "exploration",
            AssociationOptions("off", "existing-relations", "1", 2, 0.15, None),
            DEFAULT_BUDGET, "current", 20, "skip", (), "", channels=("identity",))
        self.reads = []
        actual_record = MeteredStore._record

        def observed_record(store, owner, record_id, entry):
            # Record the physical read entry before calling the real hash-checked
            # implementation. A denied owner must never reach this hook.
            self.reads.append((owner["owner_id"], record_id))
            return actual_record(store, owner, record_id, entry)

        self.probe = patch.object(MeteredStore, "_record", observed_record)
        self.probe.start()

    def tearDown(self):
        self.probe.stop()
        self.app.close()

    def search(self, request):
        result = self.app.search(json_value(request))
        self.assertIn(result["status"], {"ok", "partial"}, result)
        return result

    def assemble(self, result):
        receipt = result["value"]
        self.assertEqual(len(receipt["candidates"]), 1, result)
        selected = AssembleRequest(receipt["query_id"],
            (receipt["candidates"][0]["candidate_id"],), receipt["request_digest"])
        return self.app.assemble(json_value(selected))

    def test_primary_scope_limits_output_but_ceiling_allows_source_authorization(self):
        result = self.search(self.request)
        packet = self.assemble(result)
        self.assertTrue(any(owner == self.b for owner, _ in self.reads))
        self.assertFalse(packet["value"]["complete"], packet)
        self.assertIn("必要内容被当前范围排除", packet["warnings"])
        self.assertNotIn(self.fx.record_ids["B.unit"],
            {ref["id"] for ref in packet["value"]["contributors"]})
        self.assertNotIn("MQ_B_DEFINITION", str(packet["value"]["parts"]))

    def test_owner_ceiling_rejects_parent_before_outside_dependency_body_read(self):
        result = self.search(replace(self.request, scope_ceiling=self.scope))
        self.assertEqual(result["value"]["candidates"], [], result)
        self.assertTrue(result["warnings"], result)
        self.assertFalse(any(owner == self.b for owner, _ in self.reads), self.reads)
        self.assertNotIn(self.fx.record_ids["B.unit"], str(result))

    def test_both_scopes_allow_required_fixed_content_and_complete_packet(self):
        result = self.search(replace(self.request, scope=self.request.scope_ceiling))
        packet = self.assemble(result)
        self.assertEqual(packet["status"], "ok", packet)
        self.assertTrue(packet["value"]["complete"], packet)
        self.assertIn(self.fx.record_ids["B.unit"],
            {ref["id"] for ref in packet["value"]["contributors"]})
        self.assertIn("MQ_B_DEFINITION", str(packet["value"]["parts"]))
        self.assertTrue(any(owner == self.b for owner, _ in self.reads))

    def test_explicit_user_exclusions_deny_derived_parent_under_wide_ceiling(self):
        b_ref = from_legacy(self.fx.ref("B.unit"))[0]
        for field, value in (("excluded_owner_ids", (self.b,)),
                             ("excluded_refs", (b_ref,)),
                             ("exclude_ids", (b_ref.id,))):
            with self.subTest(exclusion=field):
                self.reads.clear()
                primary = replace(self.scope, **{field: value})
                result = self.search(replace(self.request, scope=primary))
                self.assertEqual(result["value"]["candidates"], [], result)
                self.assertTrue(result["warnings"], result)
                self.assertFalse(any(owner == self.b for owner, _ in self.reads), self.reads)
                self.assertNotIn(b_ref.id, str(result))


if __name__ == "__main__":
    unittest.main()
