"""关联算法及真实修订测试，所有内容仅限隔离合成对象。"""
from copy import deepcopy
import uuid
import unittest
from test_memory_store import MemoryStoreTests, draft, request
from memory import associations
from memory.errors import MemoryError


class AssociationTests(unittest.TestCase):
    setUp = MemoryStoreTests.setUp
    tearDown = MemoryStoreTests.tearDown
    def test_G01_G02_explanation_and_vector_math(self):
        r = associations.keyword_candidates(["预热", "偏差", "条件"], ["预热", "偏差", "夹具"])
        self.assertEqual(r["score"], .5)
        self.assertEqual(r["shared"], ["偏差", "预热"])
        self.assertFalse(associations.keyword_candidates(["预热"], ["预热", "夹具"])["eligible"])
        for vector, expected in [([1, 0], 1), ([0, 1], 0)]:
            r = associations.semantic_candidates([1, 0], vector, encoder="synthetic", model="deterministic",
                                                  source_versions=["synthetic-r1"])
            self.assertAlmostEqual(r["score"], expected, places=12)

    def test_G03_G04_G07_single_edge_history_stale_and_boundaries(self):
        receipt = self.service.commit(request())
        a = self.service.inspect("RES-TEST")["records"][receipt["record_results"][0]["record_id"]]
        second = draft(); second["title"] = "另一个合成经验"
        receipt = self.service.commit(request(second, head=receipt["commit_id"]))
        b = self.service.inspect("RES-TEST")["records"][receipt["record_results"][0]["record_id"]]
        payload = {"from": associations.record_ref(a), "to": associations.record_ref(b),
                   "relation": "analogous_to", "explanation": "共同漂移问题但不是验证",
                   "shared_structure": "输入前置状态影响结果", "transfer_limits": ["夹具不同不能迁移数值"],
                   "basis_refs": [associations.record_ref(a), associations.record_ref(b)], "status": "accepted"}
        req = {"request_id": str(uuid.uuid4()), "actor": {"kind": "ai", "id": "synthetic-test"},
               "owner_id": "RES-TEST", "expected_head": receipt["commit_id"], "payload": payload, "reason": "保留类比边界"}
        edge_receipt = associations.decide(self.service, req)
        self.assertEqual(associations.decide(self.service, req)["commit_id"], edge_receipt["commit_id"])
        edge_id = edge_receipt["record_results"][0]["record_id"]
        for status in ("rejected", "withdrawn"):
            req.update(request_id=str(uuid.uuid4()), expected_head=edge_receipt["commit_id"])
            req["payload"]["status"] = status
            edge_receipt = associations.decide(self.service, req)
            self.assertEqual(edge_receipt["record_results"][0]["record_id"], edge_id)
        edge = self.service.inspect("RES-TEST")["records"][edge_id]
        self.assertEqual(edge["revision"], 3)
        self.assertEqual(self.service.inspect("RES-TEST", 1, record_id=edge_id)["record"]["payload"]["status"], "accepted")
        update = draft(); update["body_markdown"] = "新合成依据，旧关系须重验"
        self.service.commit(request(update, head=edge_receipt["commit_id"], rid=a["record_id"], revision=1))
        self.assertTrue(associations.view(self.service, edge)["stale"])
        bad = deepcopy(req); bad.update(request_id=str(uuid.uuid4()), expected_head=self.service.inspect("RES-TEST")["head"]["commit_id"])
        bad["payload"]["transfer_limits"] = []
        with self.assertRaises(MemoryError):
            associations.decide(self.service, bad)

    def test_G05_G06_exclusion_before_graph_walk(self):
        def edge(a,b):
            return {"from": {"target_id": a}, "to": {"target_id": b}, "relation": "related_to", "status": "accepted"}
        edges = [edge("A","B"), edge("B","C"), edge("C","D"), edge("D","A"), edge("B","D")]
        one = associations.expand_neighbors(["A"], edges, hops=1)
        self.assertEqual({x["target_id"] for x in one}, {"B"})
        two = associations.expand_neighbors(["A"], edges, hops=2)
        self.assertEqual({x["target_id"] for x in two}, {"B","C","D"})
        line = [edge("A","B"), edge("B","C")]
        self.assertEqual(associations.expand_neighbors(["A"], line, hops=2, exclude_ids=["B"]), [])
        self.assertEqual(associations.expand_neighbors(["A"], line, hops=2, allowed_ids=["A","C"]), [])
        with self.assertRaises(MemoryError):
            associations.expand_neighbors(["A"], edges, expansion_count=2)


del MemoryStoreTests
