"""可卸载的用户级 rdwork 命令。只添加一个固定 PATH 项，不改系统环境。

工作区地址保存在 launcher.json，更新位置只替换该文件。保留其他 PATH 项的
文本、顺序和类型；卸载只移除本安装实际添加的项，不删除工作区数据。
"""
import json
import os
from pathlib import Path
import subprocess

MARKER = 'ai-rd-workspace-command-v1'


def change_path(value, folder, remove=False):
    """按 Windows 大小写/尾分隔符比较；不重排或去重其他软件的路径。"""
    def key(part):
        return os.path.normcase(part.strip().strip('"').rstrip('\\/')).casefold()
    pieces = value.split(';') if value else []
    exists = any(key(p) == key(str(folder)) for p in pieces)
    if remove:
        return ';'.join(p for p in pieces if key(p) != key(str(folder))), exists
    return (value if exists else value + (';' if value and not value.endswith(';') else '') + str(folder)), not exists


def register(root, remove=False, preview=False):
    import winreg
    root = Path(root).resolve()
    requested = Path(os.environ['LOCALAPPDATA']) / 'AI-RD-Workspace/bin'
    # Packaged Windows desktop apps may virtualize LocalAppData without exposing a
    # symlink. Register the effective physical directory so ordinary terminals can
    # find the command too; explicit directory/file links still fail closed.
    for candidate in (requested.parent, requested):
        # is_junction was added in Python 3.12; older bootstrap interpreters can
        # still detect Windows reparse-point directories through lstat attributes.
        junction = (candidate.is_junction() if hasattr(candidate, 'is_junction') else
                    bool(candidate.exists() and getattr(candidate.lstat(), 'st_file_attributes', 0) & 0x400))
        if candidate.is_symlink() or junction:
            raise ValueError('命令安装目录存在链接')
    if not requested.exists() and not remove and not preview:
        requested.mkdir(parents=True)
    folder = requested.resolve()
    receipt = folder / 'launcher.json'
    if any((folder / name).is_symlink() for name in ('launcher.json', 'rdwork.cmd', 'launch.ps1')):
        raise ValueError('命令安装文件存在链接')
    old = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
    if folder.exists() and ((old and old.get('owner') != MARKER) or (not old and any(folder.iterdir()))):
        raise ValueError('同名目录不属于本安装，拒绝覆盖')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        try:
            value, kind = winreg.QueryValueEx(key, 'Path')
        except FileNotFoundError:
            value, kind = '', winreg.REG_EXPAND_SZ
        path_added = bool(old and old.get('path_added'))
        prior_entry = old.get('path_entry', str(requested)) if old else str(folder)
        adjusted = value
        if old and path_added and prior_entry != str(folder):
            adjusted, _ = change_path(value, prior_entry, remove=True)
        next_path, changed = change_path(adjusted, folder, remove=remove) if not remove or path_added else (value, False)
        result = {'command': 'rdwork', 'root': str(root), 'directory': str(folder),
                  'remove': remove, 'preview': preview, 'path_changed': next_path != value,
                  'note': '新终端使用 rdwork；现有终端可直接运行工作区 workbench.cmd'}
        if preview or (remove and not old):
            return result
        if remove:
            # Check owned launchers before deletion; local customizations require manual handling.
            for name in ('rdwork.cmd', 'launch.ps1'):
                p = folder / name
                if p.exists() and MARKER not in p.read_text(encoding='utf-8'):
                    raise ValueError(f'命令文件已被替换：{p}')
            if next_path != value:
                winreg.SetValueEx(key, 'Path', 0, kind, next_path)
            for name in ('rdwork.cmd', 'launch.ps1', 'launcher.json'):
                (folder / name).unlink(missing_ok=True)
            if not any(folder.iterdir()):
                folder.rmdir()
        else:
            if not (root / 'workbench.cmd').is_file():
                raise ValueError('工作区缺少 workbench.cmd')
            # Do not shadow a command belonging to a different application.
            import shutil
            collision = shutil.which('rdwork')
            if collision and Path(collision).resolve() != (folder / 'rdwork.cmd').resolve():
                raise ValueError(f'已有其他 rdwork 命令：{collision}')
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'rdwork.cmd').write_text('@echo off\nrem ' + MARKER + '\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" %*\nexit /b %errorlevel%\n', encoding='ascii')
            # Workspace paths are data loaded from JSON, never interpolated into PowerShell code.
            (folder / 'launch.ps1').write_text('# ' + MARKER + '\n$entry = Get-Content -LiteralPath (Join-Path $PSScriptRoot "launcher.json") -Raw -Encoding UTF8 | ConvertFrom-Json\n& (Join-Path $entry.root "workbench.cmd") @args\nexit $LASTEXITCODE\n', encoding='ascii')
            receipt.write_text(json.dumps({'owner': MARKER, 'root': str(root), 'path_entry': str(folder), 'path_added': path_added or changed}, ensure_ascii=False), encoding='utf-8')
            if next_path != value:
                winreg.SetValueEx(key, 'Path', 0, kind, next_path)
    # Broadcast is bounded, best-effort; cannot mutate the parent shell environment.
    import ctypes
    outcome = ctypes.c_size_t()
    send = ctypes.windll.user32.SendMessageTimeoutW
    send.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_wchar_p,
                     ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_size_t)]
    send.restype = ctypes.c_void_p
    send(0xFFFF, 0x1A, 0, 'Environment', 2, 2000, ctypes.byref(outcome))
    return result
