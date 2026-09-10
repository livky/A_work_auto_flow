"""Validate optional, authored knowledge facets without changing old records.

The JSON schema establishes field shapes. These domain checks require fixed
classification/attempt/confidence evidence, explicit probability calibration,
and coherent applicability intervals. A saved classification is not a review:
this module neither assigns accepted status nor guesses outcomes from prose.
"""
from datetime import datetime
import math
import re


def validate_knowledge_facets(record):
    """Return relative payload errors after the structural schema has passed.

``knowledge_facets`` is optional and belongs to the existing payload hash.
Absent facets remain absent; adding defaults here would rewrite historical
content fingerprints and manufacture classifications for legacy materials.
"""
    facets = record["payload"].get("knowledge_facets")
    if facets is None:
        return []
    errors = []
    base = "/knowledge_facets"

    def add(path, message):
        errors.append((base + path, message))

    def terms(values, path):
        if any(not value.strip() or value != value.strip() for value in values):
            add(path, "Facet labels must be nonblank and have no surrounding whitespace")
        if len(set(values)) != len(values):
            add(path, "Duplicate facet labels are not allowed")

    def applicability(value, path):
        # Timezone-aware UTC is the same canonical storage convention as the
        # other memory timestamps. Null endpoints denote explicitly unbounded
        # applicability; they are not replaced with the current clock.
        terms(value["conditions"], path + "/conditions")
        terms(value["exclusions"], path + "/exclusions")
        if set(value["conditions"]) & set(value["exclusions"]):
            add(path, "An applicability condition cannot also be excluded")
        endpoints = []
        for name in ("valid_from", "valid_until"):
            raw = value[name]
            if raw is None:
                endpoints.append(None)
                continue
            try:
                if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", raw):
                    raise ValueError("not canonical UTC")
                endpoints.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
            except ValueError:
                endpoints.append(None)
                add(path + "/" + name, "Applicability time must be RFC3339 UTC ending Z")
        if all(endpoints) and endpoints[0] >= endpoints[1]:
            add(path, "Applicability interval must have valid_from before valid_until")

    terms(facets["roles"], "/roles")
    if facets["roles"] and not facets["classification_basis"]:
        add("/classification_basis", "Authored knowledge roles require fixed classification evidence")
    if ("principle" in facets["roles"]) != (facets["principle_kind"] is not None):
        add("/principle_kind", "The principle role and its explicit subtype must be supplied together")
    applicability(facets["applicability"], "/applicability")
    for position, attempt in enumerate(facets["attempts"]):
        terms(attempt["conditions"], f"/attempts/{position}/conditions")
    for position, assessment in enumerate(facets["confidence"]):
        path = f"/confidence/{position}"
        if not assessment["assessed_by"].strip() or any(not assessment["method"][key].strip() for key in ("name", "version")):
            add(path, "Confidence requires a named assessor and method version")
        if assessment["level"] != "unknown" and not assessment["basis"]:
            add(path + "/basis", "A known confidence level requires fixed assessment evidence")
        probability = assessment["calibrated_probability"]
        if probability is not None:
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                add(path + "/calibrated_probability", "Calibrated probability must be finite and between zero and one")
            if assessment["calibration_ref"] is None:
                add(path + "/calibration_ref", "A numeric probability requires fixed calibration evidence")
        applicability(assessment["applicability"], path + "/applicability")

    def fixed(value, path):
        # Ordinary legacy record references may omit SHA for service resolution.
        # Classifications are evidence assertions, so their own reference closure
        # must already be fixed; the existing service still resolves/authorizes it.
        if isinstance(value, dict):
            if "target_kind" in value and not re.fullmatch(r"[0-9a-f]{64}", value.get("sha256") or ""):
                add(path + "/sha256", "Facet evidence requires a fixed SHA-256 fingerprint")
            for key, child in value.items():
                fixed(child, path + "/" + key)
        elif isinstance(value, list):
            for position, child in enumerate(value):
                fixed(child, path + "/" + str(position))

    fixed(facets, "")
    return errors
