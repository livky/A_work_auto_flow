"""按组件报告当前环境能力，严格验收不把跳过的集成测试当通过。

默认检查不联网、不安装、不修改业务索引。要求向量/OCR 能力时，在独立
子进程和临时目录运行实际离线探针；失败与未运行分别报告。
"""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import tempfile

# Windows 嵌入式 Python 的 _pth 不包含脚本目录。独立健康子进程也必须
# 显式定位同目录实现，不能依赖父进程已经导入过 workspace_cli。
sys.path.insert(0, str(Path(__file__).resolve().parent))

CAPABILITIES = ("structure", "fts", "vector", "ocr", "portable", "business-eval")


def available(module):
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def worker(root, action, timeout=60):
    """超时或崩溃均返回结构化不可用，子进程不会占有真实业务库。"""
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), action, str(root)],
                                capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        if result.returncode:
            return {"status": "unavailable", "detail": (result.stderr or result.stdout)[-2000:]}
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "detail": str(exc)}


def doctor(root, required=(), smoke=False):
    import workspace_cli as cli
    root = Path(root).resolve()
    unknown = set(required) - set(CAPABILITIES)
    if unknown:
        raise ValueError(f"未知能力：{sorted(unknown)}")
    errors, warnings = cli.validate_workspace(root)
    caps = {"structure": {"status": "ready" if not errors else "unavailable", "errors": errors, "warnings": warnings}}
    try:
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE VIRTUAL TABLE probe USING fts5(body)")
            db.execute("INSERT INTO probe VALUES ('workspace probe')")
            if db.execute("SELECT count(*) FROM probe WHERE probe MATCH 'probe'").fetchone()[0] != 1:
                raise ValueError("FTS5 读写探针失败")
        caps["fts"] = {"status": "ready", "detail": "内存 FTS5 建表、写入与查询通过"}
    except (sqlite3.Error, ValueError) as exc:
        caps["fts"] = {"status": "unavailable", "detail": str(exc)}
    cfg_path = root / "retrieval/config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
        model = (root / cfg["embedding"]["path"] / "model_optimized.onnx").resolve()
        missing = [name for name in ("qdrant_client", "fastembed", "tokenizers") if not available(name)]
        if not model.is_relative_to(root) or not model.is_file():
            missing.append("configured local model")
        caps["vector"] = {"status": "unavailable" if missing else "unverified", "missing": missing}
    except (OSError, KeyError, ValueError, TypeError) as exc:
        caps["vector"] = {"status": "unavailable", "detail": str(exc)}
    missing_ocr = [name for name in ("rapidocr_onnxruntime", "numpy") if not available(name)]
    caps["ocr"] = {"status": "unavailable" if missing_ocr else "unverified", "missing": missing_ocr}
    for capability in ("vector", "ocr"):
        if caps[capability]["status"] == "unverified" and (smoke or capability in required):
            caps[capability] = worker(root, capability)
    portable = root / "services/qdrant/runtime/python.exe"
    caps["portable"] = {"status": "unavailable" if not portable.is_file() else "unverified",
                        "detail": "完整迁移验收使用 portable.cmd check；系统 Python 不替代便携验证"}
    cases = root / "retrieval/eval.json"
    try:
        count = len(json.loads(cases.read_text(encoding="utf-8-sig"))["cases"])
        caps["business-eval"] = {"status": "unverified" if count else "unavailable", "cases": count,
                                 "detail": "存在问题不等于答案通过；需领域验收结果"}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        caps["business-eval"] = {"status": "unavailable", "detail": str(exc)}
    unmet = [name for name in required if caps[name]["status"] != "ready"]
    return {"python": sys.executable, "python_version": platform.python_version(), "capabilities": caps,
            "required": list(required), "unmet": unmet, "eligible": not unmet,
            "note": "ready 仅指该组件指定探针通过；不证明业务答案正确"}


def verify(root, profile="core"):
    if profile not in {"core", "full"}:
        raise ValueError("profile 必须是 core/full")
    required = ["structure", "fts"] + (["vector", "ocr"] if profile == "full" else [])
    health = doctor(root, required)
    tests = worker(root, "tests", timeout=180)
    passed = tests.get("status") == "completed" and tests.get("failures") == 0 and tests.get("errors") == 0 and tests.get("total", 0) > 0
    complete = passed and tests.get("skipped") == 0
    eligible = health["eligible"] and passed and (profile == "core" or complete)
    return {"profile": profile, "eligible": eligible, "health": health, "tests": tests,
            "status": ("passed" if complete else "passed-with-skips") if eligible else "failed",
            "full_integration_verified": eligible and profile == "full" and complete}


def probe(action, root):
    """子进程实现。捕获第三方库输出，确保父进程只接收一个 JSON。"""
    if action == "tests":
        import unittest
        # 只加载当前工作区固定测试目录，不支持任意测试路径或 shell 命令。
        logs = io.StringIO()
        with redirect_stdout(logs):
            suite = unittest.defaultTestLoader.discover(str(root / "automation/tests"))
            result = unittest.TextTestRunner(stream=logs, verbosity=2).run(suite)
        return {"status": "completed", "total": result.testsRun, "failures": len(result.failures),
                "errors": len(result.errors), "skipped": len(result.skipped),
                "skip_reasons": [reason for _, reason in result.skipped], "log": logs.getvalue()}
    import socket
    from unittest.mock import patch
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("健康探针禁止联网")):
        if action == "vector":
            import qdrant_backend
            cfg = json.loads((root / "retrieval/config.json").read_text(encoding="utf-8-sig"))
            scratch = root / "tmp"
            scratch.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="health-", dir=scratch) as name:
                target = Path(name).resolve()
                if not target.is_relative_to(scratch.resolve()) or target == scratch.resolve():
                    raise ValueError("临时目录越界")
                cfg["vector_store"]["path"] = str(target / "qdrant")
                backend = qdrant_backend.LocalBackend(root, cfg)
                try:
                    vector = next(backend.model.query_embed("本地能力验证"))
                    import math
                    if not len(vector) or not all(math.isfinite(float(v)) for v in vector):
                        raise ValueError("向量结果无效")
                    backend.search("能力验证", 1)
                    return {"status": "ready", "dimensions": len(vector), "detail": "离线模型校验、编码与临时库查询通过"}
                finally:
                    backend.close()
        if action == "ocr":
            import numpy as np
            from rapidocr_onnxruntime import RapidOCR
            RapidOCR()(np.full((64, 160, 3), 255, dtype=np.uint8))
            return {"status": "ready", "detail": "OCR 引擎加载与空白图执行通过；不代表字符准确率"}
    raise ValueError("未知探针")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["vector", "ocr", "tests"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        with redirect_stdout(io.StringIO()):
            value = probe(args.action, args.root.resolve())
        print(json.dumps(value, ensure_ascii=False))
    except Exception as exc:
        print(f"健康探针失败：{exc}", file=sys.stderr)
        raise SystemExit(2)
