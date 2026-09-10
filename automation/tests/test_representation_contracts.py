"""P0：实际材料查询解析器、表示注册表、预算账本与生成器的运行验证。

样本均为独立合成 DTO，不读取业务材料。测试运行 parse、Ledger 和生成器，
不把设计文件能导入、注解存在或人工标注当作查询/AI/浏览器验收。
Q 编号只指本文件覆盖的契约片段，完整集成覆盖见样本 README。
"""
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, fields, replace
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


REPOSITORY = Path(__file__).resolve().parents[2]
SCRIPTS = REPOSITORY / "automation" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from material_query import contracts as c, definitions, generate_types, legacy_adapter
from material_query.budget import DEFAULT_BUDGET, SERVER_LIMITS, Ledger, check_limits
from material_query.validation import QueryError, object_fields, parse
from memory.errors import MemoryError


SAMPLES = Path(__file__).resolve().parent / "fixtures" / "material-query"
REPRESENTATIONS = {"original", "full", "section", "unit_digest", "topic", "domain"}
RESULT_STATES = {"ok", "partial", "rejected", "cancelled", "failed"}


def samples(name):
    """每次读取新 JSON 对象，负例变换不能污染后续正例。"""
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def query_sample():
    return next(row["input"] for row in samples("query-valid.json") if row["id"] == "query-unit_digest")


