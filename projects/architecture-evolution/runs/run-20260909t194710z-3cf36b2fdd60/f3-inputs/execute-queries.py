"""Capture public A07/A08 product calls; do not generate AI judgments.

The readable projection copies returned Markdown and receipt metadata verbatim.
An AI must actually read those files before declaring any reading or assessment.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import os
import sys

REPOSITORY = Path.cwd().resolve()
RUN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "automation/testing"))
import ai_review

F3 = json.loads((RUN / "f3-inputs/manifest.json").read_text(encoding="utf-8"))
ROOT = Path(F3["root"])
CLI = REPOSITORY / "automation/scripts/workspace_cli.py"
ACTOR = "Codex /root/retrieval_review actual AI"
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError("Refusing to overwrite existing evidence: " + str(path))
        return
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def request(key, definition, *, excluded=(), output_chars=12000, association="off"):
    scope = {"owner_ids": [F3["record_owners"][key]], "levels": None, "kinds": None, "roles": None,
        "outcomes": None, "review_states": None, "validities": None, "include_unknown": False,
        "excluded_refs": [F3["refs"][x] for x in excluded], "excluded_owner_ids": [],
        "recorded_from": None, "recorded_before": None, "include_refs": [F3["refs"][key]]}
    return {"definition": {"key": definition, "version": "1"}, "question": F3["refs"][key]["id"], "keywords": [],
        "scope": scope, "scope_ceiling": deepcopy(scope), "purpose": "exploration",
        "association": {"mode": association, "strategy": "existing-relations", "strategy_version": "1",
            "max_items": 5, "output_share": 0.2, "supplement_scope": None},
        "budget": {"wall_ms": 10000, "read_bytes": 2097152, "output_chars": output_chars,
            "candidates": 100, "graph_nodes": 50, "graph_edges": 100, "graph_hops": 2, "model_tokens": 0},
        "freshness": "fixed", "result_limit": 8, "missing_policy": "reject", "fallback_definitions": [],
        "applicability": "SYNTHETIC F3 only", "channels": ["identity"]}


def capture(attempt, label, action, raw=None, assemble=False):
    path = attempt / "authored-requests" / (label + ".json")
    if raw is not None:
        write(path, raw)
    argv = [sys.executable, "-X", "utf8", str(CLI), "material-query", action]
    if raw is not None:
        argv += ["--request", str(path)]
    if assemble:
        argv += ["--assemble"]
    old = [p for p in (attempt / "calls").glob("*/result.json") if json.loads(p.read_text(encoding="utf-8"))["argv"] == argv]
    if old:
        call, receipt = old[0].parent, json.loads(old[0].read_text(encoding="utf-8"))
    else:
        call, receipt = ai_review.capture_call(attempt, argv, path if raw is not None else None, cwd=ROOT)
        write(call / "product-fingerprints.json", {str(p.relative_to(REPOSITORY)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [CLI, REPOSITORY / "automation/scripts/material_query/coordinator.py", REPOSITORY / "automation/scripts/material_query/assembly.py"]})
    value = json.loads((call / "stdout.txt").read_bytes())
    projection = ["# " + label, "", "这是公开调用实际输出的可读投影；AI 阅读尚未声明。", "",
        "调用证据：" + str(call.relative_to(attempt)), "", "返回码：" + str(receipt["exit_code"]), ""]
    packet = value.get("assembly", value)
    payload = packet.get("value") if isinstance(packet.get("value"), dict) else {}
    projection += ["```json", json.dumps({"status": packet.get("status"), "code": packet.get("code"),
        "warnings": packet.get("warnings"), "consumed": packet.get("consumed"), "stop_reason": packet.get("stop_reason"),
        "complete": payload.get("complete"), "basis": packet.get("basis")}, ensure_ascii=False, indent=2), "```", ""]
    for part in payload.get("parts", []):
        projection += ["## " + part["group"] + " / " + part["heading"], "", part["markdown"], "",
            "固定来源：`" + json.dumps(part["refs"], ensure_ascii=False) + "`", ""]
    if not payload.get("parts"):
        projection += ["## 完整返回值", "", "```json", json.dumps(value, ensure_ascii=False, indent=2), "```", ""]
    write(attempt / "delivered" / (label + ".md"), "\n".join(projection))
    return {"label": label, "call": str(call), "delivered": str(attempt / "delivered" / (label + ".md")), "exit_code": receipt["exit_code"]}


def main():
    meta = {"fixture": F3, "source_generation": "Independent AI-authored SYNTHETIC premises; no F1 labels imported",
        "context": "continuous; same executing AI authored premises; not a blinded or fresh-context test",
        "source_fingerprints": {str(path.relative_to(REPOSITORY)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [CLI, REPOSITORY / "automation/scripts/material_query/coordinator.py",
                         REPOSITORY / "automation/scripts/material_query/assembly.py", REPOSITORY / "automation/testing/ai_review.py"]}}
    metadata_path = RUN / "f3-inputs/ai-input-environment.json"
    if not metadata_path.exists():
        write(metadata_path, meta)
    attempts = {}
    for name in ("A07", "A08"):
        existing = list((RUN / "actual-ai" / name).glob("attempt-*/manifest.json"))
        attempts[name] = existing[0].parent if existing else ai_review.initialize(RUN / "actual-ai", name, actor=ACTOR, model=None,
            context_mode="continuous", metadata_file=metadata_path)
    calls = []
    a07, a08 = attempts["A07"], attempts["A08"]
    calls.append(capture(a07, "definitions", "definitions"))
    for label, key, definition, options in (
        ("tank-summary", "tank_model", "unit_digest", {}),
        ("tank-full", "tank_section", "full", {}),
        ("tank-excluded-definition", "tank_section", "full", {"excluded": ["tank_definitions"]}),
        ("section-summary-missing", "tank_section", "unit_digest", {}),
        ("tank-small-budget", "tank_section", "full", {"output_chars": 250})):
        calls.append(capture(a07, label, "search", request(key, definition, **options), True))
    calls.append(capture(a08, "capabilities", "capabilities"))
    calls.append(capture(a08, "tank-full", "search", request("tank_section", "full"), True))
    calls.append(capture(a08, "retry-full", "search", request("retry", "full"), True))
    calls.append(capture(a08, "unconfigured-structural", "search", request("tank_section", "full", association="explore_structural"), True))
    write(RUN / "f3-inputs/attempts.json", {"attempts": {key: str(path) for key, path in attempts.items()}, "calls": calls})
    print(json.dumps({"attempts": {key: str(path) for key, path in attempts.items()}, "calls": calls}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
