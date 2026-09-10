"""Strict, offline memory contracts and named domain validation.

Only the documented JSON Schema subset is supported. This is deliberately not
a general JSON Schema implementation. Validation is pure: callbacks supplied by
the service may read authorized references, but this module never writes files.
"""
import copy
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "memory-v3.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
LEGACY_LEVELS = {"source": "L0", "event": "L1", "experience": "L2", "map": "L3",
          **dict.fromkeys(("question", "goal", "route", "checkpoint", "association",
                           "representation", "policy", "consolidation", "feedback", "review"))}
V2_LEVELS = {**LEGACY_LEVELS, "detail": "L1", "event": "L2", "experience": "L3", "map": "L4"}
LEVELS = {**V2_LEVELS, 'document': None, 'document_section': None}
RECORD_SCHEMA_VERSION = 3
TAXONOMY_VERSION = 2
CONTENT_FIELDS = ("owner_id", "kind", "level", "title", "keywords", "body_markdown",
                  "payload", "sources", "provenance_gap", "discovery", "sensitivity")
SUPPORTED = {"type", "const", "enum", "required", "properties", "additionalProperties",
             "items", "minLength", "minItems", "oneOf", "$defs", "$ref"}


def project_memory_level(record):
    """Return the current semantic layer without changing immutable bytes.

    ``level`` participates in v1 content_hash. Never write this projected value
    back into a historical record or include display metadata in its hash.
    Unknown versions/kinds fail explicitly instead of inventing a layer.
    """
    version, kind = record.get("schema_version", 1), record.get("kind")
    allowed = LEGACY_LEVELS if version == 1 else V2_LEVELS if version == 2 else LEVELS
    if type(version) is not int or version not in (1, 2, 3) or kind not in allowed:
        raise ValueError("Unsupported memory record version or kind")
    return LEVELS[kind]


# Both names are public for consumers which render current research history.
effective_level = project_memory_level


def canonical_hash(value):
    """SHA-256 of UTF-8 canonical JSON; array and Unicode text order are retained."""
    def check(item):
        # json.dumps silently coerces integer map keys and tuples. Neither is a
        # JSON value supplied by our cross-language contract, so reject them.
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError("Canonical JSON object keys must be strings")
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        elif type(item) not in (str, int, float, bool, type(None)):
            raise ValueError("Canonical hashing accepts JSON values only")
    check(value)
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def content_hash(record):
    """Exclude audit metadata; content changes alone create a content revision."""
    return canonical_hash({key: record[key] for key in CONTENT_FIELDS})


def _pointer(path, key):
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _error(path, message, code="INVALID_SCHEMA"):
    return {"code": code, "path": path, "message": message}


def _check_schema(schema, defs, visiting=None):
    """Reject unsupported syntax even in unselected oneOf branches."""
    if not isinstance(schema, dict) or set(schema) - SUPPORTED:
        raise ValueError("Unsupported schema keywords or non-object schema")
    if not isinstance(defs, dict):
        raise ValueError("$defs must be an object")
    for key in ("properties", "$defs"):
        if key in schema and (not isinstance(schema[key], dict) or any(not isinstance(name, str) for name in schema[key])):
            raise ValueError(key + " must map string names to schemas")
    if "required" in schema:
        required = schema["required"]
        if not isinstance(required, list) or any(not isinstance(name, str) for name in required) or len(set(required)) != len(required):
            raise ValueError("required must be an array of unique strings")
    for key in ("minLength", "minItems"):
        if key in schema and (type(schema[key]) is not int or schema[key] < 0):
            raise ValueError(key + " must be a non-negative integer")
    if "oneOf" in schema and (not isinstance(schema["oneOf"], list) or not schema["oneOf"]):
        raise ValueError("oneOf must be a non-empty schema array")
    if "enum" in schema:
        if not isinstance(schema["enum"], list) or not schema["enum"]:
            raise ValueError("enum must be a non-empty array")
        values = [canonical_hash(item) for item in schema["enum"]]
        if len(set(values)) != len(values):
            raise ValueError("enum values must be unique")
    if "const" in schema:
        canonical_hash(schema["const"])
    if "additionalProperties" in schema and not isinstance(schema["additionalProperties"], (bool, dict)):
        raise ValueError("additionalProperties must be boolean or schema")
    if "items" in schema and not isinstance(schema["items"], dict):
        raise ValueError("items must be a schema")
    if "$ref" in schema:
        target = schema["$ref"]
        if not isinstance(target, str) or not target.startswith("#/$defs/") or target[8:] not in defs:
            raise ValueError("Only existing local $defs references are supported")
        visiting = set() if visiting is None else visiting
        if target in visiting:
            raise ValueError("Recursive schema references are not supported by this subset")
        _check_schema(defs[target[8:]], defs, visiting | {target})
    for key in ("properties", "$defs"):
        for child in schema.get(key, {}).values():
            _check_schema(child, defs, visiting)
    for child in schema.get("oneOf", []):
        _check_schema(child, defs, visiting)
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            _check_schema(schema[key], defs, visiting)
    types = schema.get("type", [])
    types = [types] if isinstance(types, str) else types
    if not isinstance(types, list) or ("type" in schema and not types) or any(not isinstance(t, str) for t in types):
        raise ValueError("type must be a known name or non-empty array of names")
    if len(set(types)) != len(types) or any(t not in {"object", "array", "string", "integer", "number", "boolean", "null"} for t in types):
        raise ValueError("Unsupported schema type")


