"""Record actual AI product use without generating answers or judging success.

This standard-library CLI deliberately separates subprocess execution, declared
AI reading, AI assessment, and pending human review. Files are append-only: each
attempt, call, reading, and assessment receives its own UUID. It can be copied to
a Windows x64 source distribution without third-party dependencies.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


TEMPLATES = Path(__file__).parent / "templates"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    """Exclusive creation prevents retries from overwriting earlier evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def initialize(output, scenario, task_file=None, actor=None, model=None,
               context_mode="continuous", parent_attempt=None, metadata_file=None):
    """Freeze task and expectations before any product call; never prefill prose."""
    catalog = read_json(TEMPLATES / "ai-scenarios.json")
    definition = next((x for x in catalog["scenarios"] if x["id"] == scenario), None)
    if definition is None:
        raise ValueError("Unknown actual-AI scenario: " + scenario)
    attempt = Path(output).resolve() / scenario / ("attempt-" + uuid.uuid4().hex)
    attempt.mkdir(parents=True)
    task = Path(task_file).read_text(encoding="utf-8-sig") if task_file else definition["task"]
    (attempt / "task.txt").write_text(task, encoding="utf-8")
    manifest = {
        "schema_version": 1, "scenario": definition, "created_at": utc_now(),
        "attempt_id": attempt.name, "parent_attempt": parent_attempt,
        "task": {"path": "task.txt", "sha256": digest(attempt / "task.txt")},
        "template_sha256": digest(TEMPLATES / "ai-scenarios.json"),
        "actor": actor, "model": model, "context_mode": context_mode,
        "input_environment": read_json(metadata_file) if metadata_file else {},
        "execution": "not-run", "mechanical_checks": "not-run",
        "ai_assessment": "not-reviewed", "human_review": "pending",
        "scientific_review": "not-reviewed",
        "note": "Initial states are immutable; subsequent evidence is in uniquely named events."
    }
    write_new(attempt / "manifest.json", manifest)
    return attempt


def require_attempt(attempt):
    attempt = Path(attempt).resolve()
    read_json(attempt / "manifest.json")
    return attempt


def capture_call(attempt, argv, request=None, cwd=None, timeout=120):
    """Execute an explicit public-entry argv, preserving all outcomes including timeouts.

    shell=False avoids shell interpolation. This records evidence, not authorization
    or proof that the supplied command is a public product entry; the reviewer must
    inspect argv. The copied request is exactly AI-authored input, not transformed.
    """
    attempt = require_attempt(attempt)
    if not argv:
        raise ValueError("An explicit public CLI argv is required")
    call = attempt / "calls" / ("call-" + uuid.uuid4().hex)
    call.mkdir(parents=True)
    request_ref = None
    if request:
        original = Path(request).resolve()
        (call / "request.snapshot.txt").write_bytes(original.read_bytes())
        request_ref = {"original_path": str(original), "path": "request.snapshot.txt",
                       "sha256": digest(call / "request.snapshot.txt")}
    event = {"call_id": call.name, "argv": list(argv), "cwd": str(Path(cwd or ".").resolve()),
             "started_at": utc_now(), "timeout_seconds": timeout, "request": request_ref}
    write_new(call / "invocation.json", event)
    try:
        completed = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout, shell=False)
        out, err, code = completed.stdout, completed.stderr, completed.returncode
        status = "completed"
    except subprocess.TimeoutExpired as exc:
        out, err, code, status = exc.stdout or b"", exc.stderr or b"", None, "timeout"
    except OSError as exc:
        out, err, code, status = b"", str(exc).encode("utf-8"), None, "launch-error"
    (call / "stdout.txt").write_bytes(out)
    (call / "stderr.txt").write_bytes(err)
    result = {**event, "ended_at": utc_now(), "status": status, "exit_code": code,
              "stdout": {"path": "stdout.txt", "sha256": digest(call / "stdout.txt")},
              "stderr": {"path": "stderr.txt", "sha256": digest(call / "stderr.txt")},
              "ai_assessment": "not-reviewed", "human_review": "pending"}
    write_new(call / "result.json", result)
    return call, result


def record_read(attempt, event_file):
    """Archive the text/image actually presented to AI; do not infer reading from a download."""
    attempt = require_attempt(attempt)
    event_file = Path(event_file).resolve()
    event = read_json(event_file)
    for key in ("actor", "origin", "capture_path", "locator", "coverage", "observation"):
        if not event.get(key):
            raise ValueError("Reading event requires " + key)
    if event["coverage"] not in {"full", "partial", "summary", "not-read"}:
        raise ValueError("Invalid reading coverage")
    source = Path(event["capture_path"])
    source = source if source.is_absolute() else event_file.parent / source
    target = attempt / "reads" / ("read-" + uuid.uuid4().hex)
    target.mkdir(parents=True)
    # Safe suffix preserves image viewing; JSON snapshots are never business cards.
    suffix = source.suffix if source.suffix.lower() in {".png", ".jpg", ".webp"} else ".snapshot.txt"
    capture = target / ("capture" + suffix)
    capture.write_bytes(source.read_bytes())
    write_new(target / "event.json", {**event, "recorded_at": utc_now(),
              "capture_path": capture.name, "capture_sha256": digest(capture),
              "declaration": "Executor-declared actual reading; storage alone is not proof of reading."})
    return target


