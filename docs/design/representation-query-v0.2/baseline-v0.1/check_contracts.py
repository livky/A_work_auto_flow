"""核对设计端口/字段/函数目录和合成请求；不执行产品后端。

用法：python check_contracts.py [--write] [--out 检查回执.json]
--write 仅刷新本设计目录的 FUNCTIONS.md / DATATYPES.md；默认只读核对。
退出码 0=所列静态/请求结构检查通过，1=不一致。无第三方依赖或网络。
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import datetime as dt
import hashlib
import inspect
import json
from pathlib import Path
import re
import sys
import types
import typing

HERE = Path(__file__).resolve().parent
# Windows 便携解释器可通过 ._pth 关闭脚本目录注入；仅添加当前设计目录。
sys.path.insert(0, str(HERE))
import contract_types as t
import contract_ports as ports


def signatures() -> dict[str, tuple[list[dict[str, str]], str]]:
    """直接从 Protocol 的语法树取签名，避免维护另一份手抄字段。"""
    tree = ast.parse((HERE / "contract_ports.py").read_text(encoding="utf-8"))
    out = {}
    for cls in (item for item in tree.body if isinstance(item, ast.ClassDef)):
        for method in (item for item in cls.body if isinstance(item, ast.FunctionDef)):
            args = [{"name": arg.arg, "type": ast.unparse(arg.annotation)}
                    for arg in method.args.args if arg.arg != "self"]
            out[f"{cls.name}.{method.name}"] = (args, ast.unparse(method.returns))
    return out


def render(catalog: dict, methods: dict) -> dict[str, str]:
    function_lines = ["# 逐函数设计目录", "", "由 contract_ports.py 与 function-catalog.json 生成；所有端口尚未接入产品。输入类型的全部字段见 DATATYPES.md，行为共同约束见 SPEC.md。", ""]
    for group in catalog["groups"]:
        function_lines += [f"## {group['id']} {group['title']}", "", group["invariant"], "", f"实现落点（待拆分/适配）：`{group['implementation_anchor']}`。", ""]
        for row in (r for r in catalog["functions"] if r["group"] == group["id"]):
            args, returns = methods[row["method"]]
            signature = row["method"] + "(" + ", ".join(a["name"] + ": " + a["type"] for a in args) + ") -> " + returns
            function_lines += [f"### {row['method']}", "", "```python", signature, "```", "",
                f"- 抽象判断：{row['reason']}。", f"- 前置条件：{row['precondition']}。",
                f"- 返回保证：{row['postcondition']}。", f"- 调用：{'；'.join(row['calls'])}。",
                f"- 主要错误：{', '.join(row['errors'])}。", ""]
    function_lines += ["## 已遍历但不单独增加的函数", "", "| 候选 | 处理 | 理由 |", "|---|---|---|"]
    for row in catalog["alternatives"]:
        function_lines.append(f"| {row['name']} | {row['decision']} | {row['reason']} |")
    data_lines = ["# 数据结构字段目录", "", "由 contract_types.py 生成。全部字段显式传入；业务空值、单位、状态和版本规则见 SPEC.md。DraftDocument.body_json 复用注册的业务 schema，其他核心请求不接受无约束扩展字典。", ""]
    tree = ast.parse((HERE / "contract_types.py").read_text(encoding="utf-8"))
    for cls in (item for item in tree.body if isinstance(item, ast.ClassDef)):
        data_lines += [f"## {cls.name}", ""]
        doc = ast.get_docstring(cls)
        if doc:
            data_lines += [doc, ""]
        data_lines += ["| 字段 | 类型 |", "|---|---|"]
        for field in (item for item in cls.body if isinstance(item, ast.AnnAssign)):
            annotation = ast.unparse(field.annotation).replace("|", "\\|")
            data_lines.append(f"| {field.target.id} | `{annotation}` |")
        data_lines.append("")
    return {"FUNCTIONS.md": "\n".join(function_lines) + "\n", "DATATYPES.md": "\n".join(data_lines) + "\n"}


def check_value(value: object, annotation: object, path: str = "$") -> None:
    """设计用严格结构检查；不宣称替代未来服务鉴权、版本回源或 JSON Schema。"""
    origin, args = typing.get_origin(annotation), typing.get_args(annotation)
    if origin in (typing.Union, types.UnionType):
        for branch in args:
            try:
                check_value(value, branch, path)
                return
            except ValueError:
                pass
        raise ValueError(path + ": no union branch matches")
    if origin is typing.Literal:
        if not any(value == option and type(value) is type(option) for option in args):
            raise ValueError(path + ": invalid enum")
        return
    if annotation is type(None):
        if value is not None:
            raise ValueError(path + ": expected null")
        return
    if hasattr(annotation, "__supertype__"):
        check_value(value, annotation.__supertype__, path)
        if annotation is t.Sha256 and not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(path + ": invalid SHA-256")
        if annotation is t.UtcTime:
            if not value.endswith("Z"):
                raise ValueError(path + ": UTC Z required")
            try:
                dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError(path + ": invalid UTC date") from error
        return
    if origin is tuple:
        if not isinstance(value, list):
            raise ValueError(path + ": expected JSON array")
        if len(args) == 2 and args[1] is Ellipsis:
            for index, item in enumerate(value):
                check_value(item, args[0], f"{path}[{index}]")
        else:
            if len(value) != len(args):
                raise ValueError(path + ": tuple arity")
            for index, (item, kind) in enumerate(zip(value, args)):
                check_value(item, kind, f"{path}[{index}]")
        return
    if inspect.isclass(annotation) and dataclasses.is_dataclass(annotation):
        if not isinstance(value, dict):
            raise ValueError(path + ": expected object")
        fields = typing.get_type_hints(annotation)
        if set(value) != set(fields):
            raise ValueError(path + ": missing or unknown fields")
        for name, kind in fields.items():
            check_value(value[name], kind, path + "." + name)
        if annotation is t.FixedRef and value["target_kind"] == "record" and (value["revision"] is None or value["revision"] < 1):
            raise ValueError(path + ": record revision must be fixed and positive")
        if annotation is t.BudgetLimits and any(v < 0 for k, v in value.items() if k.startswith("max_")):
            raise ValueError(path + ": budget cannot be negative")
        if annotation is t.QuerySpec:
            if not value["text"].strip() and not value["seeds"]:
                raise ValueError(path + ": text or seed required")
            if value["result_limit"] < 1:
                raise ValueError(path + ": result limit must be positive")
            if value["purpose"] == "formal" and (value["applicability"] is None or not value["applicability"]["description"].strip()):
                raise ValueError(path + ": formal purpose needs applicability")
        if annotation is t.ConfidenceAssessment and value["calibrated_probability"] is not None:
            if not 0 <= value["calibrated_probability"] <= 1 or value["calibration_ref"] is None:
                raise ValueError(path + ": calibrated probability needs range and evidence")
        if annotation is t.KnowledgeFacets and ("principle" in value["roles"]) != (value["principle_kind"] is not None):
            raise ValueError(path + ": principle role and kind must agree")
        return
    if annotation is float:
        if type(value) not in (int, float) or not float("-inf") < value < float("inf"):
            raise ValueError(path + ": finite number required")
        return
    if annotation in (int, str, bool):
        if type(value) is not annotation:
            raise ValueError(path + ": scalar type mismatch")
        return
    raise ValueError(path + ": unsupported example annotation " + str(annotation))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="刷新本设计目录的两个派生 Markdown 文件")
    parser.add_argument("--out", type=Path, help="另存检查结果；不是产品测试回执")
    args = parser.parse_args()
    catalog = json.loads((HERE / "function-catalog.json").read_text(encoding="utf-8"))
    methods = signatures()
    errors = []
    names = [row["method"] for row in catalog["functions"]]
    if len(names) != len(set(names)) or set(names) != set(methods):
        errors.append("Function catalog and Protocol methods differ")
    if {row["group"] for row in catalog["functions"]} != {"X01", *(f"G{i:02d}" for i in range(1, 13))}:
        errors.append("Missing function group")
    # Resolve every annotation so forward references and missing type names fail now.
    classes = [c for c in vars(t).values() if inspect.isclass(c) and dataclasses.is_dataclass(c)]
    for cls in classes:
        typing.get_type_hints(cls)
    for name in methods:
        cls, method = name.split(".")
        typing.get_type_hints(getattr(getattr(ports, cls), method))
    generated = render(catalog, methods)
    for name, body in generated.items():
        if args.write:
            (HERE / name).write_text(body, encoding="utf-8")
        elif not (HERE / name).is_file() or (HERE / name).read_text(encoding="utf-8") != body:
            errors.append(name + " is stale")
    examples = json.loads((HERE / "request-examples.json").read_text(encoding="utf-8"))
    cases = []
    for case in examples["cases"]:
        error = None
        try:
            check_value(case["value"], getattr(t, case["type"]))
        except ValueError as problem:
            error = str(problem)
        matches = (error is None) == case["expected_valid"]
        cases.append({"id": case["id"], "passed": matches, "observed_error": error})
        if not matches:
            errors.append("Unexpected request result: " + case["id"])
    result = {"status": "passed" if not errors else "failed", "scope": "static design and synthetic request structures only",
              "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(), "domain_methods": sum(row["group"] != "X01" for row in catalog["functions"]),
              "control_methods": 3, "data_structures": len(classes), "alternative_decisions": len(catalog["alternatives"]),
              "cases": cases, "errors": errors,
              "inputs": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ("contract_types.py", "contract_ports.py", "function-catalog.json", "request-examples.json")},
              "not_tested": ["Backend conformance", "Retrieval quality", "Runtime performance", "Access enforcement by future adapters"]}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