def check_schema(schema, defs=None):
    """Validate a trusted extension schema before registering any adapter.

    Raises ValueError for unsupported or malformed schema syntax. This public
    entry permits registration checks without fabricating an example instance.
    """
    if not isinstance(schema, dict):
        raise ValueError("Schema must be an object")
    _check_schema(schema, schema.get("$defs", {}) if defs is None else defs)


def validate_schema(value, schema, defs=None):
    """Return JSON-pointer errors. Invalid schema syntax raises ValueError."""
    check_schema(schema, defs)
    defs = schema.get("$defs", {}) if defs is None else defs

    def visit(v, node, path):
        errors = []
        if "$ref" in node:
            errors.extend(visit(v, defs[node["$ref"][8:]], path))
        if "oneOf" in node:
            branches = [visit(v, branch, path) for branch in node["oneOf"]]
            if sum(not e for e in branches) != 1:
                errors.append(_error(path, "Exactly one schema alternative must match"))
                if branches and all(branches):
                    errors.extend(min(branches, key=len))
            # oneOf and $ref do not erase sibling constraints. A schema may
            # combine them with type/const/properties, all of which must hold.
        checks = {"object": lambda: isinstance(v, dict), "array": lambda: isinstance(v, list),
                  "string": lambda: isinstance(v, str), "integer": lambda: type(v) is int,
                  "number": lambda: type(v) in (int, float) and math.isfinite(v),
                  "boolean": lambda: type(v) is bool, "null": lambda: v is None}
        types = node.get("type", [])
        types = [types] if isinstance(types, str) else types
        if types and not any(checks[t]() for t in types):
            return [_error(path, "Unexpected value type")]
        # Python considers True == 1; JSON enum/const must preserve JSON types.
        equal = lambda a, b: type(a) is type(b) and a == b
        if "const" in node and not equal(v, node["const"]):
            errors.append(_error(path, "Value does not match const"))
        if "enum" in node and not any(equal(v, e) for e in node["enum"]):
            errors.append(_error(path, "Value is outside enum"))
        if isinstance(v, str) and len(v) < node.get("minLength", 0):
            errors.append(_error(path, "String is too short"))
        if isinstance(v, list):
            if len(v) < node.get("minItems", 0):
                errors.append(_error(path, "Array is too short"))
            if "items" in node:
                for index, item in enumerate(v):
                    errors.extend(visit(item, node["items"], _pointer(path, index)))
        if isinstance(v, dict):
            for key in node.get("required", []):
                if key not in v:
                    errors.append(_error(_pointer(path, key), "Required field is missing"))
            properties = node.get("properties", {})
            for key, item in v.items():
                if key in properties:
                    errors.extend(visit(item, properties[key], _pointer(path, key)))
                elif isinstance(node.get("additionalProperties"), dict):
                    errors.extend(visit(item, node["additionalProperties"], _pointer(path, key)))
                elif node.get("additionalProperties") is False:
                    errors.append(_error(_pointer(path, key), "Unknown field"))
        return errors

    try:
        canonical_hash(value)
    except (ValueError, TypeError, UnicodeError):
        return [_error("", "Value must be finite, Unicode JSON")]
    return visit(value, schema, "")


