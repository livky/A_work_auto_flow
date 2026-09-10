"""兼容正文完整性：科学结构字段不能在full或摘要边界中静默丢失。"""
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from material_query.assembly import content_parts, readable_payload
from material_query.contracts import DefinitionRef, FixedRef


class MaterialAssemblyTests(unittest.TestCase):
    def test_legacy_detail_full_keeps_steps_formulas_variables_and_results(self):
        root = Path(__file__).resolve().parents[2]
        draft = json.loads((root / "automation/schemas/memory-detail-v2.example.json").read_text(encoding="utf-8"))["operations"][0]["draft"]
        ref = FixedRef("record", "MEM-SYNTHETIC", 1, "0" * 64, None)
        text = content_parts(draft, ref, DefinitionRef("full", "1"))[0][2]
        for key in ("method", "results"):
            self.assertIn(draft["payload"][key], text)
        for step in draft["payload"]["steps"]:
            self.assertIn(step, text)
        formula = draft["payload"]["formulas"][0]
        self.assertIn("$$\n" + formula["latex"] + "\n$$", text)
        for variable in formula["variables"]:
            self.assertIn(variable["meaning"], text)
            self.assertIn(variable["unit"], text)

    def test_experience_digest_retains_prohibitions_and_retry_conditions(self):
        payload = {"recommendation": "有条件参考", "applicable": ["时延已知"], "prohibited": ["执行器饱和时不外推"],
                   "failure_modes": ["振荡"], "retry_conditions": ["重新测定约束"]}
        text = readable_payload(payload)
        for value in payload.values():
            for item in value if isinstance(value, list) else [value]:
                self.assertIn(item, text)

    def test_section_does_not_present_first_block_as_an_unmatched_answer(self):
        from material_query.validation import QueryError
        record = {"schema_version": 3, "kind": "detail", "title": "合成方法", "record_id": "MEM-SYNTHETIC",
                  "revision": 1, "record_hash": "0" * 64,
                  "payload": {"unit_type": "method", "blocks": [{"block_id": "definition", "markdown": "完整变量定义", "requires_block_ids": []}]}}
        ref = FixedRef("record", record["record_id"], 1, record["record_hash"], None)
        with self.assertRaises(QueryError) as caught:
            content_parts(record, ref, DefinitionRef("section", "1"), "不存在的关键词")
        self.assertEqual(caught.exception.code, "SOURCE_MISSING")
