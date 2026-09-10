"""局部正式证据适配的真实 F1 回归，不把全库扫描/mock accepted 当作准入。"""
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from material_query_fixture import materialize, SCOPE
from material_query.budget import DEFAULT_BUDGET, Ledger
from material_query.contracts import FixedRef
from material_query.evidence import Evidence
from material_query.legacy_adapter import from_legacy
from material_query.reader import Reader
from material_query.validation import QueryError
from memory import index
from memory.contracts import canonical_hash
from memory.evidence_adapter import EvidenceAdapter


class MaterialEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.fx = materialize(Path(cls.temp.name) / "局部 证据 F1", isolation_root=cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def reader(self, *, budget=DEFAULT_BUDGET, access=None, excluded=()):
        return Reader(self.fx.root, Ledger(budget), access_owner_ids=access, excluded_ids=excluded)

    def assess(self, key="A.event", *, scope=SCOPE, reader=None):
        reader = reader or self.reader()
        with reader.ledger.active():
            return Evidence(reader).assess(self.fx.records[key], scope)

    def assert_code(self, code, action):
        with self.assertRaises(QueryError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def test_only_one_of_two_claims_is_effectively_accepted(self):
        states = {row["claim_id"]: row for row in self.assess()}
        accepted, unresolved = states[self.fx.claims["accepted"]], states[self.fx.claims["unreviewed"]]
        self.assertEqual(accepted["review_state"], "accepted")
        self.assertTrue(accepted["effective_validity"], accepted)
        self.assertEqual(unresolved["review_state"], "not-reviewed")
        self.assertFalse(unresolved["effective_validity"])
        self.assertEqual(accepted["owner_id"], self.fx.owner_ids["A"])
        claim = self.fx.records["A.event"]["payload"]["claims"][0]
        self.assertEqual(accepted["sha256"], canonical_hash(claim))

    def test_wrong_scope_changed_content_and_old_revision_are_ineligible(self):
        self.assertTrue(self.assess(scope=None)[0]["effective_validity"])
        self.assertFalse(any(row["effective_validity"] for row in self.assess(scope="synthetic:other")))
        for key in ("A.stale_event.r2", "A.stale_event.r1"):
            with self.subTest(key=key):
                states = self.assess(key)
                self.assertTrue(states)
                self.assertFalse(any(row["effective_validity"] for row in states))
        current = self.assess("A.stale_event.r2")[0]
        self.assertEqual(current["review_state"], "accepted")
        self.assertTrue(any(error["code"] == "STALE_BASIS" for error in current["errors"]))

    def test_retracted_and_superseded_reviews_remain_ineligible(self):
        states = {row["claim_id"]: row for row in self.assess("B.event")}
        for label in ("retracted", "superseded"):
            state = states[self.fx.claims[label]]
            self.assertEqual(state["review_state"], label)
            self.assertFalse(state["effective_validity"])

    def test_historical_claim_hash_resolves_without_revalidating_changed_claim(self):
        # The old statement is a real historical fixed reference. Reading it for
        # provenance must be possible, while its former accepted review cannot
        # authorize the changed current statement as formal evidence.
        from copy import deepcopy
        from memory.contracts import CONTENT_FIELDS
        source = self.fx.records["A.stale_event.r1"]
        draft = {key: deepcopy(source[key]) for key in (*CONTENT_FIELDS, "schema_version", "record_reason")}
        draft["payload"]["claims"][0]["claim_id"] = "CLM-MQ-HISTORICAL-STATEMENT"
        saved = self.fx.commit_draft("historical.claim.r1", draft)
        old = saved["payload"]["claims"][0]
        self.fx.review("historical.claim.review", "historical.claim.r1", old["claim_id"])
        changed = deepcopy(saved["payload"])
        changed["claims"][0]["statement"] = "SYNTHETIC ONLY：当前主张已经改变"
        self.fx.revise("historical.claim.r2", "historical.claim.r1", payload=changed)
        ref = FixedRef("claim", old["claim_id"], None, canonical_hash(old), None)
        reader = self.reader()
        with reader.ledger.active():
            review = reader.record(from_legacy(self.fx.ref("historical.claim.review"))[0])
            self.assertEqual(review["record_id"], self.fx.record_ids["historical.claim.review"])
            self.assert_code("STALE", lambda: Evidence(reader).project([ref], SCOPE))
        states = self.assess("historical.claim.r2")
        self.assertEqual(states[0]["review_state"], "accepted")
        self.assertFalse(states[0]["effective_validity"])

    def test_project_returns_only_accepted_statement_and_exact_claim_selection(self):
        ref, _ = from_legacy(self.fx.ref("A.event"))
        reader = self.reader()
        with reader.ledger.active():
            result = Evidence(reader).project([ref], SCOPE)
        self.assertEqual([row["claim_id"] for row in result["claims"]], [self.fx.claims["accepted"]])
        unreviewed = self.fx.records["A.event"]["payload"]["claims"][1]
        self.assertNotIn(unreviewed["statement"], result["text"])
        self.assertEqual(result["claims"][0]["text"], result["text"])
        fixed = FixedRef("claim", unreviewed["claim_id"], None, canonical_hash(unreviewed), None)
        reader = self.reader()
        with reader.ledger.active():
            result = Evidence(reader).project([fixed], SCOPE)
        self.assertEqual(result["claims"], [])
        self.assertEqual(result["text"], "")
        self.assertEqual(result["rejected"][0]["canonical_id"], fixed.id)

    def test_bad_fixed_claim_hash_and_legacy_owner_are_explicitly_rejected(self):
        cid = self.fx.claims["accepted"]
        self.assert_code("STALE", lambda: Evidence(self.reader()).project([FixedRef("claim", cid, None, "0" * 64, None)], SCOPE))
        self.assert_code("UNSUPPORTED", lambda: Evidence(self.reader()).project([
            FixedRef("owner", self.fx.owner_ids["A"], None, "0" * 64, None)], SCOPE))

    def test_does_not_construct_global_adapter_or_read_unrelated_record_bodies(self):
        reader = self.reader(access=[self.fx.owner_ids["A"]])
        opened = []
        original = reader.store.read_json

        def trace(path):
            if path.parent.name == "records":
                opened.append(path.stem)
            return original(path)

        with patch.object(EvidenceAdapter, "__init__", side_effect=AssertionError("global evidence scan")), \
                patch.object(reader.store, "read_json", side_effect=trace), \
                patch.object(reader, "file_bytes", wraps=reader.file_bytes) as read_source:
            states = self.assess(reader=reader)
        self.assertTrue(states[0]["effective_validity"])
        self.assertEqual(set(opened), {self.fx.record_ids["A.event"], self.fx.record_ids["A.review.accepted"]})
        self.assertEqual(read_source.call_count, 1, "共同原件在一次证据闭包中只哈希一次")
        self.assertEqual(read_source.call_args.args[0].id, self.fx.sources["A"]["source_id"])
        self.assertGreater(reader.ledger.snapshot()["graph_nodes"], 0)
        self.assertGreater(reader.ledger.snapshot()["graph_edges"], 0)

    def test_denied_owner_or_explicitly_excluded_source_cannot_supply_evidence(self):
        self.assert_code("DENIED", lambda: self.assess("B.event", reader=self.reader(access=[self.fx.owner_ids["A"]])))
        self.assert_code("DENIED", lambda: self.assess(reader=self.reader(excluded=[self.fx.sources["A"]["source_id"]])))

    def test_source_revocation_is_checked_on_next_operation(self):
        self.assertTrue(self.assess()[0]["effective_validity"])
        with self.fx.source_access("A", enabled=False):
            self.assert_code("DENIED", self.assess)
        self.assertTrue(self.assess()[0]["effective_validity"])

    def test_changed_original_bytes_invalidate_formal_claim_without_reindex(self):
        path = self.fx.root / self.fx.sources["A"]["path"]
        before = path.read_bytes()
        try:
            path.write_bytes(before + b"\nSYNTHETIC CHANGE\n")
            states = self.assess()
            self.assertFalse(any(row["effective_validity"] for row in states))
            self.assertTrue(any(error["code"] == "STALE" for row in states for error in row["errors"]))
        finally:
            path.write_bytes(before)

    def test_read_budget_zero_exact_and_one_less_than_measured_source_closure(self):
        measured_reader = self.reader()
        self.assertTrue(self.assess(reader=measured_reader)[0]["effective_validity"])
        measured = measured_reader.ledger.snapshot()["read_bytes"]
        self.assertGreater(measured, (self.fx.root / self.fx.sources["A"]["path"]).stat().st_size)
        exact = self.reader(budget=replace(DEFAULT_BUDGET, read_bytes=measured))
        self.assertTrue(self.assess(reader=exact)[0]["effective_validity"])
        self.assertEqual(exact.ledger.snapshot()["read_bytes"], measured)
        for limit in (0, measured - 1):
            limited = self.reader(budget=replace(DEFAULT_BUDGET, read_bytes=limit))
            self.assert_code("BUDGET", lambda: self.assess(reader=limited))
            self.assertLessEqual(limited.ledger.snapshot()["read_bytes"], limit)

    def test_zero_graph_budget_and_cancellation_stop_further_evidence_work(self):
        for field in ("graph_nodes", "graph_edges", "graph_hops"):
            reader = self.reader(budget=replace(DEFAULT_BUDGET, **{field: 0}))
            self.assert_code("BUDGET", lambda: self.assess(reader=reader))
        reader = self.reader()
        reader.ledger.cancelled.set()
        self.assert_code("CANCELLED", lambda: self.assess(reader=reader))
        self.assertEqual(reader.ledger.snapshot()["read_bytes"], 0)

    def test_binary_registered_evidence_is_hashed_without_text_decoding(self):
        path = self.fx.root / self.fx.sources["A"]["path"]
        before, binary = path.read_bytes(), b"\xff\x00\x81SYNTHETIC BINARY\xfe"
        try:
            path.write_bytes(binary)
            ref = dict(self.fx.source_ref("A"), sha256=hashlib.sha256(binary).hexdigest())
            reader = self.reader(budget=replace(DEFAULT_BUDGET, read_bytes=len(binary)))
            with reader.ledger.active():
                self.assertIsNone(Evidence(reader)._reference(ref))
            self.assertEqual(reader.ledger.snapshot()["read_bytes"], len(binary))
        finally:
            path.write_bytes(before)

    def test_lagging_index_cannot_hide_new_review(self):
        db = index.connect(self.fx.root, create=False)
        oid = self.fx.owner_ids["A"]
        before = db.execute("SELECT indexed_generation FROM memory_index_state WHERE owner_id=?", (oid,)).fetchone()[0]
        try:
            db.execute("UPDATE memory_index_state SET indexed_generation=indexed_generation-1 WHERE owner_id=?", (oid,))
            db.commit()
            self.assert_code("STALE", self.assess)
        finally:
            db.execute("UPDATE memory_index_state SET indexed_generation=? WHERE owner_id=?", (before, oid))
            db.commit()
            db.close()

    def test_navigation_association_cannot_project_endpoint_claims(self):
        ref, _ = from_legacy(self.fx.ref("edge.current"))
        reader = self.reader()
        with reader.ledger.active():
            result = Evidence(reader).project([ref], SCOPE)
        self.assertEqual(result["claims"], [])
        self.assertTrue(result["rejected"])

    def test_missing_review_index_row_with_current_watermark_is_not_unreviewed(self):
        db = index.connect(self.fx.root, create=False)
        rid = self.fx.record_ids["A.review.accepted"]
        before = dict(db.execute("SELECT * FROM memory_records WHERE canonical_id=?", (rid,)).fetchone())
        try:
            db.execute("DELETE FROM memory_records WHERE canonical_id=?", (rid,))
            db.commit()
            self.assert_code("STALE", self.assess)
        finally:
            columns = list(before)
            db.execute("INSERT INTO memory_records (" + ",".join(columns) + ") VALUES (" + ",".join("?" for _ in columns) + ")", list(before.values()))
            db.commit()
            db.close()


if __name__ == "__main__":
    unittest.main()
