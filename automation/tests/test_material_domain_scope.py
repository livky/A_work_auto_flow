"""C07：真实 domain 多贡献来源的授权交集与撤权前置拦截。

该测试保留 F1 的两个真实 owner/原件登记，用公开 Memory API 保存一个
domain 所需的规范 map，直接声明两份固定原件和两条必要技术单元。
读取探针包装真实 _file / MeteredStore._record / Path.open，不返回假正文、
不把 full 冒充 domain，也不改变生产授权逻辑。
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from material_query_fixture import materialize
from memory import contracts as memory_contracts
from memory.errors import MemoryError
from memory.service import MemoryService
from material_query.budget import DEFAULT_BUDGET
from material_query.contracts import AssociationOptions, AssembleRequest, DefinitionRef, QueryRequest, Scope
from material_query.coordinator import Coordinator
from material_query.reader import MeteredStore
from material_query.wire import json_value


class MaterialDomainScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.fx = materialize(Path(cls.temporary.name) / "领域多来源 中文 F1", isolation_root=cls.temporary.name)
        fx = cls.fx
        units = [fx.ref("A.unit", "prerequisite"), fx.ref("B.unit", "prerequisite")]
        originals = [fx.source_ref("A"), fx.source_ref("B")]
        draft = {key: deepcopy(fx.records["A.map"][key]) for key in
                 (*memory_contracts.CONTENT_FIELDS, "schema_version", "record_reason")}
        draft.update(
            title="SYNTHETIC ONLY 两对象领域概览",
            body_markdown="DOMAIN_C07_MAP：固定 A/B 两项贡献的合成领域导航，未生成新科学结论。",
            # Declare both raw inputs directly. Their current registry gates are
            # therefore checked before loading either necessary contributor body.
            sources=[*originals, *units],
            payload={
                "topic": "合成领域：温度反馈与冷却反馈的限定导航",
                "goal_refs": [], "route_refs": [], "result_refs": units,
                "question_refs": [], "conflict_refs": [],
                "next_steps": ["分别核对两对象的原件授权和固定技术单元"],
                "coverage": {"owner_ids": [fx.owner_ids["A"], fx.owner_ids["B"]],
                             "source_versions": originals, "missing": []},
            },
        )
        fx.commit_draft("AB.domain", draft)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_domain_two_owner_sources_are_rechecked_before_revoked_body_reads(self):
        fx = self.fx
        app = Coordinator(fx.root)
        scope = Scope((fx.owner_ids["A"], fx.owner_ids["B"]), None, None, None, None, None, None,
                      False, (), (), None, None)
        request = QueryRequest(
            DefinitionRef("domain", "1"), fx.record_ids["AB.domain"], (), scope, scope,
            "exploration", AssociationOptions("off", "existing-relations", "1", 2, 0.15, None),
            DEFAULT_BUDGET, "current", 1, "reject", (), "", channels=("identity",),
        )
        events = []
        raw_path = (fx.root / fx.sources["B"]["path"]).absolute()
        original_file = MemoryService._file
        original_record = MeteredStore._record
        original_open = Path.open

        def observed_file(service, ref):
            events.append(("source_check", ref["target_id"]))
            try:
                value = original_file(service, ref)
            except MemoryError as exc:
                events.append(("source_error", ref["target_id"], exc.code))
                raise
            events.append(("source_allowed", ref["target_id"]))
            return value

        def observed_record(store, owner, record_id, entry):
            # This hook runs before the actual canonical record body read.
            events.append(("record_read", owner["owner_id"], record_id))
            return original_record(store, owner, record_id, entry)

        def observed_open(path, *args, **kwargs):
            mode = args[0] if args else kwargs.get("mode", "r")
            if path.absolute() == raw_path and ("r" in mode or "+" in mode):
                events.append(("raw_original_open", "B"))
            return original_open(path, *args, **kwargs)

        def selected(result):
            self.assertIn(result["status"], {"ok", "partial"}, result)
            self.assertIsNotNone(result["value"], result)
            rows = result["value"]["candidates"]
            self.assertEqual(len(rows), 1, result)
            self.assertEqual(rows[0]["refs"][0]["id"], fx.record_ids["AB.domain"])
            # No fallback was requested; the actual candidate is still domain.
            self.assertEqual(rows[0]["realization"]["definition"], {"key": "domain", "version": "1"})
            self.assertEqual(rows[0]["realization"]["state"], "assemblable")
            return AssembleRequest(result["value"]["query_id"], (rows[0]["candidate_id"],),
                                   result["value"]["request_digest"])

        def assert_revoked_gate(result):
            self.assertIn(result["status"], {"rejected", "partial"}, result)
            if result["value"] is not None:
                self.assertFalse(result["value"]["complete"], result)
            public = json.dumps(result, ensure_ascii=False)
            self.assertNotIn("MQ_B_DIGEST_R1", public)
            self.assertNotIn("MQ_B_DEFINITION", public)
            self.assertNotIn("MQ_B_ORIGINAL", public)
            self.assertIn(("source_error", fx.sources["B"]["source_id"], "ACCESS_DENIED"), events)
            self.assertNotIn(("record_read", fx.owner_ids["B"], fx.record_ids["B.unit"]), events)
            self.assertNotIn(("raw_original_open", "B"), events)

        registry_before = (fx.root / "retrieval/sources.json").read_bytes()
        try:
            with patch.object(MemoryService, "_file", observed_file), \
                    patch.object(MeteredStore, "_record", observed_record), \
                    patch.object(Path, "open", observed_open):
                search = app.search(json_value(request))
                cached_selection = selected(search)
                packet = app.assemble(json_value(cached_selection))
                self.assertEqual(packet["status"], "ok", packet)
                self.assertTrue(packet["value"]["complete"], packet)
                self.assertEqual(packet["value"]["definition"], asdict(request.definition))
                contributors = {ref["id"] for ref in packet["value"]["contributors"]}
                self.assertTrue({fx.record_ids["AB.domain"], fx.record_ids["A.unit"],
                                 fx.record_ids["B.unit"]} <= contributors)
                parts = json.dumps(packet["value"]["parts"], ensure_ascii=False)
                self.assertIn("DOMAIN_C07_MAP", parts)
                self.assertIn("MQ_A_DIGEST_R2", parts)
                self.assertIn("MQ_B_DIGEST_R1", parts)
                self.assertIn(("record_read", fx.owner_ids["B"], fx.record_ids["B.unit"]), events)
                self.assertIn(("source_allowed", fx.sources["A"]["source_id"]), events)
                self.assertIn(("source_allowed", fx.sources["B"]["source_id"]), events)

                # Create a second real selection before revocation, so both a
                # never-assembled selection and an already cached domain packet
                # must recheck the same original registration at assembly time.
                fresh_selection = selected(app.search(json_value(request)))
                with fx.source_access("B", enabled=False):
                    for label, selection in (("new assembly", fresh_selection), ("cached domain packet", cached_selection)):
                        with self.subTest(path=label):
                            events.clear()
                            result = app.assemble(json_value(selection))
                            assert_revoked_gate(result)
                            # The two-owner selection/ceiling was retained. The
                            # refusal came from B's original gate, not an owner
                            # exclusion or silently narrowed primary scope.
                            self.assertEqual(app.store.get(selection.query_id).request.scope.owner_ids,
                                             scope.owner_ids)
                self.assertEqual((fx.root / "retrieval/sources.json").read_bytes(), registry_before)
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()

