"""模拟长期使用后扩展的旧工作区，仅由测试显式调用，不含真实业务材料。"""
import hashlib
import json
from pathlib import Path


def snapshot(root, names, directories):
    """记录受保护文件的字节指纹及目录集合；包含空目录，避免只测文件遗漏。"""
    return {'files': {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names},
            'directories': sorted(directories)}


def populate(root, branches=8):
    """在各业务区添加多层目录、中文空格名称、单文件和目录工具以及用户扩展。

    目录规模固定且可重复；比较完整受保护集合，不以几个抽样文件替代数据保留验收。
    不在真实工作区调用：测试使用 TemporaryDirectory 或 .local 隔离目录。
    """
    root = Path(root).resolve()
    names, directories = [], set()
    def write(name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        names.append(name)
        directories.add(path.parent.relative_to(root).as_posix())
    for area in ['core-algorithms', 'research', 'runs', 'projects', 'knowledge', 'reports/sources', 'data/catalog']:
        for i in range(branches):
            parent = f'{area}/用户扩展 {i}/阶段 A/版本 01'
            write(parent + '/材料.txt', f'SYNTHETIC ONLY {area} {i}\n')
            empty = parent + '/空目录'
            (root / empty).mkdir()
            directories.add(empty)
    entries = ['tools/packages/用户库/子包', 'tools/scripts/用户脚本/任务组', 'tools/scripts/用户脚本/单文件.py']
    write(entries[0] + '/__init__.py', '# Synthetic package; never executed during migration.\n')
    write(entries[1] + '/worker.py', '# Synthetic script collection.\n')
    write(entries[2], '# Synthetic CLI.\n')
    write('automation/user-extension/nested/custom.py', '# User-owned extension, absent from new source.\n')
    write('.agents/skills/user-example/SKILL.md', '---\nname: user-example\ndescription: Synthetic fixture only.\n---\nSynthetic fixture.\n')
    # 依赖缓存含无效 JSON，必须按既有规则剪枝；业务目录中的无效 JSON 另作反例。
    write('automation/user-extension/node_modules/vendor/broken.json', '{synthetic invalid cache')
    write('.local/user-cache/nested/broken.json', '{synthetic invalid cache')
    registry = root / 'tools/registry.json'
    value = json.loads(registry.read_text(encoding='utf-8'))
    value['tools'].extend({'tool_id': f'TOOL-USER-SYNTHETIC-{i}', 'kind': 'python-package' if i == 0 else 'python-cli',
                           'entrypoint': entry, 'status': 'active'} for i, entry in enumerate(entries))
    registry.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    names.extend(['tools/registry.json', 'retrieval/config.json', 'retrieval/sources.json', 'AGENTS.md'])
    return snapshot(root, names, directories)


def assert_preserved(root, expected):
    """缺失文件、目录或任何字节变化都失败；不自动修复测试目标掩盖问题。"""
    for name, fingerprint in expected['files'].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != fingerprint:
            raise AssertionError('Protected file changed or missing: ' + name)
    for name in expected['directories']:
        if not (root / name).is_dir():
            raise AssertionError('Protected directory missing: ' + name)
