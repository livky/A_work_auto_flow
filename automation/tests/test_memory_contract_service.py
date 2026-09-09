"""C02/C04/C07：公共服务拒绝坏草案，真实来源读取且整个工作区无写入。"""
from copy import deepcopy
from pathlib import Path
import unittest

import test_memory_evidence as fixture
import test_memory_store as store_fixture
from test_memory_contracts import examples
from memory.errors import MemoryError


class ContractServiceTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixture.MemoryEvidenceTests()
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.root, self.service = self.fx.root, self.fx.service
        self.existing = self.fx.save(self.fx.value([]))

    def snapshot(self):
        return (store_fixture.snapshot_files(self.root),
                sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob('*') if path.is_dir()))

    def rejected(self, draft, pointer):
        before = self.snapshot()
        request = store_fixture.request(draft, head=self.service.inspect("RES-TEST")["head"]["commit_id"])
        for entry in (self.service.validate_draft, self.service.commit):
            with self.assertRaises(MemoryError) as caught:
                entry(request)
            self.assertEqual(caught.exception.code, "INVALID_SCHEMA")
            self.assertTrue(any(error["path"].endswith(pointer) for error in caught.exception.errors), caught.exception.as_dict())
            self.assertEqual(self.snapshot(), before)

    def test_C02_level_kind_unknown_payload_have_precise_pointer_and_no_writes(self):
        for field, value, pointer in (("level", "L4", "/level"), ("kind", "unregistered", "/kind"),
                                      ("payload.magic_score", 100, "/payload/magic_score")):
            with self.subTest(negative={"level": "NEG-LAYER", "kind": "NEG-KIND"}.get(field, "NEG-UNKNOWN")):
                draft = self.fx.value([])
                if field.startswith("payload."):
                    draft["payload"]["magic_score"] = value
                else:
                    draft[field] = value
                self.rejected(draft, pointer)

    def test_C04_normal_boundaries_persist_and_each_missing_boundary_is_rejected(self):
        experience = self.fx.value([])
        experience["payload"].update(applicable=["SYNTHETIC ONLY A"], prohibited=["SYNTHETIC ONLY B"], retry_conditions=["Acquire input"])
        saved = self.fx.save(experience)
        for field in ("applicable", "prohibited", "retry_conditions"):
            self.assertEqual(saved["payload"][field], experience["payload"][field])
        bad = deepcopy(experience)
        bad["payload"]["applicable"] = []
        self.rejected(bad, "/payload/applicable")
        association = self.fx.value([])
        association.update(kind="association", payload=examples()["association"])
        association["payload"].update({"from": self.fx.record_ref(self.existing, "analogous_to"),
                                       "to": self.fx.record_ref(saved, "analogous_to")})
        normal = self.fx.save(association)
        self.assertEqual(normal["payload"]["transfer_limits"], association["payload"]["transfer_limits"])
        association["payload"]["transfer_limits"] = []
        self.rejected(association, "/payload/transfer_limits")

    def test_C07_registered_original_compared_to_excerpt_and_summary_stays_interpretation(self):
        original = self.fx.source.read_bytes()
        source = self.fx.value([])
        source.update(kind="source", payload=examples()["source"], body_markdown=original.decode("utf-8"))
        source["payload"].update(source_ref=self.fx.file_ref(), acquisition="verbatim_export")
        copied = self.fx.save(source)
        self.assertEqual(copied["level"], "L0")
        self.assertEqual(copied["body_markdown"], original.decode("utf-8"))
        source["body_markdown"] = "SYNTHETIC ONLY AI interpretation absent from original"
        self.rejected(source, "/body_markdown")
        interpretation = self.fx.value([])
        interpretation["body_markdown"] = source["body_markdown"]
        self.assertEqual(self.fx.save(interpretation)["level"], "L3")
        gap = store_fixture.draft()
        gap["body_markdown"] = "Original text was not acquired; no excerpt asserted."
        gap["provenance_gap"] = "SYNTHETIC ONLY original not acquired"
        stored = self.fx.save(gap)
        self.assertEqual(stored["sources"], [])
        self.assertEqual(stored["provenance_gap"], gap["provenance_gap"])
        self.assertEqual(self.fx.source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
