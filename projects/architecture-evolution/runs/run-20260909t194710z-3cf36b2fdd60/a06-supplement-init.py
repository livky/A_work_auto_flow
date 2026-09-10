"""Freeze the A06 supplemental task before its first public product call.

This evidence helper records inputs only. It does not generate assessment text,
interpret query candidates, or execute a product mutation. Re-running refuses to
overwrite the pointer so that the existing attempt remains attributable.
"""
import json
import sys
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
FIXTURE = ROOT / '.local/testing/material-query-f3-20260910-actual/workspace'
sys.path.insert(0, str(ROOT / 'automation/testing'))
import ai_review

ACTOR = 'Codex /root/memory_review actual AI'
pointer = RUN / 'a06-supplement-attempt.json'
if pointer.exists():
    raise SystemExit('A06 supplemental pointer exists; reuse its attempt explicitly.')

task_path = RUN / 'a06-supplement-task.txt'
task = '''补充 A06 的新问题发现候选过程：从第二研究 API 重试的问题出发，以自然语言问题和技术关键词通过公共 lexical 查询发现候选，初始请求不含 MEM ID 或 include_refs。先阅读真实候选，再固定引用展开水箱与重试正文，判断有条件可参考方法与不可推广结论。通过公共入口保存带条件的参考说明并回读。此尝试补充既有 A08/A09，不重演原场景，不把连续已知上下文伪装成盲测。只访问 SYNTHETIC F3 隔离工作区；不修改产品代码、真实 Project、原件或既有结论。'''
with task_path.open('x', encoding='utf-8') as stream:
    stream.write(task + '\n')

# Hash only explicitly named inputs; no broad workspace or business-data scan.
fingerprinted = [
    ROOT / 'automation/scripts/workspace_cli.py',
    ROOT / 'automation/scripts/material_query/coordinator.py',
    ROOT / 'automation/scripts/material_query/assembly.py',
    ROOT / 'automation/workflows/material-query/SKILL.md',
    ROOT / 'automation/workflows/development-checks/SKILL.md',
    ROOT / 'automation/testing/ai_review.py',
]
metadata = {
    'fixture_root': str(FIXTURE),
    'input': 'Existing independent SYNTHETIC F3 after A09; no physical experiment',
    'context': 'continuous; reviewer already read A08/A09; discovery query has no fixed record IDs but is not blind',
    'supplements': ['A08/attempt-827ddd756ca34e78825e4e48c7d98aa4', 'A09/attempt-6a3c96e965c1408e998f7cfc8de720e7'],
    'source_fingerprints': {str(p.relative_to(ROOT)): ai_review.digest(p) for p in fingerprinted},
    'initial_heads': {owner: ai_review.read_json(FIXTURE / 'research' / owner / 'memory/HEAD.json') for owner in ['tank', 'retry', 'saturation']},
    'original_source_sha256': {owner: ai_review.digest(FIXTURE / 'research' / owner / 'data/合成 输入.md') for owner in ['tank', 'retry', 'saturation']},
}
metadata_path = RUN / 'a06-supplement-metadata.json'
ai_review.write_new(metadata_path, metadata)
attempt = ai_review.initialize(RUN / 'actual-ai', 'A06', task_path, ACTOR,
                               context_mode='continuous', metadata_file=metadata_path)

# The new problem and keywords refer to engineering concepts, never fixture
# record identities or fixture labels. Scope is the authorized three owners.
scope = {'owner_ids': ['RES-F3-TANK', 'RES-F3-RETRY', 'RES-F3-SATURATION'],
         'kinds': ['detail'], 'include_unknown': False}
query = {
    'definition': {'key': 'full', 'version': '1'},
    'question': '重试等待达到上限后，能否借用其他反馈模型的分段分析来检查边界，并据此保证稳定和最终成功？',
    'keywords': ['重试', '饱和', '误差', '边界'],
    'scope': scope, 'scope_ceiling': scope,
    'purpose': 'exploration', 'association': {'mode': 'off'},
    'budget': {'wall_ms': 10000, 'read_bytes': 2097152, 'output_chars': 14000,
               'candidates': 100, 'graph_nodes': 50, 'graph_edges': 100,
               'graph_hops': 2, 'model_tokens': 0},
    'freshness': 'current', 'result_limit': 8, 'missing_policy': 'reject',
    'fallback_definitions': [], 'applicability': 'SYNTHETIC F3 cross-research reference only',
    'channels': ['lexical'],
}
query_path = attempt / 'authored-requests/discovery.json'
ai_review.write_new(query_path, query)
ai_review.write_new(pointer, {'attempt': str(attempt), 'query': str(query_path)})
print(json.dumps({'attempt': str(attempt), 'query': str(query_path)}, ensure_ascii=False))
