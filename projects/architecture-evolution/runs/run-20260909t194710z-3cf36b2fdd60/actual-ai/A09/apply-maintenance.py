"""Apply the reviewed plan, repeat its stable request, and inspect fixed revisions."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture as c

target = c.attempt()
request = json.loads((target / "ready-apply-request.json").read_text(encoding="utf-8"))
first = c.call("maintenance-apply", "maintenance-apply", request)
repeat = c.call("maintenance-apply-same-id", "maintenance-apply", request)
model_ref = c.F3["refs"]["tank_model"]
old = c.call("model-r1-after", "inspect", domain="memory", inspect_args=["RES-F3-TANK", "--record-id", model_ref["id"], "--revision", "1"])
new = c.call("model-r2-after", "inspect", domain="memory", inspect_args=["RES-F3-TANK", "--record-id", model_ref["id"], "--revision", "2"])
# Re-submitting the old review after the real canonical write must expose its
# stale HEAD. This negative check is read/preflight-only and cannot undo r2.
old_review = json.loads((target / "authored-requests/maintenance-review.json").read_text(encoding="utf-8"))
stale = c.call("maintenance-stale-review", "maintenance-review", old_review)
index = c.call("maintenance-index-reconcile", "reconcile", {"owner_id": "RES-F3-TANK", "vector": "off"}, domain="memory")
for key in ("tank_definitions", "saturation"):
    ref = c.F3["refs"][key]
    c.call("retained-" + key, "inspect", domain="memory", inspect_args=[c.F3["record_owners"][key], "--record-id", ref["id"], "--revision", "1"])
c.write(target / "applied-model.json", new)
print(json.dumps({"first": first, "repeat": repeat, "old_hash": old.get("record", {}).get("record_hash"),
    "new_record": new.get("record"), "stale_review": stale, "reconciled_index_status": index.get("index_status")}, ensure_ascii=False, indent=2))
