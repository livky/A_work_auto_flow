"""安装常用工作区 Skill 的轻量入口，详细方法始终维护在 workflows。

默认只预览；--apply 新建入口。拒绝覆盖内容不同的已有技能，不修改全局技能、
权限或客户端设置。仓库保留目录若只读，应按环境审批流程执行此具体安装。
"""
import argparse
import difflib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
# 默认发现入口与 --name 的允许集合使用同一登记；完整方法仍只维护在
# workflows，升级此脚本不会覆盖用户已修改的本地 Skill。
NAMES = ("workspace-context", "context-maintenance", "evidence-inspection", "research-loop", "development-checks",
         "material-query", "association-exploration", "semantic-maintenance")


def install(apply=False, names=None):
    entries = []
    selected = NAMES if names is None else tuple(dict.fromkeys(names))
    if not selected or not set(selected).issubset(NAMES):
        raise ValueError("只能安装已登记的工作区技能")
    for name in selected:
        source = ROOT / "automation/workflows" / name / "SKILL.md"
        text = source.read_text(encoding="utf-8")
        frontmatter = re.match(r"---\s*\n(.*?)\n---", text, re.S)
        if not frontmatter:
            raise ValueError(f"工作流缺少 frontmatter：{source}")
        target = ROOT / ".agents/skills" / name / "SKILL.md"
        content = "---\n" + frontmatter.group(1) + "\n---\n\n# 工作区技能入口\n\n" + (
            f"在含 workspace.json 的当前研发工作区使用。读取 [完整工作流](../../../automation/workflows/{name}/SKILL.md)，"
            "按本轮任务执行；根 AGENTS 与用户明确要求优先。本文件只用于技能发现，方法和命令在工作流源维护。\n")
        if target.exists():
            current = target.read_text(encoding="utf-8")
            if current != content:
                # 冲突仍在批次预检阶段阻止任何写入。只输出供用户合并的
                # 文本差异，不静默替换自定义规则，也不自动应用这些建议。
                difference = "".join(difflib.unified_diff(
                    current.splitlines(keepends=True), content.splitlines(keepends=True),
                    fromfile=str(target) + " (current, preserved)",
                    tofile=str(target) + " (generated proposal)", n=3))
                raise FileExistsError(
                    f"已有不同技能，拒绝覆盖：{target}\n请保留用户规则并按以下差异合并后重试：\n{difference}")
        entries.append((target, content))
    # 所有冲突先检查完，再进行批量写入。删除这些新入口即可撤销本次安装。
    for target, content in entries:
        print(("安装：" if apply else "预览：") + str(target))
        if apply and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--name", choices=NAMES, action="append", help="只安装指定入口，保留其他本地修改；可重复")
    args = parser.parse_args()
    try:
        install(args.apply, args.name)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
