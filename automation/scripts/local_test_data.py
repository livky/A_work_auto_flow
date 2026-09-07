"""生成可重复使用的合成工作区。实例仅在 .local/test-workspace，不进入正式图谱。

生成器和断言可发布，生成的数据、监测日志和检索结果不可发布。已有沙盒绝不
静默重置，以便用户检查变更和失效链；需要全新样本时保留旧目录后重新生成。
"""
import hashlib
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[2]


def build(target, source=ROOT):
    target = Path(target)
    if target.exists():
        raise FileExistsError('样本目标已存在，拒绝覆盖')
    target.mkdir(parents=True)
    def put(name, value):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, dict) else value, encoding='utf-8')
        return path
    for name in ('config.json', 'context-policy.json'):
        value = json.loads((source / 'retrieval' / name).read_text(encoding='utf-8'))
        if name == 'config.json':
            value['vector_store'] = {'provider': None}
            value['ocr_enabled'] = False
        put('retrieval/' + name, value)
    put('retrieval/sources.json', {'sources': []})
    put('retrieval/eval.json', {'cases': []})
    put('workspace.json', {'schema_version': 1, 'workspace_id': 'synthetic-only', 'required_paths': [], 'context_policy': {'excluded_directories': ['.local']}})
    put('tools/registry.json', {'tools': []})
    put('AGENTS.md', '# 合成测试工作区\n所有记录为软件测试样例，不能作为公司算法或真实业务结论。')
    put('README.md', '# 本机合成数据\n覆盖算法、数据、Run、研究、知识、报告、项目、工具和检索；不得用作业务验收。')
    measurement = put('data/catalog/synthetic-measurement.csv', 'sample,temperature_C,offset_ms\n1,20,1.2\n2,30,1.4\n3,40,1.6\n')
    put('data/contracts/measurement.json', {'synthetic': True, 'columns': {'temperature_C': 'degC', 'offset_ms': 'ms'}, 'allow_missing': False})
    put('data/catalog/synthetic.dataset.json', {'schema_version': 1, 'dataset_id': 'DATA-SYNTHETIC',
        'title': '合成温度与偏移', 'synthetic': True, 'path': 'data/catalog/synthetic-measurement.csv',
        'contract': 'data/contracts/measurement.json', 'access_class': 'synthetic-only'})
    put('data/catalog/README.md', '# 合成测量\n三行数据用于检查温漂引用和输入版本，不代表仪器性能。')
    algorithm_doc = put('core-algorithms/synthetic-drift/README.md', '# 合成温漂说明（虚构文档）\n测试模型为线性映射：\n\n$$b(T)=0.02T+0.8$$\n\n其中温度 T 的单位为 degC，偏移 b 的单位为 ms。\n[实现](code/drift.py)')
    put('core-algorithms/synthetic-drift/code/drift.py', '"""仅用于合成测试；温度单位 degC，输出 ms。"""\ndef offset(temperature_c):\n    return 0.02 * temperature_c + 0.8\n')
    put('core-algorithms/synthetic-drift/module.json', {'module_id': 'MOD-SYNTHETIC', 'entity_kind': 'core-algorithm', 'title': '合成温漂（虚构）', 'source_document': '仅测试：虚构算法说明', 'claims': [], 'dependencies': []})
    result = put('runs/synthetic-base/result.txt', '合成计算：30 degC 时偏移 1.4 ms。\n')
    def ref(path):
        return {'path': path.relative_to(target).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    review = {'status': 'not-reviewed'}
    claim = {'claim_id': 'CLM-SYNTHETIC', 'statement': '合成计算偏移为 1.4 ms', 'scope': 'synthetic:only',
             'kind': 'calculation', 'record_reason': '用于验证来源哈希变化后下游报告显示风险',
             'evidence_refs': [{'target': measurement.relative_to(target).as_posix(), 'sha256': ref(measurement)['sha256'], 'locator': 'row 2', 'relation': 'input'}],
             'review': review, 'review_history': []}
    put('runs/synthetic-base/run.json', {'run_id': 'RUN-SYNTHETIC', 'title': '合成温漂测试', 'question': '测试引用与失效传播',
        'status': 'running', 'record_reason': '跨模块软件测试样例', 'module_ids': ['MOD-SYNTHETIC'],
        'inputs': [ref(measurement), ref(algorithm_doc)], 'artifacts': [ref(result)], 'claims': [claim],
        'review': review, 'dependencies': [], 'parent_run_ids': [], 'quality_results': [], 'code': {}, 'environment': {}})
    put('runs/synthetic-base/README.md', '# 合成 Run\n用于演示 running → succeeded 状态变化。执行成功仍不代表结论复核。')
    # Pins record fingerprints once; changes to upstream remain visible, never auto-confirmed.
    import evidence
    graph = evidence.EvidenceGraph(target)
    dep = {'target': 'CLM-SYNTHETIC', 'sha256': graph.nodes['CLM-SYNTHETIC']['fingerprint'], 'relation': 'supports', 'locator': 'statement'}
    put('research/synthetic-topic/research.json', {'research_id': 'RES-SYNTHETIC', 'title': '合成温漂研究', 'claims': [], 'dependencies': [dep], 'review': review})
    put('research/synthetic-topic/SYNTHESIS.md', '# 合成研究\n[Run](../../runs/synthetic-base/run.json)\n温漂结论尚未复核。')
    for name, eid in [('knowledge/patterns/synthetic.md', 'EVD-SYNTHETIC-KNOWLEDGE'), ('reports/sources/synthetic.md', 'EVD-SYNTHETIC-REPORT')]:
        put(name, '# 合成证据链\n仅用于测试；引用的计算结果不可用于真实工程决策。')
        put(name + '.evidence.json', {'evidence_id': eid, 'document_path': name, 'claims': [], 'dependencies': [dep], 'review': review})
    put('projects/synthetic/project.json', {'project_id': 'PRJ-SYNTHETIC', 'title': '合成交付聚合', 'module_ids': ['MOD-SYNTHETIC']})
    put('tools/synthetic/README.md', '# 合成工具\n示例：检查 CSV 的温度单位与非空字段。')
    put('tools/synthetic/tool.json', {'tool_id': 'TOOL-SYNTHETIC', 'title': '合成检查工具'})
    put('inbox/README.md', '# 合成待整理材料\n不自动纳入检索。')
    put('archive/README.md', '# 合成归档\n不自动纳入检索。')
    put('governance/README.md', '# 合成数据边界\n无外部授权和企业连接器。')
    put('context/NOW.md', '# 合成环境\n只有软件测试样例，没有业务验收结论。')
    put('context/START_HERE.md', '# 合成入口\n从 README 开始；不把本沙盒并入正式工作区。')
    put('synthetic-marker.json', {'schema': 1, 'synthetic': True, 'modules': ['core-algorithms', 'data', 'runs', 'research', 'knowledge', 'reports', 'projects', 'tools', 'retrieval', 'context', 'governance', 'inbox', 'archive']})
    return target


def generate(root, preview=False):
    from deployment import safe
    target = safe(Path(root), '.local/test-workspace')
    if target.exists():
        marker = target / 'synthetic-marker.json'
        if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')).get('synthetic') is not True:
            raise ValueError('已有目录不是本生成器的合成沙盒，拒绝使用')
    elif not preview:
        # Build a sibling staging directory, so interruption never publishes a partial fixture.
        stage = target.with_name('test-workspace-' + uuid.uuid4().hex)
        build(stage)
        stage.rename(target)
    return {'root': str(target), 'synthetic': True, 'preview': preview, 'note': '生成实例不发布；重复运行保留已有编辑，不提高复核状态'}
