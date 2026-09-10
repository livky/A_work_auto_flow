"""只读检查设计包；不执行产品算法，不把用例设计计为行为通过。

用法：automation/python.ps1 docs/design/representation-query-v0.2/check_design.py
可用 --out 将检查回执写入新文件；拒绝覆盖，失败退出 1，成功退出 0。
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import typing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    errors = []
    # embedded Python 不自动将脚本目录加入 sys.path；显式加载唯一设计模块。
    spec = importlib.util.spec_from_file_location("representation_design", root / "contracts.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    methods = []
    for name, value in vars(module).items():
        if isinstance(value, type) and value.__module__ == module.__name__:
            typing.get_type_hints(value)
            for method, function in vars(value).items():
                if callable(function) and not method.startswith("_"):
                    typing.get_type_hints(function)
                    methods.append(f"{name}.{method}")
    cases = json.loads((root / "test-cases.json").read_text(encoding="utf-8"))
    ids = set()
    coverage = set()
    for case in cases:
        if case["id"] in ids:
            errors.append("duplicate ID: " + case["id"])
        ids.add(case["id"])
        for field in ("requirement", "fixture", "action", "expected", "tier", "status", "ports"):
            if not case.get(field):
                errors.append(case["id"] + " missing " + field)
        if case.get("status") != "designed_not_run":
            errors.append(case["id"] + " must not claim execution")
        coverage.update(case["ports"])
    for method in methods:
        if method not in coverage:
            errors.append("method has no designed case: " + method)
    unknown = coverage - set(methods)
    if unknown:
        errors.append("unknown ports: " + repr(sorted(unknown)))
    result = {"status": "failed" if errors else "passed", "scope": "design_structure_only",
              "designed_cases": len(cases), "protocol_methods": len(methods),
              "product_behavior_tests_executed": 0, "errors": errors}
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(output)
    print(output)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
