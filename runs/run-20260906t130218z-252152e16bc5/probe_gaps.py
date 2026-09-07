"""在临时合成工作区复现架构边界，不读取真实业务材料。

用法：automation/python.ps1 <本脚本> --output <结果 JSON>
输出是观测事实，不是业务正确性测试。退出码 0 表示探针执行完成，
2 表示输入或运行失败；不将“发现缺口”混同于脚本失败。
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "automation/scripts"))
import retrieval as retrieval
import workspace_cli as cli


def write(path: Path, value: object) -> None:
    """只向本探针控制的临时目录写合成 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(Path(__file__).resolve().parent):
        parser.error("结果只能写入本 Run 目录")
    scratch = (WORKSPACE / "tmp").resolve()
    scratch.mkdir(exist_ok=True)
    results = {}
    # 临时目录在已确认的 workspace/tmp 内；进入后再次检查绝对路径，
    # 确保 TemporaryDirectory 自动清理的目标不会越出指定临时范围。
    with tempfile.TemporaryDirectory(prefix="review-probe-", dir=scratch) as name:
        root = Path(name).resolve()
        if not root.is_relative_to(scratch) or root == scratch:
            raise ValueError("临时目录边界检查失败")
        write(root / "workspace.json", {"required_paths": []})
        write(root / "tools/registry.json", {"tools": []})
        cfg = retrieval.read_json(WORKSPACE / "retrieval/config.json")
        # 本次只检查元数据和依赖传播，不冒充验证真实向量模型。
        cfg.update(include_directories=["runs", "research"], vector_store={}, embedding={}, ocr_enabled=False)
        write(root / "retrieval/config.json", cfg)
        write(root / "retrieval/sources.json", {"sources": []})
        with redirect_stdout(io.StringIO()):
            run_dir = cli.create_run(root, None, "合成阈值验证")
        run_path = run_dir / "run.json"
        record = retrieval.read_json(run_path)
        record.update(status="succeeded", conclusion="合成阈值 123 可用于全部工况")
        write(run_path, record)
        errors, warnings = cli.validate_workspace(root)
        results["incomplete_succeeded_run"] = {
            "empty_fields": [key for key in ("inputs", "artifacts", "quality_results") if not record[key]],
            "validation_errors": errors, "validation_warnings": warnings,
        }

        # 显式撤回原 Run，再让研究综合通过真实链接引用它。
        # 检查上下文条目是否继承撤回风险，既看 Run 也看研究综合。
        record["review"] = {"status": "retracted", "reviewer": "synthetic-probe", "reason": "合成反证"}
        write(run_path, record)
        research_dir = root / "research/probe"
        write(research_dir / "research.json", {
            "research_id": "RES-PROBE", "sensitivity": "restricted", "related_module_ids": [],
        })
        synthesis = research_dir / "SYNTHESIS.md"
        synthesis.write_text(
            "# 合成研究综合\n\n合成阈值 123 可用于全部工况。\n"
            f"来源：[原始 Run](../../runs/{run_dir.name}/run.json)\n", encoding="utf-8")
        result = retrieval.search(root, "合成阈值", record=False)
        pack = retrieval.assemble(root, result, budget=40000)
        relevant = [entry for entry in pack["manifest"]["sources"]
                    if entry.get("path") in {str(run_path), str(synthesis)}]
        results["retraction_scope"] = [{
            "path": Path(entry["path"]).relative_to(root).as_posix(),
            "mode": entry["mode"], "review": entry.get("review"),
            "blocking_run_ids": entry.get("blocking_run_ids"),
        } for entry in relevant]

        # 分级标签是策略数据；该探针不创建任何真实敏感信息。
        # 观测其是否成为索引的权限过滤字段，不判断当前用户实际授权。
        with retrieval.closing(retrieval.connect(root)) as db:
            docs = retrieval.read_docs(db)
        research_doc = next(doc for doc in docs.values() if doc["path"] == str(synthesis))
        results["sensitivity_metadata"] = {
            "source_card_sensitivity": "restricted", "indexed_state": research_doc["state"],
            "indexed_sensitivity": research_doc["meta"].get("sensitivity"),
        }

        before = retrieval.source_id(root / "research/probe/SYNTHESIS.md")
        after = retrieval.source_id(root / "relocated/research/probe/SYNTHESIS.md")
        results["relocated_source_id"] = {"same_logical_file_different_path_has_same_id": before == after}
        write(output, results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"探针失败：{exc}", file=sys.stderr)
        raise SystemExit(2)
