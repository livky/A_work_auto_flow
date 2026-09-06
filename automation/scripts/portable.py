"""Windows 离线迁移：预览/创建 ZIP，以及解压后的真实运行检查。

退出码：0 成功，1 检查或打包失败。默认仅预览，--apply 才写 ZIP；
不覆盖已有包，不修改原始材料。解压到新目录即可恢复整个快照。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
# 嵌入版 _pth 不自动加入脚本目录，显式定位同目录模块。
sys.path.insert(0, str(Path(__file__).resolve().parent))
# 缓存含旧绝对路径，迁移后重建；查询、反馈、Run 等历史证据必须保留。
OMIT = {".git", "__pycache__", "scratch", "tmp", "dist", ".venv", "venv"}
OMIT_PATHS = {"retrieval/generated", "services/qdrant/storage"}


def inventory(root):
    """仅遍历实际目录；拒绝链接/联接，避免悄悄打包工作区外的材料。"""
    for folder, dirs, files in os.walk(root, followlinks=False):
        base = Path(folder)
        for name in list(dirs):
            path = base / name
            relative = path.relative_to(root).as_posix()
            if name in OMIT or relative in OMIT_PATHS:
                dirs.remove(name)
            elif path.is_symlink() or path.is_junction():
                raise ValueError(f"请先处理目录链接：{relative}")
        for name in sorted(files):
            path = base / name
            if path.is_symlink():
                raise ValueError(f"请先处理文件链接：{path}")
            if path.suffix not in {".pyc", ".pyo"}:
                yield path


def check(root):
    """使用当前包的真实模型、OCR 和临时数据库，不改动业务向量库。"""
    expected = root / "services/qdrant/runtime/python.exe"
    if Path(sys.executable).resolve() != expected.resolve():
        raise ValueError("请使用工作区内 runtime/python.exe，不能用系统 Python 冒充迁移成功")
    import socket
    from unittest.mock import patch
    from qdrant_backend import LocalBackend
    from rapidocr_onnxruntime import RapidOCR
    import numpy as np
    cfg = json.loads((root / "retrieval/config.json").read_text(encoding="utf-8"))
    for key in ("path", "manifest"):
        path = Path(cfg["embedding"][key])
        if path.is_absolute() or not (root / path).resolve().is_relative_to(root):
            raise ValueError(f"模型配置不可迁移：{path}")
    # 禁止 Python socket 外连；推理明确使用本地模型和 CPU。
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("自检禁止联网")):
        with tempfile.TemporaryDirectory(prefix="portable-check-", dir=root) as temporary:
            cfg["vector_store"]["path"] = str(Path(temporary) / "qdrant")
            backend = LocalBackend(root, cfg)
            try:
                vector = next(backend.model.query_embed("Windows 离线迁移验证"))
                if len(vector) != 384 or not np.isfinite(vector).all():
                    raise ValueError("嵌入输出异常")
                backend.search("迁移验证", 1)
            finally:
                backend.close()
            RapidOCR()(np.full((64, 160, 3), 255, dtype=np.uint8))
    subprocess.run([sys.executable, str(root / "automation/scripts/workspace_cli.py"), "validate"], cwd=root, check=True)
    sources = json.loads((root / "retrieval/sources.json").read_text(encoding="utf-8"))
    print(json.dumps({"status": "passed", "root": str(root), "python": sys.executable,
                      "embedding_dimensions": 384, "ocr": "loaded and executed",
                      "external_sources_to_review": sources}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "pack"])
    parser.add_argument("--output", type=Path, help="ZIP 输出路径；默认 dist/workspace-windows.zip")
    parser.add_argument("--apply", action="store_true", help="实际创建包；默认只预览")
    args = parser.parse_args()
    if args.command == "check":
        check(ROOT)
        return
    output = (args.output or ROOT / "dist/workspace-windows.zip").resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / "dist"):
        raise ValueError("工作区内的压缩包只能写入 dist，防止递归打包自身")
    files = list(inventory(ROOT))
    print(json.dumps({"files": len(files), "bytes": sum(p.stat().st_size for p in files),
                      "output": str(output), "apply": args.apply,
                      "excluded": sorted(OMIT | OMIT_PATHS)}, ensure_ascii=False, indent=2), flush=True)
    if not args.apply:
        return
    check(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    # x 模式禁止覆盖；中断留下的包需换名称，原文件始终不变。
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
        for path in files:
            archive.write(path, "workspace/" + path.relative_to(ROOT).as_posix())
    with output.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    print(json.dumps({"archive": str(output), "sha256": digest, "bytes": output.stat().st_size}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"迁移操作失败：{error}", file=sys.stderr)
        sys.exit(1)
