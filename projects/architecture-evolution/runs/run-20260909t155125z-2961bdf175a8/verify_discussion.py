"""核对本 Run 的来源、文稿链接与代码边界，生成 discussion-checks.json。

这是研究产物的静态检查，不执行产品、模型或检索性能测试。
从工作区根目录运行；输入只读，输出限定为本 Run 的检查回执。
退出码 0 表示所列静态检查通过，1 表示发现问题。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="工作区根目录")
    args = parser.parse_args()
    root = args.root.resolve()
    run_dir = Path(__file__).resolve().parent
    problems: list[str] = []

    # 只核对本次交付与显式导航，不递归读取历史文稿或外部业务材料。
    markdown_paths = sorted(run_dir.glob("*.md")) + [
        root / "projects/architecture-evolution/README.md",
        root / "projects/architecture-evolution/plans/abstract-interfaces.md",
    ]
    local_links = 0
    footnote_count = 0
    for path in markdown_paths:
        body = path.read_text(encoding="utf-8-sig")
        definitions = re.findall(r"^\[\^([^\]]+)\]:", body, re.MULTILINE)
        uses = re.findall(r"\[\^([^\]]+)\](?!:)", body)
        footnote_count += len(definitions)
        if len(set(definitions)) != len(definitions):
            problems.append(f"Duplicate footnote definition: {path.name}")
        for missing in sorted(set(uses) - set(definitions)):
            problems.append(f"Undefined footnote {missing}: {path.name}")
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", body):
            target = target.strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("#"):
                continue
            local_links += 1
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if not resolved.exists():
                problems.append(f"Missing local target: {path.name} -> {target}")

    json_paths = sorted(run_dir.glob("*.json"))
    for path in json_paths:
        # 上次的回执在重跑时不是输入，避免检查输出自身形成循环依据。
        if path.name != "discussion-checks.json":
            json.loads(path.read_text(encoding="utf-8-sig"))
    sources = json.loads((run_dir / "sources.json").read_text(encoding="utf-8-sig"))
    source_rows = sources["sources"]
    if len(source_rows) != len({item["url"] for item in source_rows}):
        problems.append("Duplicate primary source URLs")
    for item in source_rows:
        if not item.get("title") or not item.get("examined_version"):
            problems.append(f"Incomplete source metadata: {item.get('source_id')}")

    required = [
        "DISCUSSION.md", "retrieval-boundaries.md", "storage-boundaries.md",
        "graph-research.md", "graph-sources.json", "retrieval-research.md",
        "sources.json", "validation.txt", "baseline/ARCHITECTURE.md.snapshot",
        "baseline/MODULE_IMPACT-v1.md.snapshot",
    ]
    for relative in required:
        if not (run_dir / relative).is_file():
            problems.append(f"Missing deliverable: {relative}")

    # 记录真实执行的 Git 只读命令；原有文档改动不当作本轮程序实现。
    git_prefix = ["git", "-c", f"safe.directory={root.as_posix()}", "-c", "core.safecrlf=false"]
    product_command = git_prefix + [
        "diff", "--name-only", "HEAD", "--", "automation/scripts", "automation/schemas",
        "automation/tests", "workbench", "setup.cmd",
    ]
    product_result = subprocess.run(product_command, cwd=root, capture_output=True, text=True, encoding="utf-8")
    if product_result.returncode or product_result.stdout.strip():
        problems.append("Product paths differ from HEAD or Git inspection failed")
    diff_command = git_prefix + ["diff", "--check"]
    diff_result = subprocess.run(diff_command, cwd=root, capture_output=True, text=True, encoding="utf-8")
    if diff_result.returncode:
        problems.append("Git diff whitespace check failed")

    # 前一轮记录是固定输入历史；只回读已登记文件，绝不改写旧 Run 清单。
    old_run_path = root / "projects/architecture-evolution/runs/run-20260909t151004z-a68fba9f176d/run.json"
    old_run = json.loads(old_run_path.read_text(encoding="utf-8-sig"))
    old_files_checked = 0
    for item in old_run["inputs"] + old_run["artifacts"]:
        path = root / item["path"]
        old_files_checked += 1
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            problems.append(f"Prior Run fingerprint mismatch: {item['path']}")

    result = {
        "schema_version": 1,
        "run_id": "RUN-20260909T155125Z-2961BDF175A8",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not problems else "failed",
        "scope": "Research artifacts and static source boundaries only",
        "counts": {"markdown_files": len(markdown_paths), "local_links": local_links,
                   "footnote_definitions": footnote_count, "primary_sources": len(source_rows),
                   "prior_run_fingerprints": old_files_checked},
        "commands": [{"argv": product_command, "exit_code": product_result.returncode,
                      "stdout": product_result.stdout, "stderr": product_result.stderr},
                     {"argv": diff_command, "exit_code": diff_result.returncode,
                      "stdout": diff_result.stdout, "stderr": diff_result.stderr}],
        "independent_ai_static_review": [
            {"reviewer": "memory_review", "scope": "Version content, review and recovery boundaries",
             "reported_result": "No material issue found; not a runtime or human acceptance test"},
            {"reviewer": "retrieval_review", "scope": "Retrieval boundaries and proposed call graph",
             "reported_result": "One P2: missing application entry to projection maintenance; resolved by adding the explicit application call and post-commit orchestration explanation"},
        ],
        "not_executed": ["Product tests", "Live AI behavior", "Performance and retrieval benchmark",
                         "Concurrency and recovery tests", "Windows setup upgrade", "Second physical machine"],
        "human_review": "pending",
        "problems": problems,
    }
    (run_dir / "discussion-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], **result["counts"], "problems": problems}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
