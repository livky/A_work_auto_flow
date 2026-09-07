"""只读核对关系展示的数据基础；仅在本 Run 写统计，不生成或修改业务关系。

现有 SQLite 用只读模式打开，避免触发索引、模型加载或写库；合成工作区
只有已存在时才检查。统计是实现盘点，不能证明业务关联或图展示的有效性。
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'automation/scripts'))
import evidence
import retrieval


def inspect(root):
    graph = evidence.EvidenceGraph(root)
    relations = Counter(ref.get('relation', 'untyped') for node in graph.nodes.values()
                        for ref in graph.refs(node) if isinstance(ref, dict))
    result = {'evidence_nodes': len(graph.nodes),
              'claims': sum(n['kind'] == 'claim' for n in graph.nodes.values()),
              'typed_reference_counts': dict(relations),
              'propagation_edges': sum(map(len, graph.edges.values())),
              'errors': graph.errors}
    database = root / 'retrieval/generated/search.sqlite3'
    if database.exists():
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            docs = retrieval.read_docs(db)
        for doc in docs.values():
            doc['meta']['related'] = [str((root / p).resolve()) for p in doc['meta'].get('related', [])]
        edges = retrieval.relations(docs)
        groups = Counter(mid for doc in docs.values() for mid in doc['meta'].get('module_ids', []))
        result['existing_index'] = {
            'documents': len(docs), 'undirected_neighbor_pairs': sum(map(len, edges.values())) // 2,
            'module_group_sizes': dict(groups),
            'note': '现有缓存快照；未刷新。邻接包含组内两两连接，不等于显式证据依赖。'}
    else:
        result['existing_index'] = None
    return result


if __name__ == '__main__':
    files = ['automation/scripts/evidence.py', 'automation/scripts/evidence_observer.py',
             'automation/scripts/evidence_view.py', 'automation/scripts/retrieval.py',
             'automation/scripts/context_engine.py', 'automation/scripts/workbench.py',
             'automation/scripts/qdrant_backend.py', 'automation/ui/workbench.html',
             'retrieval/config.json', 'retrieval/context-policy.json']
    result = {'observed_at': datetime.now(timezone.utc).isoformat(),
              'scope': '正式工作区含本次新建的研究和 planned Run；不含真实业务验收',
              'workspace': inspect(ROOT),
              'synthetic': inspect(ROOT / '.local/test-workspace') if (ROOT / '.local/test-workspace/synthetic-marker.json').exists() else None,
              'inputs': [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in files]}
    output = Path(__file__).with_name('relationship-audit.json')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'inputs'}, ensure_ascii=False, indent=2))
