"""验证 v0.1 公共基线和继承覆盖，不执行任何产品后端。

用法（工作区根目录）：
    automation/python.ps1 docs/design/representation-query-v0.2/baseline-v0.1/check_inheritance.py
    .../check_inheritance.py --out <本轮检查回执.json>

默认只读。--out 仅保存本次真实结构检查回执，不生成产品通过率、不修改原基线。
退出码：0=本检查范围通过；1=缺号、重复、坏链接、输入漂移或指纹不一致。
仅依赖 Python 标准库，兼容 Windows x64 的便携解释器。
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote


HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
ROOT = HERE.parents[3]


def load_json(path: Path) -> object:
    """统一按 UTF-8 读取；错误应由主入口转为失败回执，不能当成空配置。"""
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    """字节 SHA256 只验证版本，不解释为研究内容已经复核。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def controlled_path(base: Path, relative: str) -> Path:
    """拒绝绝对路径和越界路径；清单不授予访问工作区之外文件的权限。"""
    candidate = (base / relative).resolve()
    if Path(relative).is_absolute() or not candidate.is_relative_to(base.resolve()):
        raise ValueError(f"Path outside controlled root: {relative}")
    return candidate


def protocol_methods(path: Path) -> set[str]:
    """从保存的原语法树提取签名身份，避免用手工数字冒充实际覆盖。"""
    module = ast.parse(path.read_text(encoding="utf-8"))
    return {
        f"{cls.name}.{method.name}"
        for cls in module.body
        if isinstance(cls, ast.ClassDef)
        for method in cls.body
        if isinstance(method, ast.FunctionDef)
    }


