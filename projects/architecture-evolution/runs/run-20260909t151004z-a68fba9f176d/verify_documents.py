"""Check this documentation change without modifying product or historical data.

Run from any directory with the workspace Python wrapper. --out selects the
new receipt only; source files are read-only. Exit 1 means an observed failure.
This bounded check is not a Markdown renderer or a product behavior test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import unquote


def digest(path):
    """Hash actual bytes; text newline normalization would hide real changes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    project = root / "projects/architecture-evolution"
    git = ["git", "-c", f"safe.directory={root.as_posix()}", "-c", "core.safecrlf=false", "-C", str(root)]
    changed = subprocess.check_output(git + ["diff", "--name-only", "-z", "HEAD"]).decode().split("\0")
    changed = [p for p in changed if p]
    # Historical design bodies retain old links as evidence. Current navigation,
    # all changed non-design Markdown, and the new Project are checked here.
    paths = {root / p for p in changed if p.endswith(".md") and not p.startswith("docs/design/")}
    paths.add(root / "docs/DOCUMENTATION_MAINTENANCE.md")
    paths.update(project.rglob("*.md"))
    paths = sorted(p for p in paths if not (
        p.is_relative_to(project) and "artifacts" in p.relative_to(project).parts
    ))
    failures, links, skipped = [], [], []
    for path in paths:
        body = path.read_text(encoding="utf-8-sig")
        # Fenced examples are illustrative inputs, not navigation links.
        prose = re.sub(r"^```[^\n]*\n.*?^```\s*$", "", body, flags=re.M | re.S)
        for match in re.finditer(r"\[[^\]\n]*\]\(([^)\n]+)\)", prose):
            target = match.group(1).strip().strip("<>")
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            target = unquote(target.split(' "', 1)[0])
            relative, _, anchor = target.partition("#")
            candidate = (path.parent / relative).resolve() if relative else path
            entry = {"source": path.relative_to(root).as_posix(), "target": target}
            # Generated console logs are intentionally ignored by Git. Their
            # absence is reported, not reclassified as a successful link.
            if not candidate.exists() and candidate.suffix == ".log":
                skipped.append({**entry, "reason": "runtime log absent; result JSON is authoritative"})
            elif not candidate.exists():
                failures.append({**entry, "reason": "missing local target"})
            else:
                links.append(entry)
    inventory = json.loads((project / "docs/document-inventory.json").read_text(encoding="utf-8-sig"))
    entries = inventory["entries"]
    inventory_mismatch = [item["path"] for item in entries if digest(root / item["path"]) != item["sha256"]]
    inventory_paths = {item["path"] for item in entries}
    actual_paths = {p.relative_to(root).as_posix() for p in (root / "docs").rglob("*") if p.is_file()}
    coverage_mismatch = sorted(inventory_paths ^ actual_paths)
    # Product code, schemas, dependency locks and frozen fixtures must remain
    # byte-identical to HEAD. This list deliberately does not ignore JSON changes.
    # refresh-index legitimately updates this derived JSON when the new Project
    # Run is added. No other non-Markdown tracked file is allowed by this check.
    allowed_generated = {"context/generated/run-index.json"}
    unexpected_changes = [p for p in changed if not p.endswith(".md") and p not in allowed_generated]
    fixture_changes = [p for p in changed if p.startswith("docs/design/system-memory/fixtures/")]
    map_body = (project / "context/MODULE_IMPACT.md").read_text(encoding="utf-8")
    code_paths = sorted(set(re.findall(r"`([^`]+\.py)`", map_body)))
    missing_code_paths = [p for p in code_paths if not (root / "automation/scripts" / p).exists()]
    checks = {
        "local_link_failures": failures,
        "inventory_fingerprint_mismatch": inventory_mismatch,
        "inventory_coverage_mismatch": coverage_mismatch,
        "unexpected_tracked_non_markdown_changes": unexpected_changes,
        "frozen_fixture_changes": fixture_changes,
        "missing_map_code_paths": missing_code_paths,
    }
    result = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not any(checks.values()) else "failed",
        "scope": "current working-tree documentation change against HEAD and final docs inventory",
        "markdown_files_checked": len(paths), "local_links_checked": len(links),
        "inventory_files_checked": len(entries), "map_code_paths_checked": len(code_paths),
        "files": [p.relative_to(root).as_posix() for p in paths],
        "allowed_changed_generated_files": sorted(set(changed) & allowed_generated),
        "checks": checks, "skipped_links": skipped,
        "limitations": ["Local targets only; HTTP links, reference-style links and anchor rendering are not validated by this script.",
                        "Historical fixture-manifest mismatch is recorded separately; unchanged bytes do not establish fixture validity.",
                        "No UI, live AI behavior, retrieval quality or second-machine acceptance is established."],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"files", "limitations"}}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
