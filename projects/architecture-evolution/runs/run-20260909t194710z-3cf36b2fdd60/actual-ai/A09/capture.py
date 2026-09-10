"""Generic public-call capture for actual A09, with no semantic decisions.

Run this helper from the repository root. Each label is a new evidence item;
post-commit index warnings stay in the real subprocess receipt. All material
operations target only the previously registered SYNTHETIC F3 workspace.
"""
from pathlib import Path
import json
import os
import sys

REPOSITORY = Path.cwd().resolve()
RUN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "automation/testing"))
sys.path.insert(0, str(RUN / "f3-inputs"))
import ai_review
from importlib.util import spec_from_file_location, module_from_spec
spec = spec_from_file_location("f3_queries", RUN / "f3-inputs/execute-queries.py")
queries = module_from_spec(spec)
spec.loader.exec_module(queries)
F3, ROOT, CLI = queries.F3, queries.ROOT, queries.CLI
ACTOR = "Codex /root/retrieval_review actual AI"
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def attempt():
    existing = list(Path(__file__).parent.glob("attempt-*/manifest.json"))
    if existing:
        return existing[0].parent
    return ai_review.initialize(RUN / "actual-ai", "A09", actor=ACTOR, model=None, context_mode="continuous",
        metadata_file=RUN / "f3-inputs/ai-input-environment.json")


def call(label, action, request=None, *, domain="material-query", inspect_args=None):
    target = attempt()
    argv = [sys.executable, "-X", "utf8", str(CLI)]
    if domain == "memory":
        argv += ["--root", str(ROOT)]
    argv += [domain, action]
    path = target / "authored-requests" / (label + ".json") if request is not None else None
    if path:
        write(path, request)
        argv += ["--request", str(path)]
    if inspect_args:
        argv += inspect_args
    folder, receipt = ai_review.capture_call(target, argv, path, cwd=ROOT)
    raw = json.loads((folder / "stdout.txt").read_bytes())
    write(target / "outcomes" / (label + ".json"), {"call": str(folder), "exit_code": receipt["exit_code"], "result": raw})
    return raw


def main():
    target = attempt()
    captured = queries.capture(target, "saturation-full", "search", queries.request("saturation", "full"), True)
    before = {alias: call("initial-" + alias, "inspect", domain="memory", inspect_args=[owner]) for alias, owner in F3["owners"].items()}
    write(target / "initial-owner-inspection.json", before)
    print(json.dumps({"attempt": str(target), "saturation": captured, "heads": {key: value["head"] for key, value in before.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
