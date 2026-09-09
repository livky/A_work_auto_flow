"""W01 contract tests; service/search/frontend acceptance is reported separately.

Examples exercise each registered kind; reference callbacks represent authorized
source access and never read company materials or create business directories.
"""
import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from memory import contracts as c
from memory.generate_types import generate, SCHEMA_PATH
from memory.errors import MemoryError


def fixed_ref():
    return dict(target_kind="record", target_id="MEM-example", revision=1,
                sha256=None, locator="正文", relation="references")


def examples():
    r = fixed_ref()
    return {
        "detail": dict(run_ref=dict(target_kind="owner", target_id="RUN-synthetic", revision=None,
                                    sha256="a" * 64, locator="run.json", relation="input"),
                       question="合成计算问题", method="依据固定输入比较", steps=["读取输入", "对比结果"],
                       inputs=[], parameters=[], formulas=[], figures=[], results="未运行，仅契约测试", limitations=["SYNTHETIC ONLY"]),
        "source": dict(source_ref=r, acquisition="original_link", completeness="unknown", acquired_at=None),
        "event": dict(occurred_at=None, question_refs=[], goal_ref=None, route_ref=None,
                      action="进行比较", observation={"value": None, "reason": "unknown", "note": "未记录"},
                      decision=None, decision_refs=[], run_refs=[], failure=None, claims=[]),
        "experience": dict(problem_structure="边界问题", recommendation="先核对输入", applicable=["合成案例"],
                           prohibited=["真实业务推断"], failure_modes=[], retry_conditions=["补齐输入"], claim_refs=[], claims=[]),
        "map": dict(topic="导航", goal_refs=[], route_refs=[], result_refs=[], question_refs=[], conflict_refs=[],
                    next_steps=[], coverage=dict(owner_ids=[], source_versions=[], missing=[])),
        "question": dict(question="是否可用", status="open", decision_affected="方法选择", missing_evidence=[],
                         resolution_refs=[], replacement_ref=None, reopen_reason=None),
        "goal": dict(objective="验证", constraints=[], success_criteria=[], previous_goal_ref=None, change_impact="首次"),
        "route": dict(goal_ref=r, hypothesis="假设", status="planned", attempt_refs=[], blocker=None,
                      next_step="补输入", reopen_condition="新证据", replacement_ref=None),
        "checkpoint": dict(goal_ref=r, route_refs=[], completed_refs=[], question_refs=[], next_step="补输入",
                           prerequisites=[], stop_reason="等待", budget_remaining={"value": None, "reason": "not_acquired", "note": "未取得"}),
        "association": {"from": r, "to": dict(r, target_id="MEM-other"), "relation": "analogous_to", "explanation": "类似边界",
                        "shared_structure": "相同条件", "transfer_limits": ["不可迁移数字"], "basis_refs": [], "status": "candidate"},
        "representation": dict(target=r, slot="boundary", text="合成适用边界", boundary_refs=[]),
        "policy": dict(mode="basic", overrides={"auto_summary": False, "retain": ["失败边界"]}),
        "consolidation": dict(basis_heads={}, trigger="结束", affected_refs=[], decisions=[], remaining_refs=[]),
        "feedback": dict(query_id="Q-example", target=r, label="missing", note="", adopted_in=None),
        "review": dict(target_claim_id="CLM-example", target_content_hash="a" * 64, state="not-reviewed",
                       reviewer=dict(kind="human", id="fixture"), reason="仅测试", evidence_refs=[], scope=None, replacement_claim_id=None),
    }


def draft(kind="event"):
    return dict(schema_version=2, owner_id="RES-example", kind=kind, title="中文🧪", body_markdown="第一行\n第二行",
                payload=copy.deepcopy(examples()[kind]), sources=[], provenance_gap="仅合成数据，无现实依据",
                record_reason="回归验证", discovery="owner_only", sensitivity="internal")


