"""实际共享账本的预约/结算回归：竞争、父子计量、清账与活动墙钟。"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from material_query.budget import DEFAULT_BUDGET, Ledger
from material_query.validation import QueryError


class MaterialBudgetReservationTests(unittest.TestCase):
    def ledger(self, **limits):
        return Ledger(replace(DEFAULT_BUDGET, read_bytes=100, candidates=10, **limits))

    def assert_code(self, code, callback):
        with self.assertRaises(QueryError) as captured:
            callback()
        self.assertEqual(captured.exception.code, code)

    def assert_model_dimension_exhausts_first(self, first):
        """Exercise each model resource independently, including its zero case.

        These are real shared-ledger reservations/charges, not a tokenizer or
        model execution. All other resource limits retain spare capacity so the
        test cannot accidentally pass because an unrelated counter is zero.
        """
        dimensions = ("model_calls", "model_input_tokens", "model_output_tokens", "model_tokens")
        for limit in (0, 2):
            with self.subTest(first=first, limit=limit):
                limits = {key: 20 for key in dimensions}
                limits[first] = limit
                ledger = self.ledger(**limits)
                too_large = {key: 1 for key in dimensions}
                too_large[first] = limit + 1
                self.assert_code("BUDGET", lambda: ledger.reserve(too_large))
                self.assertTrue(all(ledger.snapshot()[key] == 0 for key in dimensions))
                costs = {key: 1 for key in dimensions}
                costs[first] = limit
                token = ledger.reserve(costs)
                with ledger.provider(token):
                    for key, amount in costs.items():
                        ledger.charge(key, amount)
                settled = ledger.settle(token, costs)
                self.assertEqual({key: ledger.snapshot()[key] for key in dimensions}, costs)
                self.assertEqual(ledger.settle(token, costs), settled)
                self.assertEqual(ledger.remaining(first), 0)
                self.assertTrue(all(ledger.remaining(key) > 0 for key in dimensions if key != first))
                self.assert_code("BUDGET", lambda: ledger.reserve({first: 1}))

    def test_model_input_limit_can_exhaust_before_output_calls_and_total(self):
        self.assert_model_dimension_exhausts_first("model_input_tokens")

    def test_model_output_limit_can_exhaust_before_input_calls_and_total(self):
        self.assert_model_dimension_exhausts_first("model_output_tokens")

    def test_model_call_limit_can_exhaust_before_input_output_and_total(self):
        self.assert_model_dimension_exhausts_first("model_calls")

    def test_model_total_limit_can_exhaust_before_input_output_and_calls(self):
        self.assert_model_dimension_exhausts_first("model_tokens")

    def test_competing_providers_cannot_reserve_same_remaining_capacity(self):
        ledger, barrier = self.ledger(), threading.Barrier(2)
        def request():
            barrier.wait(timeout=2)
            try:
                return ledger.reserve({"read_bytes": 70})
            except QueryError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(request) for _ in range(2)]
            results = [future.result(timeout=3) for future in pending]
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertIn("BUDGET", results)
        self.assertEqual(ledger.remaining("read_bytes"), 30)
        self.assertEqual(ledger.snapshot()["read_bytes"], 0)

    def test_unreserved_work_cannot_take_another_provider_hold(self):
        ledger = self.ledger()
        reservation = ledger.reserve({"read_bytes": 80})
        ledger.charge("read_bytes", 20)
        self.assert_code("BUDGET", lambda: ledger.charge("read_bytes", 1))
        ledger.charge("read_bytes", 40, reservation=reservation)
        receipt = ledger.settle(reservation, {"read_bytes": 40})
        self.assertEqual(receipt["released"]["read_bytes"], 40)
        self.assertEqual(ledger.snapshot()["read_bytes"], 60)
        self.assertEqual(ledger.remaining("read_bytes"), 40)

    def test_parent_settlement_does_not_repeat_child_charges(self):
        ledger = self.ledger()
        reservation = ledger.reserve({"read_bytes": 80, "candidates": 3})
        with ledger.provider(reservation):
            ledger.charge("read_bytes", 20)
            with ledger.provider(reservation):
                ledger.charge("read_bytes", 15)
                ledger.charge("candidates", 1)
            self.assert_code("CONFLICT", lambda: ledger.reserve({"read_bytes": 1}))
        first = ledger.settle(reservation, {"read_bytes": 35, "candidates": 1})
        second = ledger.settle(reservation, {"read_bytes": 35, "candidates": 1})
        self.assertEqual(first, second)
        self.assertEqual(ledger.snapshot()["read_bytes"], 35)
        self.assertEqual(ledger.snapshot()["candidates"], 1)
        self.assert_code("CONFLICT", lambda: ledger.settle(reservation, {"read_bytes": 36, "candidates": 1}))

    def test_reservation_identity_and_ceiling_are_bound_to_original_ledger(self):
        ledger, other = self.ledger(), self.ledger()
        reservation = ledger.reserve({"read_bytes": 60})
        self.assert_code("DENIED", lambda: other.settle(reservation, {}))
        forged = deepcopy(reservation)
        forged["ceiling"]["read_bytes"] = 90
        self.assert_code("CONFLICT", lambda: ledger.settle(forged, {}))
        self.assertEqual(ledger.remaining("read_bytes"), 40)

    def test_zero_usage_releases_unused_hold(self):
        ledger = self.ledger()
        reservation = ledger.reserve({"read_bytes": 100})
        self.assertEqual(ledger.remaining("read_bytes"), 0)
        receipt = ledger.settle(reservation, {})
        self.assertEqual(receipt["actual"]["read_bytes"], 0)
        self.assertEqual(ledger.remaining("read_bytes"), 100)

    def test_provider_over_ceiling_is_rejected_before_next_unit_of_work(self):
        ledger = self.ledger()
        reservation = ledger.reserve({"read_bytes": 50})
        with ledger.provider(reservation):
            ledger.charge("read_bytes", 40)
            self.assert_code("BUDGET", lambda: ledger.charge("read_bytes", 11))
        ledger.settle(reservation, {"read_bytes": 40})
        self.assertEqual(ledger.snapshot()["read_bytes"], 40)

    def test_settlement_cannot_understate_already_observed_usage(self):
        ledger = self.ledger()
        reservation = ledger.reserve({"read_bytes": 50})
        ledger.charge("read_bytes", 30, reservation=reservation)
        self.assert_code("CONFLICT", lambda: ledger.settle(reservation, {"read_bytes": 29}))
        self.assertEqual(ledger.held["read_bytes"], 20)
        ledger.settle(reservation, {"read_bytes": 30})
        self.assertEqual(ledger.held["read_bytes"], 0)

    def test_external_overrun_is_recorded_and_stops_new_work(self):
        ledger = self.ledger()
        reservation = ledger.reserve({"read_bytes": 50})
        receipt = ledger.settle(reservation, {"read_bytes": 120})
        self.assertTrue(receipt["overrun"])
        self.assertEqual(ledger.snapshot()["read_bytes"], 120)
        self.assertEqual(ledger.remaining("read_bytes"), 0)
        self.assert_code("BUDGET", lambda: ledger.reserve({"candidates": 1}))
        self.assertEqual(ledger.settle(reservation, {"read_bytes": 120}), receipt)

    def test_cancelled_provider_can_still_settle_actual_cost(self):
        ledger = self.ledger()
        reservation = ledger.reserve({"read_bytes": 60})
        ledger.charge("read_bytes", 15, reservation=reservation)
        ledger.cancelled.set()
        self.assert_code("CANCELLED", lambda: ledger.reserve({}))
        with ledger.active(cleanup=True):
            receipt = ledger.settle(reservation, {"read_bytes": 15})
        self.assertFalse(receipt["overrun"])
        self.assertEqual(ledger.held["read_bytes"], 0)
        self.assertEqual(ledger.snapshot()["read_bytes"], 15)

    def test_parallel_provider_wall_cost_is_one_observed_active_interval(self):
        now = [0.0]
        ledger = Ledger(replace(DEFAULT_BUDGET, wall_ms=10000, read_bytes=100), clock=lambda: now[0])
        start, release = threading.Barrier(3), threading.Event()
        first, second = ledger.reserve({"read_bytes": 20}), ledger.reserve({"read_bytes": 20})
        def provider(token):
            with ledger.provider(token):
                start.wait(timeout=2)
                release.wait(timeout=2)
                ledger.charge("read_bytes", 10)
            return ledger.settle(token, {"read_bytes": 10})
        with ledger.active():
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(provider, token) for token in (first, second)]
                start.wait(timeout=2)
                now[0] = 1.0
                release.set()
                for job in jobs:
                    self.assertFalse(job.result(timeout=3)["overrun"])
        self.assertEqual(ledger.snapshot()["wall_ms"], 1000)
        self.assertEqual(ledger.snapshot()["read_bytes"], 20)
        now[0] = 9.0  # Human waiting is TTL time, not active execution cost.
        self.assertEqual(ledger.snapshot()["wall_ms"], 1000)

    def test_invalid_units_and_settled_provider_reuse_are_rejected(self):
        ledger = self.ledger()
        for costs in ({"read_bytes": True}, {"read_bytes": -1}, {"invented": 1}):
            self.assert_code("VALIDATION", lambda costs=costs: ledger.reserve(costs))
        reservation = ledger.reserve({"read_bytes": 10})
        ledger.settle(reservation, {})
        self.assert_code("CONFLICT", lambda: ledger.charge("read_bytes", 1, reservation=reservation))


if __name__ == "__main__":
    unittest.main()