class RepresentationContractTests(unittest.TestCase):
    def test_basis_observation_is_stable_for_same_observation_and_changes_with_refs(self):
        from material_query.wire import observe_basis
        original = {"refs": [], "owner_heads": [["A", "commit-1"]], "index_watermarks": [], "consistency": "fixed_refs"}
        stamped = observe_basis(original)
        self.assertTrue(stamped["observed_at"].endswith("Z"))
        self.assertTrue(stamped["basis_id"].startswith("BASIS-"))
        self.assertEqual(stamped, observe_basis(stamped))
        changed = observe_basis({**stamped, "owner_heads": [["A", "commit-2"]]})
        self.assertNotEqual(stamped["basis_id"], changed["basis_id"])
        self.assertEqual(stamped["observed_at"], changed["observed_at"])
        self.assertNotIn("basis_id", original)
        parse(stamped, c.Basis)

    def test_structured_issue_retries_and_never_discloses_unobserved_refs(self):
        from material_query.coordinator import failure
        ref = c.FixedRef("record", "MEM-observed", 1, "a" * 64, None)
        hidden = c.FixedRef("record", "MEM-private", 1, "b" * 64, None)
        basis = {"refs": [asdict(ref)], "owner_heads": [], "index_watermarks": [], "consistency": "fixed_refs"}
        result = failure(QueryError("STALE", "版本已变更", affected_refs=(ref, hidden)), basis=basis)
        self.assertEqual(result["issues"][0]["affected_refs"], [asdict(ref)])
        self.assertEqual(result["issues"][0]["retry"], "replan")
        parse(result, c.Result[c.SearchReceipt])
        denied = failure(QueryError("DENIED", "访问被拒绝", affected_refs=(hidden,)))
        self.assertNotIn("MEM-private", json.dumps(denied))
        self.assertEqual(denied["issues"][0]["retry"], "after_external_change")
        for code, retry in (("BUDGET", "replan"), ("EXPIRED", "replan"), ("RUNNING", "same_request"), ("VALIDATION", "never")):
            self.assertEqual(failure(QueryError(code, code))["issues"][0]["retry"], retry)

    def assert_code(self, code, action):
        with self.assertRaises(QueryError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_q01_q02_definitions_are_six_pure_registered_types(self):
        # 列定义不需要材料库，也不应偷偷打开来源或数据库。
        with patch.object(Path, "open", side_effect=AssertionError("definition listing opened a file")):
            values = definitions.listing()
            self.assertEqual({item["ref"]["key"] for item in values}, REPRESENTATIONS)
            for key in sorted(REPRESENTATIONS):
                value = definitions.get(c.DefinitionRef(key, definitions.VERSION))
                self.assertEqual(value.ref.key, key)
                self.assertTrue(value.rules)
                self.assertTrue(value.output_sections)
        for key, version in (("unregistered", definitions.VERSION), ("full", "unknown-version"), ("full", "")):
            with self.subTest(key=key, version=version):
                self.assert_code("UNSUPPORTED", lambda: definitions.get(c.DefinitionRef(key, version)))

    def test_q72_positive_query_samples_parse_six_actual_immutable_types(self):
        values = samples("query-valid.json")
        self.assertEqual({row["input"]["definition"]["key"] for row in values}, REPRESENTATIONS)
        for row in values:
            with self.subTest(case=row["id"]):
                value = parse(row["input"], c.QueryRequest)
                self.assertIsInstance(value, c.QueryRequest)
                self.assertIsInstance(value.scope, c.Scope)
                self.assertIsInstance(value.budget, c.Budget)
                self.assertIsInstance(value.keywords, tuple)
                self.assertEqual(definitions.get(value.definition).ref, value.definition)
                # 验证真实 frozen 对象，而不只检查类型注解里有没有 frozen=True。
                with self.assertRaises(FrozenInstanceError):
                    value.question = "不能原地改变已解析请求"

    def test_q05_q68_negative_query_samples_reject_unknown_fields_and_bad_values(self):
        for row in samples("query-invalid.json"):
            with self.subTest(case=row["id"]):
                error = self.assert_code(row["expected_code"], lambda: parse(row["input"], c.QueryRequest))
                self.assertTrue(error.fields)
                self.assertNotIn("UNTRUSTED_CLIENT_CONTEXT", str(error))

    def test_q06_scope_null_and_empty_arrays_remain_distinct(self):
        # 本测试验证解析后不扩大范围；授权交集与实际空结果由查询集成测试负责。
        dimensions = ("owner_ids", "levels", "kinds", "roles", "outcomes", "review_states",
                      "validities", "source_ids", "confidence_levels")
        for dimension in dimensions:
            for raw, expected in ((None, None), ([], ())):
                with self.subTest(dimension=dimension, value=raw):
                    value = query_sample()
                    value["scope"][dimension] = raw
                    parsed = parse(value, c.QueryRequest)
                    self.assertEqual(getattr(parsed.scope, dimension), expected)
        value = query_sample()
        value["scope"].update(owner_ids=["RES-MQ-A"], excluded_owner_ids=["RES-MQ-A"])
        parsed = parse(value, c.QueryRequest)
        self.assertEqual(parsed.scope.owner_ids, ("RES-MQ-A",))
        self.assertEqual(parsed.scope.excluded_owner_ids, ("RES-MQ-A",))

    def test_q09_rfc3339_time_windows_validate_offsets_and_order(self):
        valid = {"field": "recorded_at", "start_inclusive": "2026-09-10T08:00:00+08:00",
                 "end_exclusive": "2026-09-10T01:00:00Z"}
        window = parse(valid, c.TimeWindow)
        self.assertEqual(window.start_inclusive, valid["start_inclusive"])
        invalid_times = ("2026-09-10T00:00:00", "2026-09-10 00:00:00+00:00",
                         "2026-09-10T00:00:00+0000", "2026-13-10T00:00:00Z", "not-a-time")
        for raw in invalid_times:
            with self.subTest(raw=raw):
                self.assert_code("VALIDATION", lambda: parse({**valid, "start_inclusive": raw}, c.TimeWindow))
                request = query_sample()
                request["scope"]["recorded_from"] = raw
                self.assert_code("VALIDATION", lambda: parse(request, c.QueryRequest))
        # 以 UTC 比较边界，不能用字符串大小比较不同时区。
        for end in ("2026-09-10T00:00:00Z", "2026-09-09T23:59:59Z"):
            with self.subTest(end=end):
                self.assert_code("VALIDATION", lambda: parse({**valid, "end_exclusive": end}, c.TimeWindow))
        self.assertIsNone(parse({**valid, "start_inclusive": None, "end_exclusive": None}, c.TimeWindow).start_inclusive)

    def test_q23_q68_numbers_distinguish_bool_nonfinite_and_server_limits(self):
        base = asdict(DEFAULT_BUDGET)
        for field in fields(c.Budget):
            for invalid in (True, -1, 0.5):
                with self.subTest(field=field.name, invalid=invalid):
                    self.assert_code("VALIDATION", lambda: parse({**base, field.name: invalid}, c.Budget))
        zero = parse({key: 0 for key in base}, c.Budget)
        self.assertTrue(all(value == 0 for value in asdict(zero).values()))
        check_limits(SERVER_LIMITS)
        self.assert_code("VALIDATION", lambda: check_limits(replace(SERVER_LIMITS, read_bytes=SERVER_LIMITS.read_bytes + 1)))
        for share in (True, float("nan"), float("inf"), -0.01, 1.01):
            with self.subTest(share=share):
                request = query_sample()
                request["association"]["output_share"] = share
                self.assert_code("VALIDATION", lambda: parse(request, c.QueryRequest))
        for limit in (0, 101, True, 1.5):
            request = query_sample()
            request["result_limit"] = limit
            self.assert_code("VALIDATION", lambda: parse(request, c.QueryRequest))

    def test_q20_fixed_refs_cover_five_kinds_and_reject_unfixed_records(self):
        values = samples("fixed-refs.json")
        self.assertEqual({row["input"]["kind"] for row in values}, {"record", "file", "owner", "claim", "representation"})
        for row in values:
            with self.subTest(case=row["id"]):
                ref = parse(row["input"], c.FixedRef)
                self.assertEqual(asdict(ref), row["input"])
        record = values[0]["input"]
        changes = ({"id": " "}, {"kind": "url"}, {"revision": None}, {"revision": 0}, {"revision": -1},
                   {"revision": True}, {"revision": 1.0}, {"sha256": "a" * 63}, {"sha256": "A" * 64},
                   {"sha256": "g" * 64}, {"locator": {"path": "UNTRUSTED_LOCATOR"}})
        for change in changes:
            with self.subTest(change=change):
                self.assert_code("VALIDATION", lambda: parse({**record, **change}, c.FixedRef))
        representation = values[-1]["input"]
        self.assert_code("VALIDATION", lambda: parse({**representation, "revision": None}, c.FixedRef))

    def test_q66_legacy_refs_keep_identity_hash_and_edge_relation(self):
        for row in samples("fixed-refs.json"):
            value = parse(row["input"], c.FixedRef)
            legacy = legacy_adapter.to_legacy(value, relation="contradicts")
            restored, relation = legacy_adapter.from_legacy(legacy)
            with self.subTest(kind=value.kind):
                self.assertEqual(relation, "contradicts")
                self.assertEqual(restored.id, value.id)
                self.assertEqual(restored.revision, value.revision)
                self.assertEqual(restored.sha256, value.sha256)
                self.assertEqual(restored.kind, "record" if value.kind == "representation" else value.kind)
        original = {"record_id": "MEM-P0", "revision": 2, "record_hash": "a" * 64, "content_hash": "b" * 64}
        self.assertEqual(legacy_adapter.fixed_record(original).sha256, original["record_hash"])
        legacy = legacy_adapter.to_legacy(parse(samples("fixed-refs.json")[0]["input"], c.FixedRef))
        self.assert_code("VALIDATION", lambda: legacy_adapter.from_legacy({**legacy, "extra": True}))
        missing = deepcopy(legacy)
        del missing["relation"]
        self.assert_code("VALIDATION", lambda: legacy_adapter.from_legacy(missing))
        error = legacy_adapter.memory_error(MemoryError("ACCESS_DENIED", "PRIVATE_PATH_SENTINEL"))
        self.assertEqual(error.code, "DENIED")
        self.assertNotIn("PRIVATE_PATH_SENTINEL", str(error))
        self.assertEqual(error.fields, ())

    def test_q72_result_five_states_parse_with_bound_nested_value_type(self):
        rows = samples("result-valid.json")
        self.assertEqual({row["input"]["status"] for row in rows}, RESULT_STATES)
        for row in rows:
            with self.subTest(case=row["id"]):
                value = parse(row["input"], c.Result[c.SearchReceipt])
                self.assertIsInstance(value, c.Result)
                self.assertIsInstance(value.consumed, c.Budget)
                if value.value is not None:
                    self.assertIsInstance(value.value, c.SearchReceipt)
                    self.assertIsInstance(value.value.candidates[0], c.Candidate)
                    self.assertIsInstance(value.value.candidates[0].refs[0], c.FixedRef)
                    self.assertIsInstance(value.basis.owner_heads[0], tuple)

    def test_q72_result_negative_samples_reject_unknown_wrappers_and_untyped_values(self):
        rows = samples("result-invalid.json")
        self.assertEqual({row["input"]["status"] for row in rows}, RESULT_STATES)
        for row in rows:
            with self.subTest(case=row["id"]):
                self.assert_code(row["expected_code"], lambda: parse(row["input"], c.Result[c.SearchReceipt]))

    def test_q68_action_wrapper_rejects_context_injection_and_missing_fields(self):
        request = query_sample()
        value = {"request": request, "trace": False}
        self.assertIs(object_fields(value, ("request",), ("trace",)), value)
        invalid = ({}, [], {"request": request, "context": {"access_handle": "CLIENT_FORGED_AUTHORITY"}},
                   {"request": request, "unexpected": True})
        for wrapper in invalid:
            with self.subTest(wrapper_type=type(wrapper).__name__):
                error = self.assert_code("VALIDATION", lambda: object_fields(wrapper, ("request",), ("trace",)))
                self.assertNotIn("CLIENT_FORGED_AUTHORITY", str(error))


class FakeClock:
    """以纳秒保存可精确控制的测试进度；对 Ledger 暴露秒，不依赖真实 sleep。"""

    def __init__(self):
        self.nanoseconds = 0

    def __call__(self):
        return self.nanoseconds / 1_000_000_000

    def advance_ms(self, amount):
        self.nanoseconds += amount * 1_000_000


class BudgetLedgerTests(unittest.TestCase):
    def ledger(self, **limits):
        clock = FakeClock()
        return Ledger(replace(DEFAULT_BUDGET, **limits), clock=clock), clock

    def assert_code(self, code, action):
        with self.assertRaises(QueryError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def test_q23_resource_budget_zero_exact_and_one_over_preserve_consumption(self):
        for limit in (0, 4):
            with self.subTest(limit=limit):
                ledger, _clock = self.ledger(read_bytes=limit)
                ledger.charge("read_bytes", limit)
                self.assertEqual(ledger.snapshot()["read_bytes"], limit)
                self.assertEqual(ledger.remaining("read_bytes"), 0)
                self.assert_code("BUDGET", lambda: ledger.charge("read_bytes", 1))
                self.assertEqual(ledger.snapshot()["read_bytes"], limit)
        ledger, _clock = self.ledger()
        for amount in (True, -1, 0.5):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                ledger.charge("read_bytes", amount)

    def test_q71_waiting_is_free_but_distinct_active_stages_accumulate(self):
        ledger, clock = self.ledger(wall_ms=1000)
        clock.advance_ms(30000)  # 用户等待消耗查询 TTL，但不属于执行活动成本。
        self.assertEqual(ledger.snapshot()["wall_ms"], 0)
        with ledger.active():
            clock.advance_ms(125)
            ledger.charge("read_bytes", 3)
            self.assertEqual(ledger.snapshot()["wall_ms"], 125)
        clock.advance_ms(30000)
        with ledger.active():
            clock.advance_ms(375)
        self.assertEqual(ledger.snapshot()["wall_ms"], 500)
        self.assertEqual(ledger.snapshot()["read_bytes"], 3)

    def test_q71_submillisecond_stages_do_not_reset_fractional_elapsed_time(self):
        ledger, clock = self.ledger(wall_ms=1000)
        for _ in range(2):
            with ledger.active():
                clock.nanoseconds += 600_000  # 每次0.6ms；两次累计1.2ms，不能都截成0。
        self.assertGreaterEqual(ledger.snapshot()["wall_ms"], 1)

    def test_q71_overlapping_active_operations_conflict_without_losing_outer_cost(self):
        ledger, clock = self.ledger(wall_ms=1000)
        with ledger.active():
            clock.advance_ms(125)
            with self.assertRaises(QueryError) as caught:
                with ledger.active():
                    self.fail("同一账本不能同时进入另一个活动操作")
            self.assertEqual(caught.exception.code, "CONFLICT")
            clock.advance_ms(125)
        self.assertEqual(ledger.snapshot()["wall_ms"], 250)
        self.assertIsNone(ledger.active_started)

    def test_q23_deadline_exhaustion_reports_observed_cost_without_clamping(self):
        for limit, elapsed in ((0, 0), (250, 250), (250, 251)):
            with self.subTest(limit=limit, elapsed=elapsed):
                ledger, clock = self.ledger(wall_ms=limit)
                with self.assertRaises(QueryError) as caught:
                    with ledger.active():
                        clock.advance_ms(elapsed)
                self.assertEqual(caught.exception.code, "BUDGET")
                self.assertEqual(ledger.snapshot()["wall_ms"], elapsed)
                self.assertIsNone(ledger.active_started)

    def test_q28_cancellation_preserves_completed_cost_and_stops_next_charge(self):
        ledger, clock = self.ledger(wall_ms=1000)
        with self.assertRaises(QueryError) as caught:
            with ledger.active():
                ledger.charge("candidates", 2)
                clock.advance_ms(125)
                ledger.cancelled.set()
                ledger.checkpoint()
        self.assertEqual(caught.exception.code, "CANCELLED")
        self.assertEqual(ledger.snapshot()["candidates"], 2)
        self.assertEqual(ledger.snapshot()["wall_ms"], 125)
        self.assert_code("CANCELLED", lambda: ledger.charge("candidates", 1))
        self.assert_code("CANCELLED", ledger.checkpoint)
        self.assertEqual(ledger.snapshot()["candidates"], 2)


class GeneratedRepresentationContractTests(unittest.TestCase):
    def test_q72_runtime_generator_matches_current_json_and_typescript(self):
        schema_text, ts_text = generate_types.rendered()
        self.assertEqual(generate_types.rendered(), (schema_text, ts_text))
        self.assertEqual((REPOSITORY / "automation/schemas/material-query.schema.json").read_text(encoding="utf-8"), schema_text)
        self.assertEqual((REPOSITORY / "automation/frontend/src/generated/material-query.ts").read_text(encoding="utf-8"), ts_text)
        schema = json.loads(schema_text)
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["$defs"]["QueryRequest"]["additionalProperties"])
        self.assertIn("export interface Result<T", ts_text)
        # 具象响应的 value 不能退化为任意 JSON；不能只验证裸泛型 Result 的 {}。
        concrete = schema["$defs"]["Result_SearchReceipt"]
        self.assertIn("#/$defs/SearchReceipt", json.dumps(concrete["properties"]["value"]))
        self.assertFalse(concrete["additionalProperties"])

    def test_q72_check_mode_detects_drift_without_overwriting_outputs(self):
        rendered = generate_types.rendered()
        with tempfile.TemporaryDirectory(prefix="material-contract-drift-") as directory:
            automation = Path(directory) / "automation"
            outputs = (automation / "schemas/material-query.schema.json", automation / "frontend/src/generated/material-query.ts")
            for path, text in zip(outputs, rendered):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            # 只将生成器的输出根导向本测试新建的目录；真实受控文件保持只读。
            with patch.object(generate_types, "SCRIPTS", automation / "scripts"), \
                    patch.object(sys, "argv", ["generate_types.py", "--check"]):
                with redirect_stdout(io.StringIO()) as stream:
                    self.assertEqual(generate_types.main(), 0)
                self.assertEqual(json.loads(stream.getvalue())["status"], "passed")
                outputs[1].write_text("// injected synthetic drift\n", encoding="utf-8")
                before = [path.read_bytes() for path in outputs]
                with redirect_stdout(io.StringIO()) as stream:
                    self.assertEqual(generate_types.main(), 1)
                self.assertEqual(json.loads(stream.getvalue())["status"], "drift")
                self.assertEqual([path.read_bytes() for path in outputs], before)


if __name__ == "__main__":
    unittest.main()
