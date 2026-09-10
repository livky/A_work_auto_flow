"""Read-only public document/query checks against the repaired live workspace."""
import json
from pathlib import Path
import sqlite3
import sys
from dataclasses import asdict
from time import perf_counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'automation/scripts'))
from memory.service import MemoryService
from memory.api import dispatch
from material_query.coordinator import Coordinator
from material_query.contracts import QueryRequest, Scope, DefinitionRef, AssociationOptions
from material_query.budget import DEFAULT_BUDGET
from material_query.wire import json_value


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


checks = {}
scope = Scope(None, None, None, None, None, None, None, False, (), (), None, None)
for keyword in ('浮点数', '浮点'):
    query = QueryRequest(DefinitionRef('full', '1'), '', (keyword,), scope, scope, 'exploration',
        AssociationOptions('off', 'existing-relations', '1', 5, .2, None), DEFAULT_BUDGET,
        'fixed', 20, 'reject', (), '')
    request = json_value(query)
    save('query-' + keyword + '.request.json', request)
    coordinator = Coordinator(ROOT)
    started = perf_counter()
    result = coordinator.search(request)
    save('query-' + keyword + '.response.json', result)
    candidates = (result.get('value') or {}).get('candidates', [])
    checks[keyword] = {'status': result['status'], 'candidates': len(candidates),
        'warnings': result['warnings'], 'elapsed_seconds': perf_counter() - started,
        'titles': [item['title'] for item in candidates]}
    coordinator.close()
    assert result['status'] == 'ok' and candidates and not result['warnings'], checks[keyword]
db = sqlite3.connect((ROOT / 'retrieval/generated/search.sqlite3').as_uri() + '?mode=ro', uri=True)
checks['sqlite_integrity'] = db.execute('PRAGMA quick_check').fetchone()[0]
checks['indexed_owners'] = db.execute('SELECT count(*) FROM memory_index_state').fetchone()[0]
checks['float_entries'] = db.execute('SELECT count(*) FROM memory_entries WHERE owner_id=?', ('RES-FLOATING-POINT-SUMMATION',)).fetchone()[0]
save('verification-final.json', checks)
print(json.dumps(checks, ensure_ascii=False, indent=2))
