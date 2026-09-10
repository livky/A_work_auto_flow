"""Capture final bytes of the explicit full-test inputs, retaining original receipt.

Usage: python capture_final_fingerprints.py. Exclusive output creation prevents
replacement of earlier observations; this does not infer test success or review.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
receipt = json.loads((RUN / "testing/full-attempt-01/results.json").read_text(encoding="utf-8"))
before = receipt["program_fingerprints"]
after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in before}
# The structural declaration is an explicit additional artifact, even when the
# test runner's original program inventory does not include .d.ts files.
name = "automation/schemas/memory-v3.d.ts"
after[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
with (RUN / "final-source-fingerprints.json").open("x", encoding="utf-8") as stream:
    json.dump({"observed_at": datetime.now(timezone.utc).isoformat(), "fingerprints": after,
        "changed_since_full_started": {name: {"before": before[name], "after": after[name]} for name in before if before[name] != after[name]},
        "additional_artifacts": [name], "note": "C17 fixture and generated structural declaration supplements are separate; no full receipt overwritten."}, stream, ensure_ascii=False, indent=2)
