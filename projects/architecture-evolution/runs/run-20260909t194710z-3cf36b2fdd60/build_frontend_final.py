"""顺序生成契约、检查类型并构建工作台；保留每步原始输出，失败立即停止。"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", required=True, help="已安装的Node可执行文件；不安装/联网")
    parser.add_argument("--out", required=True, help="本Run下不存在的新回执目录")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if not out.is_relative_to(RUN) or out.exists():
        parser.error("输出必须是本Run下的新目录，不覆盖旧回执")
    # Vite only regenerates this controlled artifact directory; never point
    # emptyOutDir at the workspace itself or a business-data directory.
    assets = (ROOT / "automation/ui/workbench-assets").resolve()
    if not assets.is_relative_to(ROOT) or assets == ROOT:
        parser.error("构建资源目录超出工作区")
    out.mkdir(parents=True)
    frontend = ROOT / "automation/frontend"
    commands = [([sys.executable, str(ROOT / "automation/scripts/material_query/generate_types.py")], ROOT),
                ([args.node, "scripts/contracts.mjs"], frontend),
                ([args.node, "node_modules/typescript/bin/tsc", "--noEmit"], frontend),
                ([args.node, "node_modules/vite/bin/vite.js", "build"], frontend)]
    receipt = {"started_at": datetime.now(timezone.utc).isoformat(), "status": "running", "steps": []}
    for number, (command, cwd) in enumerate(commands, 1):
        started = time.monotonic()
        done = subprocess.run(command, cwd=cwd, capture_output=True)
        stdout, stderr = f"{number:02d}-stdout.txt", f"{number:02d}-stderr.txt"
        (out / stdout).write_bytes(done.stdout)
        (out / stderr).write_bytes(done.stderr)
        receipt["steps"].append({"command": command, "cwd": str(cwd), "exit_code": done.returncode,
                                 "elapsed_seconds": round(time.monotonic() - started, 3), "stdout": stdout, "stderr": stderr})
        receipt["status"] = "failed" if done.returncode else "running"
        (out / "results.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if done.returncode:
            print(json.dumps({"status": "failed", "step": number, "receipt": str(out / "results.json")}, ensure_ascii=False))
            return done.returncode
    receipt.update(status="passed", finished_at=datetime.now(timezone.utc).isoformat())
    (out / "asset-manifest.json").write_bytes((assets / "asset-manifest.json").read_bytes())
    (out / "results.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "steps": len(commands), "receipt": str(out / "results.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
