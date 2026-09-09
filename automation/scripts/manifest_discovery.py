"""统一发现受控业务卡，不读取 Run 产物或记忆提交正文。

目录层级不决定对象身份；只认指定的登记文件名。扫描拒绝链接，剪枝缓存，
因而研究内、文件型对象运行容器和旧项目 analysis/runs 使用相同规则。
"""
import os
from pathlib import Path
import stat

BUSINESS_ROOTS = ('research', 'runs', 'projects', 'core-algorithms', 'knowledge', 'reports', 'data', 'tools')
EXCLUDED = {'.run-captures', '.git', '.local', 'node_modules', '__pycache__', '_template', 'templates',
            'generated', '.venv', 'venv', '.pytest_cache', '.cache', 'memory'}


def manifests(root, names):
    """返回确定顺序的卡片路径；坏卡内容由调用方报告，不被吞掉。

    Windows junction 与符号链接均拒绝跟随。memory 容器只存事务，文件型
    对象运行使用旁边的 .runtime 容器，因此这里可安全剪枝整个记忆目录。
    """
    root = Path(root).resolve()
    found = []
    for area in BUSINESS_ROOTS:
        start = root / area
        if not start.exists():
            continue
        metadata = start.lstat()
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
            raise ValueError(f'业务目录不能是链接：{start}')
        for folder, dirs, files in os.walk(start, followlinks=False):
            for name in list(dirs):
                path = Path(folder) / name
                metadata = path.lstat()
                if (name.casefold() in EXCLUDED or name.endswith('.memory') or
                        stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400):
                    dirs.remove(name)
            for name in files:
                if name not in names:
                    continue
                path = Path(folder) / name
                metadata = path.lstat()
                if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
                    raise ValueError(f'业务卡不能是链接：{path}')
                found.append(path)
    return sorted(found)


def run_home(root, owner_id):
    """以稳定对象 ID 解析归属；关联对象不意味着复制 Run。

    目录型对象直接使用自己的 runs；平铺文档/数据卡/工具注册项使用
    memory_home 的旁置 .runtime/runs，避免同一父目录的多个对象混用。
    临时 FILE 身份不可作为归属，须先采用为稳定对象。
    """
    from memory import owners
    from memory.errors import MemoryError
    try:
        owner = owners.resolve_owner(root, owner_id)
    except MemoryError as exc:
        raise ValueError(f'Run 归属解析失败（{exc.code}）：{owner_id}；{exc}') from exc
    if owner.get('temporary'):
        raise ValueError('Run 归属需要稳定对象 ID；请先采用该文档')
    native = owners.safe_path(root, owner['native_ref']['path'])
    if owner['owner_type'] in {'research', 'project', 'core-algorithm', 'run'}:
        home = native.parent / 'runs'
    elif owner['owner_type'] == 'tool':
        # 工具的 memory_home 位于集中 tools/memory，运行必须置于旁边，
        # 不能进入会被所有发现器剪枝的事务根。
        home = Path(root) / 'tools/runtime' / owner['owner_id'] / 'runs'
    else:
        home = Path(root) / (owner['memory_home'] + '.runtime') / 'runs'
    return owners.safe_path(root, home.relative_to(Path(root)).as_posix()), owner['owner_id']
