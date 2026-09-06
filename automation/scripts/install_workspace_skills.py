"""安装两个常用工作区 Skill 的轻量入口，详细方法始终维护在 workflows。

默认只预览；--apply 新建入口。拒绝覆盖内容不同的已有技能，不修改全局技能、
权限或客户端设置。仓库保留目录若只读，应按环境审批流程执行此具体安装。
"""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("workspace-context", "context-maintenance")


def install(apply=False):
    entries = []
    for name in NAMES:
        source = ROOT / "automation/workflows" / name / "SKILL.md"
        text = source.read_text(encoding="utf-8")
        frontmatter = re.match(r"---\s*\n(.*?)\n---", text, re.S)
        if not frontmatter:
            raise ValueError(f"工作流缺少 frontmatter：{source}")
        target = ROOT / ".agents/skills" / name / "SKILL.md"
        content = "---\n" + frontmatter.group(1) + "\n---\n\n# 工作区技能入口\n\n" + (
            f"在含 workspace.json 的当前研发工作区使用。读取 [完整工作流](../../../automation/workflows/{name}/SKILL.md)，"
            "按本轮任务执行；根 AGENTS 与用户明确要求优先。本文件只用于技能发现，方法和命令在工作流源维护。\n")
        if target.exists() and target.read_text(encoding="utf-8") != content:
            raise FileExistsError(f"已有不同技能，拒绝覆盖：{target}")
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
    args = parser.parse_args()
    try:
        install(args.apply)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