class MemoryContractsTests(unittest.TestCase):
    def test_all_fifteen_kinds_and_unknown_values(self):
        self.assertEqual(set(examples()), set(c.V2_LEVELS))
        for kind in examples():
            with self.subTest(kind=kind):
                original = draft(kind)
                result = c.validate_record(original, {"allow_review": True})
                self.assertTrue(result["valid"], result["errors"])
                self.assertEqual(result["record"]["level"], c.LEVELS[kind])
                self.assertEqual(result["record"]["body_markdown"], original["body_markdown"])
                self.assertNotIn("record_id", result["record"])
                self.assertNotIn("level", original)
                bad = copy.deepcopy(original)
                bad["payload"]["magic_score"] = 100
                self.assertFalse(c.validate_record(bad)["valid"])
        for reason in ("unknown", "not_acquired", "not_applicable"):
            value = draft()
            value["payload"]["observation"]["reason"] = reason
            result = c.validate_record(value)
            self.assertTrue(result["valid"])
            self.assertIsNone(result["record"]["payload"]["occurred_at"])

    def test_precise_missing_and_unknown_fields(self):
        for field in ("owner_id", "title", "payload", "record_reason"):
            value = draft(); del value[field]
            self.assertIn("/" + field, [e["path"] for e in c.validate_record(value)["errors"]])
        for field, value in (("level", "L4"), ("kind", "alien"), ("schema_version", True), ("kind", [])):
            record = draft(); record[field] = value
            self.assertFalse(c.validate_record(record)["valid"])
        value = draft(); value["payload"]["observation"] = ""
        self.assertFalse(c.validate_record(value)["valid"])

    def test_boundaries_and_reference_versions(self):
        for kind, field, bad in (("experience", "applicable", []), ("association", "shared_structure", None),
                                 ("association", "transfer_limits", []), ("route", "status", "blocked"),
                                 ("question", "status", "resolved")):
            value = draft(kind); value["payload"][field] = bad
            self.assertFalse(c.validate_record(value)["valid"])
        value = draft("source"); value["payload"]["source_ref"]["revision"] = None
        self.assertIn("/payload/source_ref/revision", [e["path"] for e in c.validate_record(value)["errors"]])
        result = c.validate_record(draft("source"), {"resolve_ref": lambda ref: None})
        self.assertEqual(result["errors"][0]["code"], "UNRESOLVED_REFERENCE")

    def test_verbatim_characters_and_lines(self):
        original = "首行🧪\n第二行\n"
        value = draft("source")
        value["payload"]["acquisition"] = "verbatim_export"
        value["payload"]["source_ref"]["locator"] = "lines:1-1"
        value["body_markdown"] = "首行🧪\n"
        context = {"read_source": lambda ref: original}
        self.assertTrue(c.validate_record(value, context)["valid"])
        value["payload"]["source_ref"]["locator"] = "chars:0-4"
        self.assertTrue(c.validate_record(value, context)["valid"])
        value["body_markdown"] = "归纳摘要"
        self.assertFalse(c.validate_record(value, context)["valid"])
        self.assertFalse(c.validate_record(value)["valid"])

    def test_hash_order_metadata_body_and_nonfinite(self):
        value = c.validate_record(draft())["record"]
        digest = c.content_hash(value)
        self.assertEqual(digest, c.content_hash(dict(reversed(list(value.items())))))
        self.assertEqual(digest, c.content_hash(dict(value, revision=9, updated_at="different", change_reason="audit")))
        self.assertNotEqual(digest, c.content_hash(dict(value, body_markdown="新正文🧪")))
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                c.canonical_hash({"nested": [bad]})
            record = draft(); record["payload"]["magic_score"] = bad
            self.assertFalse(c.validate_record(record)["valid"])

    def test_schema_subset_rejects_unknown_and_external_even_unselected(self):
        for schema in ({"type": "string", "pattern": ".*"}, {"$ref": "https://invalid/schema"},
                       {"oneOf": [{"type": "string"}, {"type": "object", "unevaluatedProperties": False}]}):
            with self.assertRaises(ValueError):
                c.validate_schema("valid text", schema)
        self.assertTrue(c.validate_schema(True, {"const": 1}))

    def test_request_temporary_refs_and_protected_server_fields(self):
        request = dict(schema_version=1, request_id="123", actor=dict(kind="ai", id="test"), owner_id="RES-example",
                       expected_head=None, operations=[dict(op="put_record", client_key="event", draft=draft())])
        request["operations"][0]["draft"]["sources"] = [{"client_key": "source", "relation": "input"}]
        self.assertTrue(c.validate_request(request)["valid"])
        for field in ("record_id", "revision", "record_hash", "created_by", "updated_at", "content_hash"):
            changed = copy.deepcopy(request); changed["operations"][0]["draft"][field] = "forged"
            self.assertFalse(c.validate_request(changed)["valid"])
        request["operations"][0]["op"] = "set_policy"
        self.assertFalse(c.validate_request(request)["valid"])
        self.assertFalse(c.validate_record(draft("review"))["valid"])

    def test_generated_structural_types_match_schema(self):
        output = SCHEMA_PATH.with_suffix("").with_suffix(".d.ts")
        self.assertEqual(output.read_text(encoding="utf-8"), generate(c.SCHEMA))
        self.assertIn("export type MemoryRecord", output.read_text(encoding="utf-8"))

    def test_schema_compositions_cannot_bypass_siblings(self):
        schema = {"$ref": "#/$defs/Text", "$defs": {"Text": {"type": "string"}}, "const": "required"}
        self.assertTrue(c.validate_schema("wrong", schema))
        self.assertFalse(c.validate_schema("required", schema))
        schema = {"oneOf": [{"type": "string"}, {"type": "integer"}], "const": "required"}
        self.assertTrue(c.validate_schema(1, schema))
        self.assertFalse(c.validate_schema("required", schema))
        malformed = [{"type": True}, {"type": []}, {"type": ["string", "string"]},
                     {"oneOf": []}, {"oneOf": {}}, {"minLength": True}, {"minItems": -1},
                     {"required": "name"}, {"required": ["name", "name"]}, {"properties": []},
                     {"items": False}, {"additionalProperties": 1}, {"enum": []}, {"enum": [1, 1]},
                     {"$ref": "#/$defs/Loop", "$defs": {"Loop": {"$ref": "#/$defs/Loop"}}}]
        for schema in malformed:
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                c.check_schema(schema)

    def test_reference_bool_identity_and_unresolved_slot(self):
        for revision in (True, False, 0, -1):
            value = draft("source"); value["payload"]["source_ref"]["revision"] = revision
            self.assertFalse(c.validate_record(value)["valid"])
        value = draft()
        value["payload"]["missing_refs"] = [{"requested_target": "MEM-lost", "reason": "未取得", "observed_at": "2026-01-01T00:00:00Z"}]
        def resolver(_):
            self.fail("An unresolved declaration must not be treated as valid evidence")
        self.assertTrue(c.validate_record(value, {"resolve_ref": resolver})["valid"])
        for identity in ("../MEM-file", "MEM-../escape", "wrong", "MEM-"):
            value = draft(); value["record_id"] = identity
            self.assertFalse(c.validate_record(value)["valid"])
        self.assertFalse(c.validate_record(draft("review"), {"allow_review": "false"})["valid"])

    def test_callback_domain_errors_preserved_and_generic_details_redacted(self):
        value = draft("source"); value["payload"]["acquisition"] = "verbatim_export"
        value["payload"]["source_ref"]["locator"] = "chars:0-1"
        for code in ("ACCESS_DENIED", "STALE_BASIS"):
            def failure(_):
                raise MemoryError(code, "safe domain message")
            with self.assertRaises(MemoryError) as caught:
                c.validate_record(value, {"read_source": failure})
            self.assertEqual(caught.exception.code, code)
            with self.assertRaises(MemoryError) as caught:
                c.validate_record(draft("source"), {"resolve_ref": failure})
            self.assertEqual(caught.exception.code, code)
        for exception in (ValueError, LookupError, OSError):
            def failure(_):
                raise exception("PRIVATE ORIGINAL EXCERPT")
            result = c.validate_record(value, {"read_source": failure})
            self.assertFalse(result["valid"])
            self.assertNotIn("PRIVATE", str(result))
        for value in ({1: "coerced"}, ("coerced",)):
            with self.assertRaises(ValueError):
                c.canonical_hash(value)


if __name__ == "__main__":
    unittest.main()
