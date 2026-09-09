"""G02/G08 真实离线编码和来源沿袭；只写隔离合成数据。"""
from copy import deepcopy
import json
import hashlib
import os
from pathlib import Path
import shutil
import unittest
import uuid
from unittest.mock import patch

from test_memory_store import MemoryStoreTests, ROOT, draft, request, snapshot_files
from memory import associations, owners
from memory.evidence_adapter import EvidenceAdapter
from memory.errors import MemoryError


def install_model_links(root, source_root=ROOT):
    """借用已验证本机模型的只读硬链接；清单/config 独立复制，无联网。"""
    source = source_root / "services/qdrant/models/multilingual-minilm"
    if not source.is_dir():
        raise RuntimeError("真实离线模型缺失；此验收不能跳过或换成 mock")
    destination = root / "services/qdrant/models/multilingual-minilm"
    for path in source.rglob("*"):
        target = destination / path.relative_to(source)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(path, target)
            except OSError:
                shutil.copyfile(path, target)
    shutil.copyfile(source_root / "services/qdrant/model-manifest.json", root / "services/qdrant/model-manifest.json")
    (root / "retrieval").mkdir(exist_ok=True)
    shutil.copyfile(source_root / "retrieval/config.json", root / "retrieval/config.json")


class RealAssociationTests(unittest.TestCase):
    setUp = MemoryStoreTests.setUp
    tearDown = MemoryStoreTests.tearDown

    def test_G02_real_384_cosine_and_propose_are_read_only_candidates(self):
        # Identical text gives a model-independent exact cosine check while the
        # real model still executes both public semantic candidate paths.
        text = "SYNTHETIC ONLY 预热后再检查零点漂移，不能直接迁移到不同夹具。"
        value = draft(); value["body_markdown"] = text
        first = self.service.commit(request(value))
        second = self.service.commit(request(value, head=first["commit_id"]))
        ids = [r["record_id"] for receipt in (first, second) for r in receipt["record_results"]]
        install_model_links(self.root)
        import qdrant_backend
        import retrieval
        backend = qdrant_backend.LocalBackend(self.root, retrieval.config(self.root), expected_dimensions=384)
        try:
            vectors = [list(v) for v in backend.model.embed([text, text])]
            model = backend.collection
        finally:
            backend.close()
        self.assertEqual([len(v) for v in vectors], [384, 384])
        records = self.service.inspect("RES-TEST")["records"]
        refs = [associations.record_ref(records[rid]) for rid in ids]
        measured = associations.semantic_candidates(*vectors, encoder="fastembed", model=model, source_versions=refs)
        self.assertAlmostEqual(measured["score"], 1.0, places=6)
        home = self.root / owners.resolve_owner(self.root, "RES-TEST")["memory_home"]
        before = snapshot_files(home)
        proposed = associations.propose(self.service, {"owner_id": "RES-TEST", "method": "semantic", "seeds": [ids[0]]})
        self.assertEqual(len(proposed["candidates"]), 1)
        candidate = proposed["candidates"][0]
        self.assertEqual(candidate["status"], "candidate")
        self.assertEqual(candidate["method"], "semantic")
        self.assertEqual(candidate["threshold"], .8)
        self.assertEqual(candidate["encoder"], "fastembed")
        self.assertEqual(candidate["source_versions"], refs)
        self.assertAlmostEqual(candidate["score"], measured["score"], places=6)
        self.assertEqual(candidate["model"], model)
        self.assertNotIn("review", candidate)
        self.assertEqual(snapshot_files(home), before)
        denied = associations.propose(self.service, {"owner_id": "RES-TEST", "method": "semantic", "seeds": [ids[0]], "exclude_ids": [ids[1]]})
        self.assertEqual(denied["candidates"], [])

    def test_G02_missing_local_model_rejects_without_network(self):
        receipt = self.service.commit(request())
        rid = receipt["record_results"][0]["record_id"]
        # Negative capability test has no model files. Observe network entry
        # points and the model constructor; positive test above stays unmocked.
        import qdrant_backend
        with patch("socket.create_connection", side_effect=AssertionError("unexpected network")) as tcp, \
             patch("urllib.request.urlopen", side_effect=AssertionError("unexpected download")) as url, \
             patch.object(qdrant_backend, "encoder", wraps=qdrant_backend.encoder) as loader:
            with self.assertRaises(MemoryError) as caught:
                associations.propose(self.service, {"owner_id": "RES-TEST", "method": "semantic", "seeds": [rid]})
            self.assertEqual(caught.exception.code, "CAPABILITY_UNAVAILABLE")
            self.assertEqual(tcp.call_count + url.call_count, 0)
            self.assertEqual(loader.call_count, 0)

    def test_G08_three_derived_summaries_do_not_become_scientific_support(self):
        # All three summaries bind the same actual source record. Associations
        # remain navigation records; adding them cannot validate the experience.
        raw = self.root / "synthetic-source.txt"
        raw.write_text("SYNTHETIC ONLY 唯一来源 D1", encoding="utf-8")
        (self.root / "retrieval").mkdir(exist_ok=True)
        registry = {"schema_version": 1, "sources": [{"source_id": "SRC-G08", "path": raw.name,
                    "enabled": True, "sensitivity": "internal"}]}
        (self.root / "retrieval/sources.json").write_text(json.dumps(registry), encoding="utf-8")
        original_ref = {"target_kind": "file", "target_id": "SRC-G08", "revision": None,
                        "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(), "locator": "完整", "relation": "derived_from"}
        source = draft(); source["title"] = "SYNTHETIC ONLY 唯一来源 D1"
        source["sources"] = [original_ref]; source["provenance_gap"] = None
        receipt = self.service.commit(request(source))
        source_id = receipt["record_results"][0]["record_id"]
        source_record = self.service.inspect("RES-TEST")["records"][source_id]
        source_ref = associations.record_ref(source_record, "derived_from")
        derived_ids = []
        for number in range(3):
            value = draft(); value["title"] = "SYNTHETIC ONLY 同源摘要 " + str(number)
            value["sources"] = [source_ref]; value["provenance_gap"] = None
            receipt = self.service.commit(request(value, head=receipt["commit_id"]))
            derived_ids.append(receipt["record_results"][0]["record_id"])
        records = self.service.inspect("RES-TEST")["records"]
        adapter = EvidenceAdapter(self.service)
        before = adapter._analyze(source_id)
        for rid in derived_ids:
            payload = {"from": associations.record_ref(records[rid]), "to": associations.record_ref(source_record),
                "relation": "derived_from", "explanation": "同一来源的派生摘要，不是独立支持",
                "shared_structure": "同一输入", "transfer_limits": ["不得计为三次验证"],
                "basis_refs": [source_ref], "status": "accepted"}
            receipt = associations.decide(self.service, {"request_id": str(uuid.uuid4()),
                "actor": {"kind": "workflow", "id": "synthetic-g08"}, "owner_id": "RES-TEST",
                "expected_head": receipt["commit_id"], "payload": payload, "reason": "保存来源沿袭"})
        current = self.service.inspect("RES-TEST")["records"]
        lineage = associations.source_lineage(self.service, derived_ids)
        self.assertEqual(lineage["source_count"], 1)
        self.assertEqual(lineage["sources"][0]["source_ids"], ["SRC-G08"])
        self.assertIsNone(lineage["scientific_support_count"])
        self.assertEqual(lineage["missing"], [])
        edges = [row for row in current.values() if row["kind"] == "association"]
        self.assertEqual(len(edges), 3)
        self.assertEqual({row["payload"]["relation"] for row in edges}, {"derived_from"})
        self.assertEqual(EvidenceAdapter(self.service)._analyze(source_id), before)
        self.assertTrue(before)  # The unreviewed source has not become evidence.


del MemoryStoreTests

if __name__ == "__main__":
    unittest.main()
