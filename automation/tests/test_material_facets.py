"""C03: authored facets on real v3 commits, current reviews and material queries.

Only the owned F1 clone is used. All content/revisions/reviews go through public
memory dispatch; no test rewrites HEAD or substitutes an accepted evidence state.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from material_query_fixture import ACTOR, SCOPE, materialize
from material_query.budget import DEFAULT_BUDGET
from material_query.contracts import AssociationOptions, DefinitionRef, QueryRequest, Scope
from material_query.coordinator import Coordinator
from material_query.reader import MeteredStore
from material_query.wire import json_value
from memory import api, contracts, index
from memory.errors import MemoryError


class MaterialFacetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="material-facets-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.fx = materialize(Path(cls.temp.name) / "真实分类 中文 F1", isolation_root=cls.temp.name)
        cls.old = deepcopy(cls.fx.records["A.event"])
        cls.applicability = {"description": "prose-only is descriptive, not a condition label",
            "conditions": ["known-delay", "linear"], "exclusions": ["saturated"],
            "valid_from": "2026-09-01T00:00:00Z", "valid_until": "2026-10-01T00:00:00Z",
            "subject_versions": [cls.fx.ref("A.unit.r2")]}

        def confidence(claim, level):
            # The target is this exact, already committed claim. Fixed claim
            # hashes survive the metadata-only record revision; its new review
            # is still appended through the real review API below.
            target = {"target_kind": "claim", "target_id": claim["claim_id"], "revision": None,
                "sha256": contracts.canonical_hash(claim), "locator": "", "relation": "references"}
            return {"target": target, "level": level, "assessed_by": "SYNTHETIC-ONLY-facet-reviewer",
                "method": {"name": "synthetic-classification", "version": "1"},
                "basis": [cls.fx.source_ref("A", "references")], "applicability": deepcopy(cls.applicability),
                "calibrated_probability": 0.8 if level == "high" else None,
                "calibration_ref": cls.fx.source_ref("B", "references") if level == "high" else None}

        cls.facets = {"roles": ["experience", "method"], "principle_kind": None,
            "attempts": [{"attempt_ref": cls.fx.ref("A.event"), "outcome": "failure", "conditions": ["known-delay"]},
                         {"attempt_ref": cls.fx.ref("B.event"), "outcome": "success", "conditions": ["linear"]}],
            "applicability": deepcopy(cls.applicability), "counterexamples": [cls.fx.source_ref("B", "contradicts")],
            "confidence": [confidence(cls.old["payload"]["claims"][0], "high"),
                           confidence(cls.old["payload"]["claims"][1], "low")],
            "classification_basis": [cls.fx.source_ref("A", "references")]}
        payload = deepcopy(cls.old["payload"])
        payload["knowledge_facets"] = deepcopy(cls.facets)
        cls.record = cls.fx.revise("facets.event.r2", "A.event", payload=payload)
        cls.fx.review("facets.accepted.r2", "facets.event.r2", cls.fx.claims["accepted"])
        index.reconcile(cls.fx.root, vector="off")

    def setUp(self):
        self.app = Coordinator(self.fx.root)
        self.addCleanup(self.app.close)
        scope = Scope((self.fx.owner_ids["A"],), None, None, None, None, None, None,
                      False, (), (), None, None)
        ceiling = replace(scope, owner_ids=(self.fx.owner_ids["A"], self.fx.owner_ids["B"]))
        self.request = QueryRequest(DefinitionRef("full", "1"), self.record["record_id"], (),
            scope, ceiling, "exploration", AssociationOptions("off", "existing-relations", "1", 0, 0, None),
            replace(DEFAULT_BUDGET, read_bytes=28 * 1024 * 1024), "current", 10, "reject", (), "", channels=("identity",))

    def search(self, *, target=None, request=None, **filters):
        request = request or self.request
        request = replace(request, question=target or request.question, scope=replace(request.scope, **filters))
        result = self.app.search(json_value(request))
        self.assertIn(result["status"], {"ok", "partial"}, result)
        return result["value"]["candidates"]

    def validation_request(self, facets, *, version=3, creating=False):
        record = self.old if creating else self.record
        draft = {key: deepcopy(record[key]) for key in (*contracts.CONTENT_FIELDS, "schema_version", "record_reason")}
        draft["schema_version"] = version
        draft["level"] = "L1" if version == 1 else "L2"
        draft["payload"]["knowledge_facets"] = deepcopy(facets)
        operation = {"op": "put_record", "draft": draft}
        if creating:
            draft["payload"]["claims"] = []
            operation["client_key"] = "new-facet-draft"
        else:
            operation.update(record_id=record["record_id"], expected_revision=record["revision"])
            draft["change_reason"] = "SYNTHETIC ONLY validation boundary"
        return {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": ACTOR,
            "owner_id": record["owner_id"], "expected_head": self.fx.head("A"), "operations": [operation]}

    def test_public_roundtrip_preserves_multiple_attempts_confidence_and_old_revision(self):
        saved = self.fx.inspect("facets.event.r2")
        self.assertEqual(saved["payload"]["knowledge_facets"], self.facets)
        self.assertEqual([row["outcome"] for row in saved["payload"]["knowledge_facets"]["attempts"]], ["failure", "success"])
        old = self.fx.inspect("A.event")
        self.assertEqual(old, self.old)
        self.assertNotIn("knowledge_facets", old["payload"])
        self.assertEqual(old["record_hash"], self.old["record_hash"])
        self.assertEqual(contracts.content_hash(old), self.old["content_hash"])

    def test_role_multiple_outcomes_review_and_validity_intersect_independently(self):
        for role in ("experience", "method"):
            for outcome in ("failure", "success"):
                with self.subTest(role=role, outcome=outcome):
                    candidates = self.search(roles=(role,), outcomes=(outcome,), review_states=("accepted",), validities=("valid",))
                    self.assertEqual(len(candidates), 1)
                    self.assertEqual([ref["id"] for ref in candidates[0]["evaluated_claim_refs"]], [self.fx.claims["accepted"]])
        self.assertEqual(self.search(roles=("hypothesis",), outcomes=("failure",)), [])
        self.assertEqual(self.search(roles=("experience",), outcomes=("mixed",)), [])
        self.assertEqual(self.search(outcomes=("failure",), review_states=("retracted",)), [])
        self.assertEqual(self.search(outcomes=("failure",), review_states=("accepted",), validities=("invalid",)), [])

    def test_confidence_targets_exact_claim_and_never_promotes_review(self):
        accepted, unreviewed = self.fx.claims["accepted"], self.fx.claims["unreviewed"]
        good = self.search(target=accepted, confidence_levels=("high",), review_states=("accepted",), validities=("valid",))
        self.assertEqual(len(good), 1)
        self.assertEqual(self.search(target=unreviewed, confidence_levels=("high",)), [])
        self.assertEqual(self.search(target=unreviewed, confidence_levels=("high",), include_unknown=True), [])
        low = self.search(target=unreviewed, confidence_levels=("low",))
        self.assertEqual(len(low), 1)
        self.assertEqual(low[0]["evidence_status"], "not-reviewed")
        self.assertEqual(low[0]["evaluated_claim_refs"], [])
        self.assertEqual([ref["id"] for ref in low[0]["unresolved_claim_refs"]], [unreviewed])
        formal = replace(self.request, purpose="formal", applicability=SCOPE)
        self.assertEqual(self.search(target=unreviewed, request=formal, confidence_levels=("low",)), [])

    def test_unknown_is_explicit_and_empty_filters_never_become_unrestricted(self):
        # B.event contains the synthetic word SUCCESS, but has no authored
        # outcome classification. It must remain unknown, even after a real
        # review exists on one of its claims.
        target = self.fx.record_ids["B.event"]
        owners = (self.fx.owner_ids["B"],)
        self.assertEqual(self.search(target=target, owner_ids=owners, outcomes=("success",)), [])
        unknown_outcome = self.search(target=target, owner_ids=owners, outcomes=("success",), include_unknown=True)
        self.assertEqual(len(unknown_outcome), 1)
        self.assertEqual(unknown_outcome[0]["unknown_facets"], ["outcomes"])
        self.assertEqual(self.search(target=target, owner_ids=owners, roles=("experience",)), [])
        unknown_role = self.search(target=target, owner_ids=owners, roles=("experience",), include_unknown=True)
        self.assertEqual(len(unknown_role), 1)
        self.assertEqual(unknown_role[0]["unknown_facets"], ["roles"])
        self.assertEqual(self.search(target=target, owner_ids=owners, confidence_levels=("high",)), [])
        unknown_confidence = self.search(target=target, owner_ids=owners, confidence_levels=("high",), include_unknown=True)
        self.assertEqual(len(unknown_confidence), 1)
        self.assertEqual(unknown_confidence[0]["unknown_facets"], ["confidence"])
        for field in ("roles", "outcomes", "confidence_levels"):
            with self.subTest(field=field):
                self.assertEqual(self.search(include_unknown=True, **{field: ()}), [])
        self.assertEqual(self.search(outcomes=("mixed",), include_unknown=True), [], "known outcomes must not become unknown")

    def test_applicability_uses_exact_structured_conditions_and_exclusions(self):
        self.assertEqual(len(self.search(applicability_conditions=("known-delay",))), 1)
        self.assertEqual(self.search(applicability_conditions=("delay",)), [])
        self.assertEqual(self.search(applicability_conditions=("prose-only",)), [])
        self.assertEqual(self.search(applicability_conditions=("saturated",)), [])
        self.assertEqual(self.search(applicability_exclusions=("known-delay",)), [])
        self.assertEqual(len(self.search(applicability_conditions=("linear",), applicability_exclusions=("saturated",))), 1)

    def test_facet_basis_is_in_real_source_permission_and_revocation_closure(self):
        reads = []
        actual = MeteredStore._record

        def observed(store, owner, record_id, entry):
            reads.append(owner["owner_id"])
            return actual(store, owner, record_id, entry)

        narrowed = replace(self.request, scope_ceiling=replace(self.request.scope_ceiling, owner_ids=(self.fx.owner_ids["A"],)))
        with patch.object(MeteredStore, "_record", observed):
            self.assertEqual(self.search(request=narrowed, outcomes=("success",)), [])
        self.assertNotIn(self.fx.owner_ids["B"], reads, "outside facet dependencies must be denied before body IO")
        before = self.fx.head("A")
        with self.fx.source_access("B", enabled=False):
            self.assertEqual(self.search(outcomes=("success",)), [])
        self.assertEqual(self.fx.head("A"), before)

    def test_public_validation_rejects_unfixed_unbased_uncalibrated_and_invalid_facets(self):
        malformed = []
        for label in ("basis", "sha", "calibration", "probability", "dates", "conflict", "principle", "outcome"):
            value = deepcopy(self.facets)
            if label == "basis":
                value["classification_basis"] = []
            elif label == "sha":
                value["attempts"][0]["attempt_ref"]["sha256"] = None
            elif label == "calibration":
                value["confidence"][0]["calibration_ref"] = None
            elif label == "probability":
                value["confidence"][0]["calibrated_probability"] = 1.01
            elif label == "dates":
                value["applicability"]["valid_from"] = value["applicability"]["valid_until"]
            elif label == "conflict":
                value["applicability"]["exclusions"].append("linear")
            elif label == "principle":
                value["roles"].append("principle")
            else:
                value["attempts"][0]["outcome"] = "probably-success-from-title"
            malformed.append((label, value))
        before = self.fx.head("A")
        for label, value in malformed:
            with self.subTest(label=label), self.assertRaises(MemoryError) as caught:
                api.dispatch(self.fx.service, "validate-draft", self.validation_request(value))
            self.assertEqual(caught.exception.code, "INVALID_SCHEMA")
        self.assertEqual(self.fx.head("A"), before)

    def test_legacy_v1_v2_save_and_fixed_read_need_no_backfill_or_new_field(self):
        for version in (1, 2):
            with self.subTest(version=version):
                request = self.validation_request(self.facets, version=version, creating=True)
                with self.assertRaises(MemoryError):
                    api.dispatch(self.fx.service, "validate-draft", request)
                draft = request["operations"][0]["draft"]
                del draft["payload"]["knowledge_facets"]
                saved = self.fx.commit_draft("facets.legacy.v" + str(version), draft)
                reread = self.fx.inspect("facets.legacy.v" + str(version))
                self.assertEqual(reread, saved)
                self.assertEqual(saved["schema_version"], version)
                self.assertNotIn("knowledge_facets", saved["payload"])
                self.assertEqual(contracts.content_hash(reread), saved["content_hash"])


if __name__ == "__main__":
    unittest.main()