def _utc(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_references(record, context):
    """Check fixed versions before resolving; authority stays with the callback."""
    errors = []

    def walk(value, path):
        if isinstance(value, dict):
            if "target_kind" in value:
                revision = value.get("revision")
                if revision is not None and (type(revision) is not int or revision < 1):
                    errors.append(_error(path + "/revision", "Fixed revisions must be positive integers"))
                if value["target_kind"] == "record":
                    if type(value.get("revision")) is not int or value["revision"] < 1:
                        errors.append(_error(path + "/revision", "Record references need a positive fixed revision"))
                elif not re.fullmatch(r"[0-9a-f]{64}", value.get("sha256") or ""):
                    errors.append(_error(path + "/sha256", "Reference needs a SHA-256 fingerprint"))
                if value.get("sha256") is not None and not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]):
                    errors.append(_error(path + "/sha256", "Invalid SHA-256"))
                resolver = context.get("resolve_ref")
                if resolver:
                    try:
                        resolved = resolver(value)
                        if resolved is None or resolved is False:
                            raise LookupError("Reference target is missing")
                    except (LookupError, ValueError):
                        # Callback exceptions may contain source excerpts or
                        # private filesystem paths. Domain MemoryError codes
                        # propagate; generic callback errors receive safe text.
                        errors.append(_error(path, "Reference target could not be resolved", "UNRESOLVED_REFERENCE"))
            for key, item in value.items():
                if key.endswith("_at") and item is not None and not _utc(item):
                    errors.append(_error(_pointer(path, key), "Expected RFC3339 UTC timestamp ending Z"))
                walk(item, _pointer(path, key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, _pointer(path, index))
    walk(record, "")
    return errors


def validate_source_excerpt(record, context):
    """Compare selected original text exactly; never normalize newlines or spaces.

    lines:N-M uses inclusive one-based lines, retaining terminators. chars:N-M
    uses a zero-based, half-open Unicode code-point range (not UTF-16 units).
    """
    p = record["payload"]
    if record["kind"] != "source" or p["acquisition"] == "original_link":
        return []
    ref = p["source_ref"]
    locator = ref["locator"]
    if not locator:
        return [_error("/payload/source_ref/locator", "An excerpt requires a precise locator")]
    if p["acquisition"] != "verbatim_export":
        return []
    match = re.fullmatch(r"(lines|chars):(\d+)-(\d+)", locator)
    if not match or not context.get("read_source"):
        return [_error("/payload/source_ref/locator", "Verbatim export requires readable original text and lines:N-M or chars:N-M")]
    try:
        original = context["read_source"](ref)
    except (ValueError, LookupError, OSError):
        return [_error("/payload/source_ref", "Original text could not be read for comparison")]
    try:
        if not isinstance(original, str):
            raise ValueError("Source is not text; use original_link")
        unit, first, last = match.group(1), int(match.group(2)), int(match.group(3))
        values = original.splitlines(keepends=True) if unit == "lines" else original
        start, stop = (first - 1, last) if unit == "lines" else (first, last)
        if start < 0 or stop <= start or stop > len(values):
            raise ValueError("Source locator is outside original text")
        selected = "".join(values[start:stop])
        if selected != record["body_markdown"]:
            raise ValueError("Body is not identical to the selected original text")
    except ValueError as exc:
        return [_error("/body_markdown", str(exc))]
    return []


def validate_report(report, context=None):
    """Validate authored array order and immutable detail identities.

    A report is an arrangement, never a request to retrieve the latest record.
    Resolving callbacks retain the service's authorization and hash checks.
    """
    errors = validate_schema(report, SCHEMA['$defs']['ResearchReport'], SCHEMA['$defs'])
    if errors:
        return errors
    sections, details, synthesis = set(), set(), False
    resolver = (context or {}).get('resolve_ref')
    for i, section in enumerate(report['sections']):
        path = f'/sections/{i}'
        if section['section_id'] in sections:
            errors.append(_error(path, 'Duplicate report section identity'))
        sections.add(section['section_id'])
        if section['role'] in {'discussion', 'conclusion'}:
            synthesis = True
        if synthesis and section['role'] == 'experiment':
            errors.append(_error(path, 'Experiments must precede discussion and conclusion'))
        for j, block in enumerate(section['blocks']):
            if block['type'] != 'detail':
                for k, ref in enumerate(block['evidence_refs']):
                    if not re.fullmatch(r'[0-9a-f]{64}', ref.get('sha256') or ''):
                        errors.append(_error(path + f'/blocks/{j}/evidence_refs/{k}/sha256', 'Report evidence needs a fixed SHA-256'))
                continue
            ref = block['ref']
            where = path + f'/blocks/{j}/ref'
            if synthesis or section['role'] != 'experiment':
                errors.append(_error(where, 'Detail blocks belong to experiment sections before synthesis'))
            if ref['target_kind'] != 'record' or not ref['target_id'].startswith('MEM-') or type(ref.get('revision')) is not int or ref['revision'] < 1 or not re.fullmatch(r'[0-9a-f]{64}', ref.get('sha256') or ''):
                errors.append(_error(where, 'Detail needs fixed MEM identity, positive revision and SHA-256'))
                continue
            if ref['target_id'] in details:
                errors.append(_error(where, 'Duplicate report detail identity'))
            details.add(ref['target_id'])
            if resolver:
                target = resolver(ref)
                if not isinstance(target, dict) or target.get('kind') != 'detail':
                    errors.append(_error(where, 'Report detail reference must resolve to a detail record'))
    return errors


def validate_record(draft, context=None):
    """Normalize defaults without fabricating server identity, time or hashes."""
    context = context or {}
    record = copy.deepcopy(draft)
    if not isinstance(record, dict):
        return {"valid": False, "errors": [_error("", "Record must be an object")], "record": record}
    kind = record.get("kind")
    if not isinstance(kind, str) or kind not in LEVELS:
        return {"valid": False, "errors": [_error("/kind", "Unknown record kind")], "record": record}
    # Old CLI drafts did not have to spell out their version. Recognize only
    # the two v2 payload shapes whose v3 form changed, without rewriting their
    # content or silently converting a long report into a new document.
    payload = record.get('payload')
    legacy_shape = isinstance(payload, dict) and (
        kind == 'detail' and 'unit_type' not in payload and 'blocks' not in payload
        or kind == 'map' and 'report' in payload)
    record.setdefault('schema_version', 2 if legacy_shape else RECORD_SCHEMA_VERSION)
    version = record["schema_version"]
    levels = LEGACY_LEVELS if version == 1 else V2_LEVELS if version == 2 else LEVELS
    if type(version) is not int or version not in (1, 2, 3) or kind not in levels:
        return {"valid": False, "errors": [_error("/schema_version", "Unsupported record version for this kind")], "record": record}
    record.setdefault("level", levels[kind])
    record.setdefault("keywords", [])
    record.setdefault("provenance_gap", None)
    if isinstance(record.get("keywords"), list) and all(isinstance(v, str) for v in record["keywords"]):
        record["keywords"] = list(dict.fromkeys(record["keywords"]))
    if isinstance(record.get("payload"), dict):
        record["payload"].setdefault("missing_refs", [])
    definition = ''.join(part.title() for part in kind.split('_')) + 'DraftV' + str(version)
    errors = validate_schema(record, SCHEMA["$defs"][definition], SCHEMA["$defs"])
    if errors:
        return {"valid": False, "errors": errors, "record": record}
    p = record["payload"]
    # Optional v3 knowledge classifications are canonical payload content. Keep
    # validation separate from scientific review and never add defaults to old
    # records: their original payload and content fingerprints remain unchanged.
    if "knowledge_facets" in p:
        from .facets import validate_knowledge_facets
        errors.extend(_error('/payload' + path, message) for path, message in validate_knowledge_facets(record))
    if kind == 'map' and 'report' in p:
        errors.extend({**error, 'path': '/payload/report' + error['path']}
                      for error in validate_report(p['report'], context))
    add = lambda path, message, code="INVALID_SCHEMA": errors.append(_error(path, message, code))
    if not record["sources"] and not record["provenance_gap"]:
        add("/provenance_gap", "Explain missing provenance when sources are empty")
    if kind == "review" and context.get("allow_review") is not True:
        add("/kind", "Review records require the dedicated review service")
    if kind == "review":
        if not p["target_claim_id"].startswith("CLM-"):
            add("/payload/target_claim_id", "Review target must be a claim identity")
        if not re.fullmatch(r"[0-9a-f]{64}", p["target_content_hash"]):
            add("/payload/target_content_hash", "Review must bind a SHA-256 content fingerprint")
        if p["state"] == "accepted" and (not p["scope"] or not p["evidence_refs"]):
            add("/payload/evidence_refs", "Accepted review requires scope and evidence; eligibility is checked by review service")
        if p["state"] == "superseded" and (not p["replacement_claim_id"] or p["replacement_claim_id"] == p["target_claim_id"]):
            add("/payload/replacement_claim_id", "Superseded review needs a different replacement claim")
    if kind == "event" and p["decision"] and not p["decision_refs"] and not record["provenance_gap"]:
        add("/payload/decision_refs", "Decision requires evidence or an explicit provenance gap")
    if kind == 'detail' and version == 3:
        from .technical_units import validate_unit
        errors.extend(_error('/payload' + path, message) for path, message in validate_unit(record))
    if kind in {'document', 'document_section'}:
        from .technical_units import validate_composition
        errors.extend(_error('/payload' + path, message) for path, message in validate_composition(record, context))
    if kind == "detail" and version == 2:
        # A detailed explanation is a document referencing an actual Run. It is
        # not another experiment, and cannot gain accepted claims by existing.
        run = p["run_ref"]
        if run["target_kind"] != "owner" or not run["target_id"].startswith("RUN-") or not run.get("sha256"):
            add("/payload/run_ref", "Detail requires a fixed native RUN owner reference")
        if not p["inputs"] and not p["missing_refs"] and not record["provenance_gap"]:
            add("/payload/inputs", "Missing calculation inputs require an explicit evidence gap")
    if kind == "association" and p["relation"] == "analogous_to":
        if not p["shared_structure"]:
            add("/payload/shared_structure", "Analogy requires a shared problem structure")
        if not p["transfer_limits"]:
            add("/payload/transfer_limits", "Analogy requires non-transferable boundaries")
    if kind == "question" and p["status"] == "resolved" and not p["resolution_refs"]:
        add("/payload/resolution_refs", "Resolved question requires fixed answer references", "INVALID_TRANSITION")
    if kind in ("question", "route") and p["status"] == "superseded":
        if not p["replacement_ref"] or p["replacement_ref"]["target_id"] == record.get("record_id"):
            add("/payload/replacement_ref", "Superseded item requires a different replacement", "INVALID_TRANSITION")
    if kind == "route" and p["status"] == "blocked" and not p["blocker"]:
        add("/payload/blocker", "Blocked route requires a blocker", "INVALID_TRANSITION")
    if kind == "consolidation":
        remaining = {canonical_hash(r) for r in p["remaining_refs"]}
        for index, decision in enumerate(p["decisions"]):
            if decision["action"] == "defer" and canonical_hash(decision["target"]) not in remaining:
                add("/payload/decisions/" + str(index), "Deferred target must remain in remaining_refs")
    for index, claim in enumerate(p.get("claims", [])):
        if not claim["claim_id"].startswith("CLM-") or len(claim["claim_id"]) == 4:
            add("/payload/claims/" + str(index) + "/claim_id", "Claim ID must use CLM- prefix")
    if len({c["claim_id"] for c in p.get("claims", [])}) != len(p.get("claims", [])):
        add("/payload/claims", "Duplicate claim identity")
    if "revision" in record:
        revision = record["revision"]
        if revision < 1 or record.get("previous_revision") != (None if revision == 1 else revision - 1):
            add("/previous_revision", "Revision chain must increment by one")
    if "record_id" in record and not re.fullmatch(r"MEM-[A-Za-z0-9][A-Za-z0-9-]*", record["record_id"]):
        add("/record_id", "Record ID must be a safe MEM- identity")
    errors.extend(validate_references(record, context))
    errors.extend(validate_source_excerpt(record, context))
    for field in ("record_hash", "content_hash"):
        if field in record:
            expected = content_hash(record) if field == "content_hash" else canonical_hash({k: v for k, v in record.items() if k != "record_hash"})
            if record[field] != expected:
                add("/" + field, "Stored hash does not match canonical content")
    return {"valid": not errors, "errors": errors, "record": record}


def validate_request(request, *, allow_review=False):
    """Structural preflight; batch identity/reference resolution belongs to service."""
    errors = validate_schema(request, SCHEMA["$defs"]["CommitRequest"], SCHEMA["$defs"])
    if not errors:
        expected_kinds = {"set_policy": "policy", "transition_question": "question",
                          "decide_association": "association", "save_checkpoint": "checkpoint"}
        forbidden = {"record_id", "revision", "previous_revision", "record_hash", "content_hash",
                     "created_at", "created_by", "updated_at", "updated_by"}
        for index, operation in enumerate(request["operations"]):
            path = "/operations/" + str(index)
            draft = operation["draft"]
            for key in forbidden & draft.keys():
                errors.append(_error(path + "/draft/" + key, "Server-owned field cannot be supplied in a request"))
            expected = expected_kinds.get(operation["op"])
            if (draft.get("kind") == "review" and not allow_review) or (expected and draft.get("kind") != expected):
                errors.append(_error(path + "/draft/kind", "Operation does not permit this record kind"))
            creating = "client_key" in operation
            updating = "record_id" in operation
            if creating == updating or (updating and operation.get("expected_revision", 0) < 1) or (creating and "expected_revision" in operation):
                errors.append(_error(path, "Use client_key for creation or record_id and positive expected_revision for update"))
    return {"valid": not errors, "errors": errors, "request": copy.deepcopy(request)}
