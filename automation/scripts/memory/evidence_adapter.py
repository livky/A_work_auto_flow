"""Current-source evidence projection for legacy and immutable memory claims.

The adapter does not write reviews or alter Run execution status. The service
owns the trusted review transaction; prepare_review builds its validated input.
Formal reads instantiate a fresh adapter instead of trusting a search cache.
"""
from collections import deque
from copy import deepcopy
import hashlib
import json

import evidence as legacy
from . import contracts, owners
from .errors import MemoryError

DEPENDENT = {"supports", "input"}
STATES = {"not-reviewed", "accepted", "disputed", "retracted", "superseded"}


def iter_refs(value):
    """Yield declared references only; unresolved descriptions grant no evidence."""
    if isinstance(value, dict):
        if "target_kind" in value:
            yield value
        else:
            for key, item in value.items():
                if key != "missing_refs":
                    yield from iter_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_refs(item)


def issue(code, target_id, message, path=None):
    return {"code": code, "target_id": target_id, "message": message,
            "path": path or [target_id]}


def legacy_ref(service, adapter, ref):
    """Translate declared legacy provenance using its original, fixed hash.

    Registry matching reads metadata only. The caller subsequently checks the
    resulting Ref through the same service permission and version gates used
    for a new record. Never replace a missing/old hash with current file bytes.
    """
    target, digest = ref.get('target') or ref.get('path'), ref.get('sha256')
    if not isinstance(target, str) or not isinstance(digest, str):
        raise MemoryError('UNRESOLVED_REFERENCE', '旧引用缺少固定目标或原始指纹')
    node = adapter.legacy.nodes.get(target)
    if node:
        return {'target_kind': 'claim' if node['kind'] == 'claim' else 'owner',
                'target_id': target, 'revision': None, 'sha256': digest,
                'locator': '', 'relation': ref.get('relation', 'references')}
    registry_path = owners.safe_path(service.root, 'retrieval/sources.json')
    try:
        registry = json.loads(registry_path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise MemoryError('UNRESOLVED_REFERENCE', '旧路径来源没有当前登记') from exc
    import retrieval
    requested = (service.root / target).absolute()
    matching = []
    for entry in registry.get('sources', []):
        candidate = (service.root / entry['path']).absolute()
        if candidate == requested:
            matching.append(entry.get('source_id') or entry.get('id') or retrieval.source_id(candidate.resolve()))
    if len(matching) != 1:
        raise MemoryError('UNRESOLVED_REFERENCE', '旧路径来源必须有唯一逐文件登记')
    return {'target_kind': 'file', 'target_id': matching[0], 'revision': None, 'sha256': digest,
            'locator': '', 'relation': ref.get('relation', 'references')}


class EvidenceAdapter:
    """A bounded-by-workspace, read-only snapshot with separate review identities."""
    def __init__(self, service, *, _owner_views=None):
        self.service, self.root = service, service.root
        self.legacy = legacy.EvidenceGraph(self.root)
        self.records, self.claims, self.reviews, self.source_heads = {}, {}, {}, {}
        self.owner_views = {}
        self.basis_checks = []
        # Legacy review fields intentionally do not change the old scientific
        # fingerprint. Bind their metadata bytes as well, so a withdrawal in
        # the prepare/publish window is still detected by the service.
        for node in self.legacy.nodes.values():
            if node["kind"] != "owner":
                continue
            path = owners.safe_path(self.root, node["path"].relative_to(self.root).as_posix())
            raw = path.read_bytes()
            if json.loads(raw.decode("utf-8-sig")) != node["raw"]:
                raise MemoryError("STALE_BASIS", "Legacy metadata changed while reading evidence")
            self.basis_checks.append({"kind": "legacy_file", "path": path.relative_to(self.root).as_posix(),
                                      "hash": hashlib.sha256(raw).hexdigest()})
        selected_owners = owners.list_owners(self.root) if _owner_views is None else list(_owner_views)
        if _owner_views is not None:
            # A request-local Catalog may supply its already validated owner
            # inventory. Recheck exact native bytes before reusing permission
            # fields; a second directory scan would not add a stronger check.
            directory_cache, fingerprints = {}, {}
            for owner in selected_owners:
                path = owners.safe_path(self.root, owner["native_ref"]["path"], _directory_cache=directory_cache)
                if path not in fingerprints:
                    fingerprints[path] = hashlib.sha256(path.read_bytes()).hexdigest()
                if fingerprints[path] != owner["fingerprint"]:
                    raise MemoryError("STALE_BASIS", "Native owner metadata changed during the request")
            owners._recheck_directory_cache(directory_cache)
        for owner in selected_owners:
            self.owner_views[owner["owner_id"]] = owner
            snapshot = service.store.read_snapshot(owner)
            self.source_heads[owner["owner_id"]] = snapshot["head"]
            self.basis_checks.append({"kind": "head", "owner_id": owner["owner_id"], "head": snapshot["head"]})
            for rid, record in snapshot["records"].items():
                if rid in self.records or rid in self.legacy.nodes:
                    raise MemoryError("INTEGRITY_ERROR", "Duplicate memory evidence identity", {"target_id": rid})
                self.records[rid] = record
                if record["kind"] in {"event", "narrative", "experience", "overview"}:
                    for claim in record["payload"].get("claims", []):
                        cid = claim["claim_id"]
                        if cid in self.claims or cid in self.legacy.nodes:
                            raise MemoryError("INTEGRITY_ERROR", "Duplicate claim identity", {"target_id": cid})
                        self.claims[cid] = (claim, record)
                elif record["kind"] == "review":
                    cid = record["payload"]["target_claim_id"]
                    if cid in self.reviews:
                        raise MemoryError("INTEGRITY_ERROR", "Multiple current review records for one claim", {"target_id": cid})
                    self.reviews[cid] = record

    def resolve_claim(self, claim_id):
        """Return current claim identity, never replace a caller's fixed hash."""
        if not isinstance(claim_id, str) or not claim_id:
            raise MemoryError("INVALID_SCHEMA", "Claim ID must be a nonempty string")
        if claim_id in self.claims:
            claim, record = self.claims[claim_id]
            sensitivity = record["sensitivity"]
            owner = self.owner_views.get(record["owner_id"])
            if owner:
                owners.require_readable_owner(owner)
            if sensitivity == "restricted":
                raise MemoryError("ACCESS_DENIED", "Claim is outside the readable scope")
            return {"sha256": contracts.canonical_hash(claim), "claim": deepcopy(claim),
                    "record": deepcopy(record), "owner_id": record["owner_id"], "sensitivity": sensitivity}
        node = self.legacy.nodes.get(claim_id)
        if not node or node["kind"] != "claim":
            raise MemoryError("UNRESOLVED_REFERENCE", "Claim identity does not exist", {"target_id": claim_id})
        parent = self.legacy.nodes.get(node["owner"], {})
        sensitivity = max((node["raw"].get("sensitivity", "internal"), parent.get("raw", {}).get("sensitivity", "internal")),
                          key=lambda value: {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}.get(value, 3))
        if sensitivity == "restricted":
            raise MemoryError("ACCESS_DENIED", "Claim is outside the readable scope")
        return {"sha256": node["fingerprint"], "claim": deepcopy(node["raw"]), "record": None,
                "owner_id": node["owner"], "sensitivity": sensitivity, "legacy": True}

    def _reference(self, ref):
        """Resolve a fixed reference and return its graph node, or an input leaf.

        Files are opened through the registered-source resolver. Current formal
        use rejects changed record revisions; history can still read them via
        store.read_record without silently upgrading their references.
        """
        errors = contracts.validate_schema(ref, contracts.SCHEMA["$defs"]["Ref"], contracts.SCHEMA["$defs"])
        errors += contracts.validate_references({"ref": ref}, {}) if not errors else []
        if errors:
            raise MemoryError("INVALID_SCHEMA", "Incomplete fixed evidence reference", errors=errors)
        target = ref["target_id"]
        if ref["target_kind"] == "record":
            record = self.records.get(target)
            if record is None:
                raise MemoryError("UNRESOLVED_REFERENCE", "Referenced memory record is missing", {"target_id": target})
            if record["sensitivity"] == "restricted":
                raise MemoryError("ACCESS_DENIED", "Referenced record is outside readable scope")
            # Record references pin the complete immutable revision, matching
            # commit and packet readers. content_hash is for scientific review
            # bindings and intentionally omits revision and audit metadata.
            if record["revision"] != ref["revision"] or (ref["sha256"] is not None and ref["sha256"] != record["record_hash"]):
                raise MemoryError("STALE_BASIS", "Referenced record content changed", {"target_id": target})
            return target
        if ref["target_kind"] == "claim":
            value = self.resolve_claim(target)
            if value["sha256"] != ref["sha256"]:
                raise MemoryError("STALE_BASIS", "Referenced claim content changed", {"target_id": target})
            self.basis_checks.append({"kind": "ref", "ref": deepcopy(ref), "hash": value["sha256"]})
            return target
        if ref["target_kind"] == "file":
            path, _metadata = self.service._file(ref)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != ref["sha256"]:
                raise MemoryError("STALE_BASIS", "Registered source bytes changed", {"target_id": target})
            self.basis_checks.append({"kind": "file", "ref": deepcopy(ref), "hash": actual})
            return None
        # The existing resolver retains legacy owner fingerprint and path rules.
        self.service._resolve_ref(ref, {}, self.basis_checks)
        return target

    def _review_errors(self, cid, claim, record, scope):
        review = self.reviews.get(cid)
        if review is None:
            return "not-reviewed", [issue("EVIDENCE_INELIGIBLE", cid, "Claim has not been reviewed")]
        p = review["payload"]
        state = p["state"]
        errors = []
        # The claim is fixed separately from the enclosing evidence content.
        # Adding checkpoint/policy records changes neither binding.
        claim_hash = contracts.canonical_hash(claim)
        bindings = [ref for ref in review["sources"] if ref.get("target_kind") == "claim" and ref.get("target_id") == cid]
        if p["target_content_hash"] != record["content_hash"] or len(bindings) != 1 or bindings[0].get("sha256") != claim_hash:
            errors.append(issue("STALE_BASIS", cid, "Review no longer matches claim or enclosing evidence content"))
        if state != "accepted":
            errors.append(issue("EVIDENCE_INELIGIBLE", cid, "Claim review state is " + state))
        if state == "accepted" and (not p["scope"] or p["scope"] != claim["scope"] or p["scope"] != scope):
            errors.append(issue("EVIDENCE_INELIGIBLE", cid, "Review scope does not match requested claim scope"))
        if state == "accepted" and not any(ref.get("relation") in DEPENDENT for ref in p["evidence_refs"]):
            errors.append(issue("EVIDENCE_INELIGIBLE", cid, "Review has no supporting evidence"))
        return state, errors

    def _analyze(self, target, scope=None, *, allow_decision=False):
        """Iterative graph evaluation: no recursion, no double-counted diamond leaf.

        The graph contains only supports/input for scientific eligibility.
        Navigation edges are handled separately by impact.reverse_dependencies.
        """
        queue, paths, deps, local = deque([target]), {target: [target]}, {}, {}
        while queue:
            current = queue.popleft()
            if current in deps:
                continue
            deps[current], local[current] = set(), []
            refs = []
            if current in self.claims:
                claim, record = self.claims[current]
                _state, failures = self._review_errors(current, claim, record, scope if current == target and scope is not None else claim["scope"])
                local[current].extend(failures)
                if record["sensitivity"] == "restricted":
                    local[current].append(issue("ACCESS_DENIED", current, "Claim is outside readable scope"))
                if not any(ref.get("relation") in DEPENDENT for ref in claim["evidence_refs"]):
                    local[current].append(issue("EVIDENCE_INELIGIBLE", current, "Claim has no supporting evidence"))
                refs = list(claim["evidence_refs"]) + list(record["sources"])
                if current in self.reviews:
                    refs += self.reviews[current]["payload"]["evidence_refs"]
            elif current in self.records:
                record = self.records[current]
                if record["sensitivity"] == "restricted":
                    local[current].append(issue("ACCESS_DENIED", current, "Record is outside readable scope"))
                refs = list(record["sources"])
                if record["kind"] == "source":
                    refs.append(dict(record["payload"]["source_ref"], relation="input"))
                elif record["kind"] in {"event", "narrative", "experience", "overview"}:
                    deps[current].update(claim["claim_id"] for claim in record["payload"]["claims"])
                    if not record["payload"]["claims"] and not (allow_decision and current == target):
                        local[current].append(issue("EVIDENCE_INELIGIBLE", current, "Narrative record contains no independently reviewable claims"))
                else:
                    refs += list(iter_refs(record["payload"]))
            elif current in self.legacy.nodes:
                node = self.legacy.nodes[current]
                try:
                    if node["kind"] == "claim":
                        self.resolve_claim(current)  # Preserve access checks.
                        failures = self.legacy.claim_errors(current, scope if current == target and scope is not None else node["raw"].get("scope"))
                    else:
                        failures = list(node["blockers"]) + list(node["issues"])
                        if node["raw"].get("review", {}).get("status") != "accepted":
                            failures.append("Legacy evidence owner is not accepted")
                        if node["raw"].get("run_id"):
                            failures += legacy.run_record_errors(self.root, node["raw"])
                            if node["raw"].get("status") != "succeeded" or node["raw"].get("finalization", {}).get("fingerprint") != node["fingerprint"]:
                                failures.append("Legacy Run is not succeeded and validly finalized")
                        deps[current].update(cid for cid, child in self.legacy.nodes.items() if child.get("owner") == current)
                    local[current].extend(issue("EVIDENCE_INELIGIBLE", current, text) for text in failures)
                except MemoryError as exc:
                    local[current].append(issue(exc.code, current, str(exc)))
            elif current in self.owner_views:
                deps[current].update(cid for cid, (_claim, record) in self.claims.items() if record["owner_id"] == current)
                if not deps[current]:
                    local[current].append(issue("EVIDENCE_INELIGIBLE", current, "Owner contains no independently reviewable claims"))
            else:
                local[current].append(issue("UNRESOLVED_REFERENCE", current, "Evidence target is missing"))
            for ref in refs:
                if ref.get("relation") not in DEPENDENT:
                    continue
                try:
                    dependency = self._reference(ref)
                    if dependency:
                        deps[current].add(dependency)
                except MemoryError as exc:
                    local[current].append(issue(exc.code, ref["target_id"], str(exc)))
                except OSError:
                    local[current].append(issue("UNRESOLVED_REFERENCE", ref["target_id"], "Evidence source could not be read"))
            for dependency in sorted(deps[current]):
                if dependency not in paths:
                    paths[dependency] = paths[current] + [dependency]
                if dependency not in deps:
                    queue.append(dependency)
        # Iteratively remove all acyclic leaves. Remaining nodes include cycles
        # and their consumers; they cannot become evidence by circular support.
        pending = {node: set(edges) for node, edges in deps.items()}
        while pending:
            leaves = {node for node, edges in pending.items() if not edges}
            if not leaves:
                break
            pending = {node: edges - leaves for node, edges in pending.items() if node not in leaves}
        for node in pending:
            local[node].append(issue("EVIDENCE_INELIGIBLE", node, "Supporting evidence contains a dependency cycle"))
        output, seen = [], set()
        for node in sorted(local):
            for failure in local[node]:
                key = (failure["code"], failure["target_id"], failure["message"])
                if key in seen:
                    continue
                seen.add(key)
                path = list(reversed(paths[node]))
                if failure["target_id"] != node:
                    path.insert(0, failure["target_id"])
                output.append(dict(failure, path=path))
        return output

    def claim_state(self, claim_id, scope=None):
        value = self.resolve_claim(claim_id)
        if claim_id in self.claims:
            claim, record = self.claims[claim_id]
            state, _ = self._review_errors(claim_id, claim, record, scope or claim["scope"])
        else:
            state = value["claim"].get("review", {}).get("status", "not-reviewed")
        errors = self._analyze(claim_id, scope or value["claim"].get("scope"))
        return {"claim_id": claim_id, "review_state": state, "effective_validity": not errors,
                "errors": errors, "sha256": value["sha256"], "owner_id": value["owner_id"]}

    def access_record(self, target, revision=None):
        """Read the pinned bytes for provenance, keeping permissions current.

        The request-local cache contains immutable revisions only. It must not
        replace current owner/record sensitivity checks in access_errors.
        """
        current = self.records.get(target)
        if current is None:
            raise MemoryError("UNRESOLVED_REFERENCE", "Provenance record is missing")
        owner = self.owner_views[current["owner_id"]]
        if current["sensitivity"] == "restricted" or owner["native_data"].get("sensitivity") == "restricted":
            # Refuse before any additional historical payload is read. The
            # caller never receives old bytes from a currently restricted owner.
            raise MemoryError("ACCESS_DENIED", "Provenance record is restricted")
        if revision is None or revision == current["revision"]:
            return current
        cache = self.__dict__.setdefault("_access_revisions", {})
        key = (target, revision)
        if key not in cache:
            cache[key] = self.service.store.read_record(owner, target, revision)
        return cache[key]

    def access_claim(self, target, sha256=None):
        """Locate the immutable container matching a fixed claim fingerprint.

        A claim may have changed or disappeared from the current payload. Only
        verified store history can establish its old provenance in that case.
        """
        latest = self.claims.get(target)
        if latest and (sha256 is None or contracts.canonical_hash(latest[0]) == sha256):
            return latest
        cache = self.__dict__.setdefault("_access_claims", {})
        key = (target, sha256)
        if key in cache:
            return cache[key]
        candidates = [latest[1]] if latest else [record for record in self.records.values()
                                               if record["kind"] in {"event", "narrative", "experience", "overview"}]
        for current in candidates:
            for revision in range(current["revision"] - 1, 0, -1):
                record = self.access_record(current["record_id"], revision)
                for claim in record["payload"].get("claims", []):
                    if claim["claim_id"] == target and (sha256 is None or contracts.canonical_hash(claim) == sha256):
                        cache[key] = (claim, record)
                        return cache[key]
        raise MemoryError("ACCESS_DENIED", "Pinned claim provenance is unavailable")

    def access_claim_containers(self, target, sha256=None):
        """Preserve every provenance container for an identical fixed claim.

        Claim refs bind the claim hash, not its enclosing record revision. If
        the claim bytes stay unchanged while parent sources change, using only
        the latest container could hide revoked original provenance. Check the
        union of verified matching containers, cached within this request.
        """
        cache = self.__dict__.setdefault("_access_claim_containers", {})
        key = (target, sha256)
        if key in cache:
            return cache[key]
        claim, first = self.access_claim(target, sha256)
        expected = sha256 or contracts.canonical_hash(claim)
        current = self.records[first["record_id"]]
        matches = []
        for revision in range(current["revision"], 0, -1):
            record = self.access_record(current["record_id"], revision)
            for candidate in record["payload"].get("claims", []):
                if candidate["claim_id"] == target and contracts.canonical_hash(candidate) == expected:
                    matches.append((candidate, record))
        cache[key] = matches
        return matches

    def access_errors(self, target, *, revision=None):
        """Check all provenance visibility independently of scientific validity.

        Background and analogy do not propagate retraction, but they also do
        not grant permission to expose text derived from a restricted source.
        This method reports access/missing-source errors, not review status.
        """
        initial = target if isinstance(target, dict) else {"target_id": target, "revision": revision}
        queue, visited, errors = deque([(initial, [initial["target_id"]])]), set(), []
        while queue:
            pinned, path = queue.popleft()
            current = pinned["target_id"]
            key = (current, pinned.get("revision"), pinned.get("sha256"))
            if key in visited:
                continue
            visited.add(key)
            refs = []
            if current in self.claims or (pinned.get("target_kind") == "claim" and current not in self.legacy.nodes):
                try:
                    containers = self.access_claim_containers(current, pinned.get("sha256"))
                except MemoryError:
                    errors.append(issue("ACCESS_DENIED", current, "Pinned claim provenance is unavailable", list(reversed(path))))
                    continue
                for claim, record in containers:
                    queue.append(({"target_id": record["record_id"], "revision": record["revision"]}, path + [record["record_id"]]))
                continue
            if current in self.records:
                try:
                    record = self.access_record(current, pinned.get("revision"))
                except MemoryError as exc:
                    errors.append(issue("ACCESS_DENIED", current, "Pinned record provenance is unavailable", list(reversed(path))))
                    continue
                if pinned.get("sha256") and pinned["sha256"] != record["record_hash"]:
                    errors.append(issue("ACCESS_DENIED", current, "Pinned record fingerprint is unavailable", list(reversed(path))))
                    continue
                owner = self.owner_views.get(record["owner_id"])
                if record["sensitivity"] == "restricted" or self.records[current]["sensitivity"] == "restricted" or (owner and owner["native_data"].get("sensitivity") == "restricted"):
                    errors.append(issue("ACCESS_DENIED", current, "Record visibility is restricted", list(reversed(path))))
                    continue
                refs = list(iter_refs({"sources": record["sources"], "payload": record["payload"]}))
            elif current in self.legacy.nodes:
                node = self.legacy.nodes[current]
                if node["raw"].get("sensitivity") == "restricted":
                    errors.append(issue("ACCESS_DENIED", current, "Legacy evidence visibility is restricted", list(reversed(path))))
                    continue
                if node.get("owner"):
                    queue.append(({"target_id": node["owner"]}, path + [node["owner"]]))
                old_refs = list(self.legacy.refs(node))
                for group in ("inputs", "artifacts"):
                    old_refs += [{"target": item.get("path")} for item in node["raw"].get(group, []) if isinstance(item, dict)]
                for ref in old_refs:
                    reference = ref.get("target")
                    if reference in self.legacy.nodes:
                        queue.append(({"target_id": reference}, path + [reference]))
                    else:
                        try:
                            original = legacy.reference_path(self.root, reference)
                            if not original.is_file():
                                raise OSError("Missing legacy source")
                        except ValueError:
                            errors.append(issue("ACCESS_DENIED", reference, "Legacy source permission or path is unavailable", [reference] + list(reversed(path))))
                        except OSError:
                            errors.append(issue("UNRESOLVED_REFERENCE", reference, "Legacy source is missing", [reference] + list(reversed(path))))
                continue
            elif current in self.owner_views:
                owner = self.owner_views[current]
                if owner["native_data"].get("sensitivity") == "restricted":
                    errors.append(issue("ACCESS_DENIED", current, "Owner visibility is restricted", list(reversed(path))))
                continue
            else:
                errors.append(issue("UNRESOLVED_REFERENCE", current, "Provenance target is missing", list(reversed(path))))
                continue
            for ref in refs:
                reference = ref["target_id"]
                if ref["target_kind"] == "file":
                    try:
                        self.service._file(ref)
                    except MemoryError as exc:
                        errors.append(issue(exc.code, reference, str(exc), [reference] + list(reversed(path))))
                else:
                    queue.append((ref, path + [reference]))
        return errors

    def prepare_review(self, request):
        """Build a trusted review revision; caller must re-run while holding lock.

        No caller-provided record IDs, revision numbers, timestamps, hashes or
        allow_review flag are accepted here. The owner is derived from the claim.
        The service handles idempotency and publishes this through MemoryStore.
        """
        allowed = {"schema_version", "request_id", "owner_id", "expected_head", "dry_run", "actor",
                   "target_claim_id", "state", "reason", "scope", "evidence_refs", "replacement_claim_id", "expected_content_hash"}
        if not isinstance(request, dict) or set(request) - allowed:
            raise MemoryError("INVALID_SCHEMA", "Unknown review request fields")
        cid = request.get("target_claim_id")
        value = self.resolve_claim(cid)
        if value.get("legacy"):
            return {"legacy": True, "claim_id": cid, "owner_id": value["owner_id"]}
        claim, record = self.claims[cid]
        state, scope = request.get("state"), request.get("scope")
        if not isinstance(state, str) or state not in STATES:
            raise MemoryError("INVALID_SCHEMA", "Unknown review state")
        if request.get("owner_id", record["owner_id"]) != record["owner_id"]:
            raise MemoryError("INVALID_SCHEMA", "Review owner must match the claim owner")
        if request.get("expected_content_hash", record["content_hash"]) != record["content_hash"]:
            raise MemoryError("STALE_BASIS", "Claim evidence content changed before review")
        evidence_refs = request.get("evidence_refs", [])
        replacement = request.get("replacement_claim_id")
        if state == "superseded":
            if not replacement or replacement == cid:
                raise MemoryError("EVIDENCE_INELIGIBLE", "Replacement must be a different existing claim")
            self.resolve_claim(replacement)
        elif replacement:
            raise MemoryError("INVALID_SCHEMA", "Replacement is only valid for superseded state")
        claim_ref = {"target_kind": "claim", "target_id": cid, "revision": None, "sha256": value["sha256"],
                     "locator": "claim:" + cid, "relation": "references"}
        record_ref = {"target_kind": "record", "target_id": record["record_id"], "revision": record["revision"],
                      "sha256": None, "locator": "payload.claims", "relation": "references"}
        draft = {"owner_id": record["owner_id"], "kind": "review", "title": "Claim review: " + cid,
                 "body_markdown": "", "record_reason": request.get("reason", ""), "change_reason": request.get("reason", ""),
                 "sources": [claim_ref, record_ref], "provenance_gap": None, "discovery": record["discovery"],
                 "sensitivity": record["sensitivity"], "payload": {"target_claim_id": cid,
                     "target_content_hash": record["content_hash"], "state": state, "reviewer": request.get("actor"),
                     "reason": request.get("reason", ""), "evidence_refs": deepcopy(evidence_refs),
                     "scope": scope, "replacement_claim_id": replacement}}
        result = contracts.validate_record(draft, {"allow_review": True})
        if not result["valid"]:
            raise MemoryError("EVIDENCE_INELIGIBLE" if state == "accepted" else "INVALID_SCHEMA", "Review does not meet the contract", errors=result["errors"])
        previous = self.reviews.get(cid)
        self.reviews[cid] = result["record"]
        try:
            for ref in evidence_refs:
                self._reference(ref)
            if state == "accepted":
                failures = self._analyze(cid, scope)
                if failures:
                    raise MemoryError("EVIDENCE_INELIGIBLE", "Claim cannot be accepted in this scope", errors=failures)
        finally:
            if previous is None:
                self.reviews.pop(cid, None)
            else:
                self.reviews[cid] = previous
        return {"owner_id": record["owner_id"], "draft": result["record"],
                "record_id": previous["record_id"] if previous else None,
                "expected_revision": previous["revision"] if previous else None,
                "basis_checks": deepcopy(self.basis_checks), "claim_id": cid}

    def formal_projection(self, refs, scope):
        if not isinstance(scope, str) or not scope.strip():
            raise MemoryError("INVALID_ARGUMENT", "Formal projection requires an explicit scope")
        selected, rejected, queue, visited = set(), [], deque(), set()
        for ref in refs:
            try:
                if isinstance(ref, str):
                    queue.append(ref)  # Explicit current-ID query, never rewrites a fixed Ref.
                else:
                    target = self._reference(ref)
                    if target:
                        queue.append(target)
            except MemoryError as exc:
                rejected.append({"canonical_id": ref.get("target_id"), "errors": [issue(exc.code, ref.get("target_id"), str(exc))]})
        while queue:
            target = queue.popleft()
            if target in visited:
                continue
            visited.add(target)
            if target in self.claims or (target in self.legacy.nodes and self.legacy.nodes[target]["kind"] == "claim"):
                selected.add(target)
            elif target in self.records:
                record = self.records[target]
                if record["kind"] in {"event", "narrative", "experience", "overview"}:
                    selected.update(claim["claim_id"] for claim in record["payload"]["claims"])
                elif record["kind"] == "association":
                    # Accepting a navigation link does not make its endpoints
                    # scientific support for the link or for each other. Even
                    # accepted endpoint claims must be selected independently.
                    rejected.append({"canonical_id": target, "errors": [issue("EVIDENCE_INELIGIBLE", target,
                        "Navigation associations cannot supply formal scientific support")]})
                else:
                    for ref in list(iter_refs(record["payload"])) + record["sources"]:
                        try:
                            dependency = self._reference(ref)
                            if dependency:
                                queue.append(dependency)
                        except MemoryError as exc:
                            rejected.append({"canonical_id": target, "errors": [issue(exc.code, ref["target_id"], str(exc), [ref["target_id"], target])]})
            elif target in self.owner_views or target in self.legacy.nodes:
                selected.update(cid for cid, (_claim, record) in self.claims.items() if record["owner_id"] == target)
                selected.update(cid for cid, node in self.legacy.nodes.items() if node.get("owner") == target)
            else:
                rejected.append({"canonical_id": target, "errors": [issue("UNRESOLVED_REFERENCE", target, "Target is missing")]})
        claims = []
        for cid in sorted(selected):
            try:
                access = self.access_errors(cid)
                if access:
                    rejected.append({"canonical_id": cid, "errors": access})
                    continue
                value, state = self.resolve_claim(cid), self.claim_state(cid, scope)
                if not state["effective_validity"]:
                    rejected.append({"canonical_id": cid, "errors": state["errors"]})
                    continue
                record = value["record"]
                claims.append({"canonical_id": cid, "claim_id": cid, "owner_id": value["owner_id"],
                               "record_id": record["record_id"] if record else None, "revision": record["revision"] if record else None,
                               "sha256": value["sha256"], "statement": value["claim"]["statement"], "text": value["claim"]["statement"],
                               "scope": scope, "review_state": "accepted", "effective_validity": True})
            except MemoryError as exc:
                rejected.append({"canonical_id": cid, "errors": [issue(exc.code, cid, str(exc))]})
        # Public output must not reveal hidden owner identities just because
        # the internal adapter checked their watermark. Keep the complete
        # source_heads/basis_checks on the adapter for transactions and Catalog.
        visible_heads = {oid: deepcopy(head) for oid, head in self.source_heads.items()
                         if not any(error["code"] in {"ACCESS_DENIED", "UNSAFE_PATH"} for error in self.access_errors(oid))}
        return {"claims": claims, "rejected": rejected, "text": "\n\n".join(item["text"] for item in claims),
                "source_heads": visible_heads}


def formal_projection(root, refs, scope, *, service=None):
    if service is None:
        from .service import MemoryService
        service = MemoryService(root)
    return EvidenceAdapter(service).formal_projection(refs, scope)