def check() -> dict:
    mapping = load_json(DESIGN / "inheritance-map.json")
    catalog = load_json(HERE / "function-catalog.json")
    manifest = load_json(HERE / "source-manifest.json")
    q_cases = load_json(DESIGN / "test-cases.json")
    errors: list[str] = []
    methods = protocol_methods(HERE / "contract_ports.py")
    catalog_methods = {row["method"] for row in catalog["functions"]}
    expected_groups = {"X01", *(f"G{i:02d}" for i in range(1, 13))}
    expected_acceptance = set(re.findall(
        r"^\|\s*(C\d{2})\s*\|",
        (HERE / "IMPLEMENTATION.md").read_text(encoding="utf-8"),
        re.MULTILINE,
    ))
    q_ids = {row["id"] for row in q_cases}
    gap_ids = {row["id"] for row in mapping["gaps"]}
    dispositions = {"保留", "细化", "替换", "延期"}

    def require_ids(rows: list[dict], key: str, expected: set[str], label: str) -> None:
        """同时检查集合和重复；仅总数相同不足以说明逐项继承。"""
        values = [row[key] for row in rows]
        repeated = [value for value, count in Counter(values).items() if count != 1]
        if repeated:
            errors.append(f"{label}: duplicate IDs {repeated}")
        if set(values) != expected:
            errors.append(
                f"{label}: missing={sorted(expected - set(values))}; "
                f"extra={sorted(set(values) - expected)}"
            )

    if methods != catalog_methods or len(methods) != 43:
        errors.append("Original method catalog/Protocol mismatch or unexpected method count")
    if expected_acceptance != {f"C{i:02d}" for i in range(1, 27)}:
        errors.append("Original C01-C26 set is incomplete")
    require_ids(mapping["groups"], "id", expected_groups, "groups")
    require_ids(mapping["methods"], "method", methods, "methods")
    require_ids(mapping["acceptance"], "id", expected_acceptance, "acceptance")

    # 验收映射允许明确存在设计缺口，但不允许把缺口抹成已通过。
    for collection in ("groups", "methods", "acceptance"):
        for row in mapping[collection]:
            identity = row.get("method", row.get("id"))
            if row.get("disposition") not in dispositions:
                errors.append(f"{identity}: missing/invalid disposition")
            if not row.get("reason") or not row.get("implementation_targets"):
                errors.append(f"{identity}: missing reason or implementation target")
            if not row.get("q_ids"):
                errors.append(f"{identity}: no explicit Q mapping")
            unknown_q = set(row.get("q_ids", ())) - q_ids
            unknown_gaps = set(row.get("gap_ids", ())) - gap_ids
            if unknown_q or unknown_gaps:
                errors.append(
                    f"{identity}: unknown Q={sorted(unknown_q)}, gaps={sorted(unknown_gaps)}"
                )
            if row.get("disposition") == "延期":
                errors.append(f"{identity}: this implementation scope does not defer old behavior")
            if row.get("test_status") != "not_run" and not row.get("test_ids"):
                errors.append(f"{identity}: test status advanced without real test IDs")

    for group in mapping["groups"]:
        actual = {row["method"] for row in mapping["methods"] if row["group"] == group["id"]}
        original = {row["method"] for row in catalog["functions"] if row["group"] == group["id"]}
        if set(group["methods"]) != actual or actual != original:
            errors.append(f"{group['id']}: method membership differs from original catalog")

    for gap in mapping["gaps"]:
        if not gap.get("minimum_fields") or not gap.get("minimum_signatures"):
            errors.append(f"{gap['id']}: missing actionable field/signature detail")
        if not gap.get("required_assertions"):
            errors.append(f"{gap['id']}: no observable assertion")
        if set(gap["q_ids"]) - q_ids or set(gap["c_ids"]) - expected_acceptance:
            errors.append(f"{gap['id']}: unknown acceptance reference")

    # 副本始终可单独验证。完整 checkout 可进一步比原件；公共发行包没有 Project
    # 时只明确记录原件不可用，不能据副本正确谎称检查过未分发的研究实例。
    baseline_results = []
    if len(manifest["files"]) != 12:
        errors.append("Public baseline must preserve all 12 original files")
    for entry in manifest["files"]:
        public_file = controlled_path(HERE, entry["name"])
        original_file = controlled_path(ROOT, entry["source_path"])
        public_ok = public_file.is_file() and digest(public_file) == entry["public_sha256"]
        original_available = original_file.is_file()
        original_ok = None
        transform_ok = None
        if not public_ok:
            errors.append(f"{entry['name']}: public fingerprint mismatch")
        if original_available:
            original_ok = digest(original_file) == entry["source_sha256"]
            if not original_ok:
                errors.append(f"{entry['name']}: original source fingerprint changed")
            if entry["navigation_edits"]:
                transformed = original_file.read_bytes().decode("utf-8")
                for edit in entry["navigation_edits"]:
                    transformed = transformed.replace(edit["before"], edit["after"])
                transform_ok = transformed.encode("utf-8") == public_file.read_bytes()
            else:
                transform_ok = original_file.read_bytes() == public_file.read_bytes()
            if not transform_ok:
                errors.append(f"{entry['name']}: copy differs beyond declared navigation edits")
        baseline_results.append({
            "name": entry["name"], "public_sha256_matches": public_ok,
            "original_available": original_available,
            "original_sha256_matches": original_ok,
            "declared_copy_transform_matches": transform_ok,
        })

    # 已发生的设计输入漂移必须重审映射，不能因为旧编号仍存在就继续称完整。
    input_results = []
    for entry in mapping["source_inputs"]:
        path = controlled_path(ROOT, entry["path"])
        actual = digest(path) if path.is_file() else None
        matched = actual == entry["sha256"]
        input_results.append({"path": entry["path"], "matches": matched, "actual_sha256": actual})
        if not matched:
            errors.append(f"Mapping input changed or missing: {entry['path']}")

    # 链接核验只检查本地目标存在；网络可用性和 Markdown 锚点渲染不属于本检查。
    link_results = []
    markdown_files = [DESIGN / "INHERITANCE.md", *sorted(HERE.glob("*.md"))]
    for path in markdown_files:
        for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)\n]+)\)", path.read_text(encoding="utf-8")):
            target = target.strip().strip("<>")
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
                continue
            relative = unquote(target.split("#", 1)[0])
            target_path = (path.parent / relative).resolve()
            exists = target_path.exists()
            link_results.append({
                "from": path.relative_to(ROOT).as_posix(), "target": target, "exists": exists
            })
            if not target_path.is_relative_to(ROOT):
                errors.append(f"Local link leaves workspace: {target}")
            elif not exists:
                errors.append(f"Missing local link: {path.name} -> {target}")

    # 文件存在性只是落点观察，不用它判断函数是否已装配、权限是否已执行。
    runtime_paths = sorted({
        target["path"]
        for method in mapping["methods"]
        for target in method["implementation_targets"]
    })
    runtime_targets = [
        {"path": relative, "exists": controlled_path(ROOT, relative).is_file(),
         "behavior_verified": False}
        for relative in runtime_paths
    ]
    return {
        "status": "passed" if not errors else "failed",
        "scope": "inheritance identifiers, obligations, declared-copy fingerprints and local links only",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "run_id": mapping["implementation_run_id"],
        "groups": len(mapping["groups"]),
        "methods": len(methods),
        "acceptance": len(expected_acceptance),
        "q_cases": len(q_cases),
        "direct_design_mappings": sum(row["design_coverage"] == "direct" for row in mapping["acceptance"]),
        "partial_design_mappings": sum(row["design_coverage"] == "partial" for row in mapping["acceptance"]),
        "open_runtime_obligation_groups": len(mapping["gaps"]),
        "baseline_files": baseline_results,
        "mapping_inputs": input_results,
        "local_links": link_results,
        "runtime_target_observations": runtime_targets,
        "errors": errors,
        "not_tested": [
            "Runtime adapter behavior", "Product backend conformance", "Actual AI review",
            "Retrieval quality or performance", "P6 release archive or real setup upgrade",
            "External source contents", "Human or scientific acceptance",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="保存本次结构检查回执；默认不写文件")
    args = parser.parse_args()
    try:
        result = check()
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {"status": "failed", "scope": "inheritance structure only", "errors": [str(error)]}
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

