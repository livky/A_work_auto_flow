"""建立本Run的实际AI记录场景并公开读取当前Project；不生成自评或通过状态。

本脚本只封存任务、环境和CLI调用。后续技术正文由当前助手撰写并明确提交；
AI阅读声明与逐项判断必须在实际查看输出后另行记录。已有场景不得覆盖。
"""
import hashlib
import json
from pathlib import Path
import sys

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
sys.path.insert(0, str(ROOT / "automation/testing"))
import ai_review


def main():
    marker = RUN / "project-recording-attempts.json"
    if marker.exists():
        raise RuntimeError("实际场景已建立，请使用已有记录继续，不重新初始化")
    tasks = {
        "A01": "将本轮表示查询开发的实际实现、失败/修复及验证范围保存到PRJ-ARCHITECTURE-EVOLUTION。只使用公共memory预检、提交、inspect和固定引用expand；旧记录/原件保留，未知结果留空，不将软件通过写为科学认可。",
        "A03": "为本轮应用契约与范围/预算、局部证据与事务维护、工作台及验证建立可独立阅读的技术单元与章节。写明变量和公式、实际测试入口、失败案例和适用边界，公开保存后按块展开核对必要定义。",
        "A04": "将新开发技术章节接入既有Project完整研究过程和简版报告，共享相同固定依据，保留此前内容及历史修订。公开回读两份文稿，并实际检查工作台阅读效果；不能把AI自查标为人工确认。",
    }
    fingerprints = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        "automation/workflows/development-checks/SKILL.md", "automation/workflows/context-maintenance/SKILL.md",
        "automation/workflows/material-query/SKILL.md", "automation/schemas/memory-v3.schema.json")}
    metadata = RUN / "project-recording-inputs.json"
    ai_review.write_new(metadata, {"owner_id": "PRJ-ARCHITECTURE-EVOLUTION", "run_id": "RUN-20260909T194710Z-3CF36B2FDD60",
        "input_fingerprints": fingerprints, "model": None, "context": "continuous; actual implementation discussion available",
        "scientific_review": "not-reviewed", "human_review": "pending"})
    attempts = {}
    for scenario, task in tasks.items():
        task_file = RUN / (scenario + "-project-task.txt")
        task_file.write_text(task, encoding="utf-8")
        attempts[scenario] = str(ai_review.initialize(RUN / "actual-ai", scenario, task_file=task_file,
            actor="Codex主任务助手", model=None, context_mode="continuous", metadata_file=metadata))
    ai_review.write_new(marker, attempts)
    call, receipt = ai_review.capture_call(attempts["A01"], [sys.executable, str(ROOT / "automation/scripts/workspace_cli.py"),
        "memory", "inspect", "PRJ-ARCHITECTURE-EVOLUTION"], cwd=ROOT)
    state = json.loads((call / "stdout.txt").read_text(encoding="utf-8-sig"))
    ai_review.write_new(RUN / "project-recording-baseline.json", {"call": str(call), "exit_code": receipt["exit_code"],
        "head": state.get("head"), "records": [{"id": row["record_id"], "revision": row["revision"], "kind": row["kind"],
            "title": row["title"], "sha256": row["record_hash"]} for row in state.get("records", {}).values()]})
    print(json.dumps({"attempts": attempts, "head": state.get("head"), "records": len(state.get("records", {})), "call": str(call)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
