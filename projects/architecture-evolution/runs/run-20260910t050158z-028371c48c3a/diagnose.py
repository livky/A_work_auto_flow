"""Read-only checks of the reported live database and one fixed document reference."""
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'automation/scripts'))
from memory.service import MemoryService
from memory.document import Reader
from memory.errors import MemoryError

db = sqlite3.connect((ROOT / 'retrieval/generated/search.sqlite3').as_uri() + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
print('integrity', db.execute('PRAGMA quick_check').fetchall()[0][0])
for table in ('memory_records', 'memory_entries', 'memory_index_state'):
    print(table, db.execute('SELECT count(*) FROM ' + table).fetchone()[0])
print('float_index', [dict(r) for r in db.execute('SELECT * FROM memory_index_state WHERE owner_id=?', ('RES-FLOATING-POINT-SUMMATION',))])
service = MemoryService(ROOT)
reader = Reader(service)
state = reader.state('RES-FLOATING-POINT-SUMMATION')
print('records', len(state['records']), 'generation', state['head']['generation'])
ref = state['records']['MEM-51cc78a8-53d2-5503-9d00-d6131d178a96']
try:
    reader.check_ref({'target_kind':'record', 'target_id':ref['record_id'], 'revision':ref['revision'], 'sha256':ref['record_hash']})
except MemoryError as exc:
    print('reference_error', vars(exc))
print('registered_sources', len(json.loads((ROOT / 'retrieval/sources.json').read_text(encoding='utf-8-sig'))['sources']))
