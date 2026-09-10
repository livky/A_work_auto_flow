"""Public fixed-source expansion and selected-chapter reading for actual AI review.

This records product responses only. The assistant must inspect the saved text
before separately declaring reading or assessing the frozen expectations.
"""
import json
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from save_implementation_records import call, write_new, OWNER, DOCS

RUN = Path(__file__).resolve().parent
checks = json.loads((RUN / "implementation-recording-checks.json").read_text(encoding="utf-8"))
unit = checks["units"]["IMPL-U1"]
source = {"target_kind": "file", "target_id": "SRC-ARCH-IMPLEMENTATION-20260910-1", "revision": None,
          "sha256": hashlib.sha256((RUN / "IMPLEMENTATION_CONTENT.md").read_bytes()).hexdigest(),
          "locator": "完整固定报告", "relation": "input"}
request = write_new("implementation-expand-request.json", {"refs": [unit, source],
    "selection": {"owner_id": OWNER, "full_ids": [unit["target_id"], source["target_id"]], "purpose": "exploration", "budget": 20000}})
call("implementation-fixed-expand", ["memory", "expand", "--request", str(request)], "A01")
request = write_new("implementation-section-context-request.json", {"owner_id": OWNER,
    "document_id": DOCS[0], "revision": checks[DOCS[0]]["ref"]["revision"],
    "section_id": checks["sections"]["IMPL-P1"]["target_id"], "budget": {"max_chars": 20000}})
call("implementation-selected-section", ["memory", "section-context", "--request", str(request)], "A03")
