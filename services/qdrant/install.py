"""安装工作区自包含的 Windows x64 Qdrant local + 推理运行时。

只下载公开 Python/依赖；不读取或发送业务材料。wheelhouse 和 SHA256 清单保留
以便离线重装。默认预览；--apply 才下载和写入。不覆盖已存在的 Python 可执行文件。
安装需要已有 Python+pip 引导一次，完成后 runtime/python.exe 不依赖引导解释器。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile
import uuid

BASE = Path(__file__).resolve().parent
PYTHON_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
PACKAGES = ["qdrant-client==1.19.0", "fastembed==0.8.0", "pypdf==6.17.0",
            "pillow==12.3.0", "rapidocr-onnxruntime==1.4.4", "pip==26.2.1"]


def install(apply=False, offline=False, lock_path=None):
    if not apply:
        print(json.dumps({"target": str(BASE), "python": PYTHON_URL, "packages": PACKAGES,
                          "offline": offline, "apply": False}, indent=2))
        return
    downloads = BASE / "downloads"
    wheels = BASE / "wheelhouse"
    # Build in a sibling staging directory. An unsuccessful pip/DLL check must not
    # damage a previously working runtime; directory depth preserves relative _pth paths.
    runtime = BASE / ("runtime-stage-" + uuid.uuid4().hex)
    for folder in (downloads, wheels, runtime):
        folder.mkdir(parents=True, exist_ok=True)
    archive = downloads / "python-3.12.10-embed-amd64.zip"
    # 离线恢复先核对已登记包，损坏时停止；校验清单是完整性记录，不是签名。
    receipt = BASE / "checksums.json"
    if offline and receipt.exists():
        for relative, expected in json.loads(receipt.read_text(encoding="utf-8")).items():
            candidate = (BASE / relative).resolve()
            if not candidate.is_relative_to(BASE.resolve()) or not candidate.is_file():
                raise ValueError(f"安装包缺失或越界：{relative}")
            if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
                raise ValueError(f"安装包校验失败：{relative}")
    if not archive.exists():
        if offline:
            raise RuntimeError("离线安装缺少 Python 安装包")
        temporary = archive.with_suffix(".partial")
        urllib.request.urlretrieve(PYTHON_URL, temporary)
        os.replace(temporary, archive)
    if not (runtime / "python.exe").exists():
        with zipfile.ZipFile(archive) as package:
            for item in package.infolist():
                if not (runtime / item.filename).resolve().is_relative_to(runtime.resolve()):
                    raise ValueError("安装包路径越界")
            package.extractall(runtime)
    # 嵌入版使用显式相对搜索路径，移动整个工作区后仍可用，不依赖系统 PATH。
    (runtime / "python312._pth").write_text(
        "python312.zip\n.\nLib/site-packages\n../../..\nimport site\n", encoding="utf-8")
    if not offline:
        pip_command = [sys.executable, "-m", "pip"]
        if subprocess.run([*pip_command, "--version"], capture_output=True).returncode:
            pip_app = downloads / 'pip.pyz'
            if not pip_app.exists():
                urllib.request.urlretrieve('https://bootstrap.pypa.io/pip/pip.pyz', pip_app)
            pip_command = [sys.executable, str(pip_app)]
        selected = ['-r', str(lock_path), 'pip==26.2.1'] if lock_path else PACKAGES
        # Always fetch wheels for the target CPython 3.12 x64, not the bootstrap version.
        subprocess.run([*pip_command, "download", "--only-binary=:all:", '--python-version', '3.12',
                        '--platform', 'win_amd64', '--implementation', 'cp', '--abi', 'cp312',
                        "--dest", str(wheels), *selected], check=True)
    target = runtime / "Lib/site-packages"
    # pip 自身也是 wheel；直接从缓存引导，不依赖系统 Python 已装 pip。
    pip_wheels = sorted(wheels.glob("pip-*.whl"))
    if not pip_wheels:
        raise RuntimeError("缺少 pip wheel；首次安装需使用带 pip 的 Python 联网下载")
    runner = "import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('pip',run_name='__main__')"
    lock = Path(lock_path) if lock_path else BASE / "requirements.lock.txt"
    # 离线恢复优先实际锁定版本；即使缓存以后多了其他版本也不会静默升级。
    install_items = ["-r", str(lock), "pip==26.2.1"] if (offline or lock_path) and lock.exists() else PACKAGES
    subprocess.run([str(runtime / "python.exe"), "-c", runner, str(pip_wheels[-1]), "install", "--no-index", "--no-compile", "--upgrade",
                    "--find-links", str(wheels), "--target", str(target),
                    "--report", str(BASE / "installation.json"), *install_items], check=True)
    checksums = {p.relative_to(BASE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in [archive, *sorted(wheels.glob("*.whl"))]}
    (BASE / "checksums.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")
    # pip 冻结全部传递依赖，记录实际安装而不把浮动版本当作可复现锁文件。
    frozen = subprocess.check_output([str(runtime / "python.exe"), "-m", "pip", "freeze"], text=True) if (target / "pip").exists() else None
    if frozen:
        (BASE / "requirements.lock.txt").write_text(frozen, encoding="utf-8")
    else:
        report = json.loads((BASE / "installation.json").read_text(encoding="utf-8"))
        locked = sorted(f"{i['metadata']['name']}=={i['metadata']['version']}" for i in report["install"])
        (BASE / "requirements.lock.txt").write_text("\n".join(locked) + "\n", encoding="utf-8")
    subprocess.run([str(runtime / "python.exe"), "-c",
                    "import qdrant_client,fastembed,pypdf,rapidocr_onnxruntime; print('local runtime ready')"], check=True)
    live = BASE / 'runtime'
    backup = BASE.parents[1] / '.local/runtime-backups' / uuid.uuid4().hex
    if live.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        live.rename(backup)
    try:
        runtime.rename(live)
    except OSError:
        if backup.exists():
            backup.rename(live)
        raise
    print(json.dumps({'runtime': str(live), 'previous_runtime': str(backup) if backup.exists() else None}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--lock", type=Path, help="新版框架依赖锁文件；引导解释器不决定目标 wheel 版本")
    args = parser.parse_args()
    install(args.apply, args.offline, args.lock)