def record_assessment(attempt, assessment_file):
    """Accept explicit per-expectation AI observations, never generate or default to pass."""
    attempt = require_attempt(attempt)
    value = read_json(assessment_file)
    expected = {x["id"] for x in read_json(attempt / "manifest.json")["scenario"]["expectations"]}
    rows = value.get("comparisons", [])
    if not value.get("actor") or not isinstance(rows, list):
        raise ValueError("Assessment requires actor and comparisons")
    seen = set()
    for row in rows:
        if row.get("expectation_id") not in expected or row["expectation_id"] in seen:
            raise ValueError("Unknown or duplicate expectation")
        seen.add(row["expectation_id"])
        if row.get("status") not in {"meets", "does-not-meet", "cannot-assess"}:
            raise ValueError("Explicit AI status required")
        if not row.get("observation") or not row.get("evidence_refs"):
            raise ValueError("Each assessment requires observed facts and evidence refs")
    if seen != expected:
        raise ValueError("Assess every frozen expectation, using cannot-assess for gaps")
    if any(value.get(k) not in (None, "pending", "not-reviewed") for k in ("human_review", "scientific_review")):
        raise ValueError("AI assessment cannot set human or scientific acceptance")
    target = attempt / "assessments" / ("assessment-" + uuid.uuid4().hex + ".json")
    write_new(target, {**value, "recorded_at": utc_now(), "human_review": "pending",
                       "scientific_review": "not-reviewed"})
    return target


def render(output):
    """Render readable observations and links; no pass count conflates evidence layers."""
    output = Path(output).resolve()
    generation = output / "reports" / ("report-" + uuid.uuid4().hex)
    generation.mkdir(parents=True)
    def local_link(path):
        """Reports remain portable; never turn an arbitrary artifact path into a link."""
        target = Path(path)
        target = (target if target.is_absolute() else output / target).resolve()
        if not target.is_relative_to(output) or not target.is_file():
            raise ValueError("Report link must resolve to an existing file inside output: " + str(target))
        return os.path.relpath(target, generation).replace(os.sep, "/")
    lines = ["# 实际 AI 使用审查", "", "人工审查均待处理；AI自查不等于科学复核。", "",
             "| 场景 | 已保存调用 | 阅读事件 | AI自查 | 人工审查 |", "|---|---:|---:|---|---|"]
    for manifest_path in sorted(output.glob("A*/attempt-*/manifest.json")):
        attempt = manifest_path.parent
        meta = read_json(manifest_path)
        calls = sorted((attempt / "calls").glob("*/result.json"))
        reads = sorted((attempt / "reads").glob("*/event.json"))
        assessments = sorted((attempt / "assessments").glob("*.json"))
        assessments.sort(key=lambda p: read_json(p)["recorded_at"])
        assessment = read_json(assessments[-1]) if assessments else None
        page_name = meta["scenario"]["id"] + "-" + attempt.name + ".md"
        page = ["# " + meta["scenario"]["title"], "", "## 任务", "", (attempt / "task.txt").read_text(encoding="utf-8"),
                "", "## AI自查", ""]
        if assessment:
            page.extend(["## 已保存可读结果", ""])
            for artifact in assessment.get("readable_artifacts", []):
                page.append(f"- [{artifact['title']}](<{local_link(artifact['path'])}>)")
            page.extend(["", "## 逐项观察", ""])
            for row in assessment["comparisons"]:
                page.extend([f"- {row['expectation_id']}：{row['status']} — {row['observation']}",
                             "  证据：" + "; ".join(str(x) for x in row["evidence_refs"])])
            page.extend(["", "## 限制", ""] + ["- " + str(x) for x in assessment.get("limitations", [])])
        else:
            page.append("尚未提交实际 AI 自查；不推断结果。")
        page.extend(["", "## 实际调用与阅读", ""])
        for path in calls + reads + assessments:
            page.append(f"- [{path.parent.name}/{path.name}](<{local_link(path)}>)")
        page.extend(["", "## 人工审查", "", "待审查。请记录意见及所审固定版本；本工具不代填认可。", ""])
        (generation / page_name).write_text("\n".join(page), encoding="utf-8")
        status = ", ".join(sorted({r["status"] for r in assessment["comparisons"]})) if assessment else "未自查"
        lines.append(f"| [{meta['scenario']['title']}]({page_name}) | {len(calls)} | {len(reads)} | {status} | 待审查 |")
    (generation / "REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return generation / "REVIEW.md"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init", help="Freeze an actual-AI scenario before execution")
    init.add_argument("--output", required=True)
    init.add_argument("--scenario", required=True)
    init.add_argument("--task-file")
    init.add_argument("--actor")
    init.add_argument("--model")
    init.add_argument("--context-mode", choices=["continuous", "fresh"], default="continuous")
    init.add_argument("--parent-attempt")
    init.add_argument("--metadata-file", help="Actual input refs, Skill/source fingerprints and initial HEAD; unknown fields remain null")
    call = sub.add_parser("call", help="Record an explicit public CLI call, preserving failures")
    call.add_argument("--attempt", required=True)
    call.add_argument("--request")
    call.add_argument("--cwd")
    call.add_argument("--timeout", type=float, default=120)
    call.add_argument("argv", nargs=argparse.REMAINDER)
    for name in ("read", "assess"):
        item = sub.add_parser(name)
        item.add_argument("--attempt", required=True)
        item.add_argument("--input", required=True)
    report = sub.add_parser("render")
    report.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "init":
            result = initialize(args.output, args.scenario, args.task_file, args.actor, args.model, args.context_mode, args.parent_attempt, args.metadata_file)
        elif args.action == "call":
            command = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            result, receipt = capture_call(args.attempt, command, args.request, args.cwd, args.timeout)
            print(json.dumps({"evidence": str(result), "receipt": receipt}, ensure_ascii=False))
            return 0 if receipt["exit_code"] == 0 else 1
        elif args.action == "read":
            result = record_read(args.attempt, args.input)
        elif args.action == "assess":
            result = record_assessment(args.attempt, args.input)
        else:
            result = render(args.output)
        print(json.dumps({"path": str(result)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
