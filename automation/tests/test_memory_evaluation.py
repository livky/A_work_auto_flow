"""固定评价适配规则不使用标签择映射，也不复制文档排名。"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from memory_fixture import build_verified_legacy
from memory import evaluation
from memory import search


class EvaluationIdentityTests(unittest.TestCase):
    def test_development_retry_query_has_one_native_fts_signal_and_real_experience(self):
        from memory_evaluation_run import prepare, FIXTURES
        with tempfile.TemporaryDirectory(prefix="开发 原生去重-") as temporary:
            output = prepare(Path(temporary) / "case")
            mapping = json.loads((output / "mapping.json").read_text(encoding="utf-8"))
            # Freeze a query that actually failed in the development run. Never
            # inspect the held-out split to choose assertions or tune rankings.
            query = next(row for row in evaluation.load_queries(FIXTURES / "queries.json")["queries"]
                         if row["query_id"] == "Q-RETRY-2")
            request = {key: query[key] for key in ("query", "purpose", "scope", "owner_id")}
            result = search.search(output / "workspace", {**request, "vector": "required"}, record=False)
            self.assertIn(mapping["MEM-EXP-RETRY"], [row["canonical_id"] for row in result["candidates"]])
            for row in result["candidates"]:
                if row["canonical_id"].startswith("RUN-"):
                    self.assertFalse({"legacy_fts", "memory_fts"} <= set(row["rank_channels"]))
            self.assertTrue(any("vector" in row["rank_channels"] for row in result["candidates"]))

    def test_single_existing_claim_identity_alignment_keeps_raw_rank_and_text(self):
        with tempfile.TemporaryDirectory(prefix="评价 身份-") as temporary:
            root = Path(temporary) / "workspace"
            build_verified_legacy(root, isolation_root=temporary)
            raw = {"candidates": [{"canonical_id": "RUN-SYNTHETIC", "score": 0.125,
                "rank_channels": {"legacy_fts": 3}, "snippet": "SYNTHETIC ONLY original preview",
                "boundaries": {"limits": ["synthetic only"]}, "source_ref": {"target_id": "RUN-SYNTHETIC"}}]}
            original = deepcopy(raw)
            aligned = evaluation.align_legacy_identity(root, raw)
            self.assertEqual(raw, original)
            row = aligned["candidates"][0]
            self.assertEqual(row["canonical_id"], "CLM-SYNTHETIC")
            for key in ("score", "rank_channels", "snippet", "boundaries"):
                self.assertEqual(row[key], raw["candidates"][0][key])
            self.assertEqual(row["alignment"]["raw_canonical_id"], "RUN-SYNTHETIC")
            path = root / "runs/synthetic-base/run.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            extra = deepcopy(data["claims"][0]); extra["claim_id"] = "CLM-SYNTHETIC-SECOND"
            data["claims"].append(extra)
            path.write_text(json.dumps(data), encoding="utf-8")
            multiple = evaluation.align_legacy_identity(root, raw)
            self.assertEqual(len(multiple["candidates"]), 1)
            self.assertEqual(multiple["candidates"][0]["canonical_id"], "RUN-SYNTHETIC")
            self.assertFalse(multiple["candidates"][0]["alignment"]["mapped"])
            self.assertEqual(multiple["candidates"][0]["alignment"]["claim_count"], 2)


if __name__ == "__main__":
    unittest.main()
