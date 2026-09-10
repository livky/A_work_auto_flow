"""C24: a changed claim becomes eligible only after a real new review.

The complete save/revise/review/project chain uses an owned F1 workspace. It
preserves the historical review and checks current owner/scope authorization;
neither accepted state nor fixed hashes are patched into canonical storage.
"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import uuid

from material_query_fixture import ACTOR, SCOPE, materialize
from material_query.budget import DEFAULT_BUDGET, Ledger
from material_query.contracts import FixedRef
from material_query.evidence import Evidence
from material_query.legacy_adapter import from_legacy
from material_query.reader import Reader
from material_query.validation import QueryError
from memory import api, contracts
from memory.errors import MemoryError


class MaterialReviewInheritanceTests(unittest.TestCase):
    def test_new_review_revalidates_changed_claim_and_preserves_old_review_owner_scope(self):
        with tempfile.TemporaryDirectory(prefix="material-review-inheritance-") as boundary:
            fx = materialize(Path(boundary) / "新复核 中文 F1", isolation_root=boundary)
            template = fx.records["A.stale_event.r1"]
            draft = {name: deepcopy(template[name]) for name in
                     (*contracts.CONTENT_FIELDS, "schema_version", "record_reason")}
            cid = "CLM-MQ-NEW-REVIEW-INHERITANCE"
            draft["payload"]["claims"][0]["claim_id"] = cid
            first = fx.commit_draft("review.inheritance.r1", draft)
            old_claim = deepcopy(first["payload"]["claims"][0])
            old_review = fx.review("review.inheritance.accepted.r1", "review.inheritance.r1", cid)
            old_review_ref = from_legacy(fx.ref("review.inheritance.accepted.r1"))[0]

            def reader(*, access=None):
                return Reader(fx.root, Ledger(DEFAULT_BUDGET), access_owner_ids=access)

            def project(ref, scope=SCOPE, *, access=None):
                current = reader(access=access)
                with current.ledger.active():
                    return Evidence(current).project([ref], scope)

            old_ref = FixedRef("claim", cid, None, contracts.canonical_hash(old_claim), None)
            self.assertEqual([row["claim_id"] for row in project(old_ref)["claims"]], [cid])

            # Keep the claim identity and its declared applicability but change
            # the actual statement. The old accepted review remains history;
            # neither its claim hash nor its record content hash can authorize
            # the changed bytes before an explicit new review is committed.
            changed = deepcopy(first["payload"])
            changed["claims"][0]["statement"] = "SYNTHETIC ONLY 新正文：需要重新检查输入并重新复核"
            second = fx.revise("review.inheritance.r2", "review.inheritance.r1", payload=changed)
            new_claim = second["payload"]["claims"][0]
            new_ref = FixedRef("claim", cid, None, contracts.canonical_hash(new_claim), None)
            self.assertNotEqual(old_ref.sha256, new_ref.sha256)
            self.assertNotEqual(first["content_hash"], second["content_hash"])
            before_review = project(new_ref)
            self.assertEqual(before_review["claims"], [])
            self.assertTrue(before_review["rejected"])
            current = reader()
            with current.ledger.active():
                state = Evidence(current).assess(second, SCOPE)[0]
            self.assertEqual(state["review_state"], "accepted")
            self.assertFalse(state["effective_validity"])

            def request(**changes):
                value = {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": ACTOR,
                    "owner_id": second["owner_id"], "expected_head": fx.head("A"),
                    "target_claim_id": cid, "expected_content_hash": second["content_hash"],
                    "state": "accepted", "scope": SCOPE,
                    "reason": "SYNTHETIC ONLY C24 新正文按原适用域重新复核；不代表现实科学验证",
                    "evidence_refs": deepcopy(new_claim["evidence_refs"]), "replacement_claim_id": None}
                value.update(changes)
                return value

            heads = (fx.head("A"), fx.head("B"))
            # Wrong ownership, a different scientific scope, the former content
            # hash, and absent inputs cannot be borrowed into the new review.
            invalid = (("owner", {"owner_id": fx.owner_ids["B"], "expected_head": fx.head("B")},
                        {"INVALID_SCHEMA", "VERSION_CONFLICT"}),
                       ("scope", {"scope": "synthetic:unrelated"}, {"EVIDENCE_INELIGIBLE"}),
                       ("old_hash", {"expected_content_hash": first["content_hash"]}, {"STALE_BASIS"}),
                       ("inputs", {"evidence_refs": []}, {"EVIDENCE_INELIGIBLE"}))
            for label, changes, expected in invalid:
                with self.subTest(rejected=label), self.assertRaises(MemoryError) as caught:
                    api.dispatch(fx.service, "review", request(**changes))
                self.assertIn(caught.exception.code, expected)
                self.assertEqual((fx.head("A"), fx.head("B")), heads)

            # The successful public review binds the new record fingerprint and
            # the new claim SHA, with the actual fixed inputs and same scope.
            review_request = request()
            receipt = api.dispatch(fx.service, "review", review_request)
            self.assertEqual(receipt["save_status"], "committed")
            result_ref = receipt["record_results"][0]
            new_review = api.dispatch(fx.service, "inspect", {"owner_id": second["owner_id"],
                "record_id": result_ref["record_id"], "revision": result_ref["revision"]})["record"]
            self.assertEqual(new_review["record_id"], old_review["record_id"])
            self.assertEqual(new_review["revision"], old_review["revision"] + 1)
            self.assertEqual(new_review["payload"]["target_content_hash"], second["content_hash"])
            self.assertEqual(new_review["payload"]["scope"], SCOPE)
            self.assertEqual(new_review["payload"]["evidence_refs"], new_claim["evidence_refs"])
            bindings = [ref for ref in new_review["sources"] if ref["target_kind"] == "claim"]
            self.assertEqual([ref["sha256"] for ref in bindings], [new_ref.sha256])

            formal = project(new_ref)
            self.assertEqual(formal["rejected"], [])
            self.assertEqual([row["claim_id"] for row in formal["claims"]], [cid])
            self.assertEqual(formal["text"], new_claim["statement"])
            self.assertTrue(formal["claims"][0]["effective_validity"])
            self.assertEqual(project(new_ref, "synthetic:unrelated")["claims"], [])
            with self.assertRaises(QueryError) as denied:
                project(new_ref, access=[fx.owner_ids["B"]])
            self.assertEqual(denied.exception.code, "DENIED")
            with self.assertRaises(QueryError) as stale:
                project(old_ref)
            self.assertEqual(stale.exception.code, "STALE")

            # Fixed historical reads retain the old review and original claim
            # record exactly, after the new review has already been admitted.
            history_reader = reader()
            with history_reader.ledger.active():
                historical = history_reader.record(old_review_ref)
            self.assertEqual(historical, old_review)
            self.assertEqual(fx.inspect("review.inheritance.r1"), first)
            self.assertEqual(fx.inspect("review.inheritance.accepted.r1"), old_review)


if __name__ == "__main__":
    unittest.main()
