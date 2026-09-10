"""顺序收口：验证本轮保存→登记证据→补偿派生索引→刷新与校验。

必须在record_audit.py成功后运行。调用以独立编号保存，失败停止；任何
旧Run或历史哈希不由此脚本更改。本轮Run的执行状态仅表示审计完成。
"""
import hashlib
import json
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
FINAL=HERE/'final'
FINAL.mkdir(exist_ok=True)
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def call(label,args,require_success=True):
    command=[sys.executable,str(ROOT/'automation/scripts/workspace_cli.py'),*args]
    print(label,flush=True)
    value=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600)
    suffix=str(uuid.uuid4())
    (FINAL/(label+'-'+suffix+'.stdout.txt')).write_bytes(value.stdout)
    (FINAL/(label+'-'+suffix+'.stderr.txt')).write_bytes(value.stderr)
    write(FINAL/(label+'-'+suffix+'.call.json'),{'command':command,'exit_code':value.returncode})
    if require_success and value.returncode:
        raise RuntimeError(label+' failed')
    try:
        result=json.loads(value.stdout.decode('utf-8-sig'))
    except ValueError:
        result={'exit_code':value.returncode,'output':value.stdout.decode('utf-8-sig')}
    write(FINAL/(label+'.json'),result)
    return result

summary=read(HERE/'recording-summary.json')
current=read(HERE/'audit-documents-map-readback.json')
verified=[]
for batch in ('audit-units','audit-sections','audit-documents-map'):
    request=read(HERE/(batch+'-request.json'))
    receipt=read(HERE/(batch+'-receipt.json'))
    for operation in request['operations']:
        rid=operation.get('record_id') or next(r['record_id'] for r in receipt['record_results'] if r.get('client_key')==operation['client_key'])
        actual=current['records'][rid]
        assert all(actual[k]==v for k,v in operation['draft'].items()),rid
        verified.append({'record_id':rid,'revision':actual['revision']})
write(HERE/'recording-verification.json',{'verified':verified,'human_review':'pending','scientific_review':'not-performed'})
for kind in ('research_process','research_report'):
    request=FINAL/(kind+'-request.json')
    write(request,{'owner_id':'PRJ-ARCHITECTURE-EVOLUTION','document_type':kind})
    value=call(kind,['memory','document','--request',str(request)])
    assert value['report']['complete'] and not value['missing']

run=read(HERE/'run.json')
run.update(status='succeeded',started_at=run['created_at'],ended_at=datetime.now(timezone.utc).isoformat(),
    question='核对本地登记与索引覆盖，并安排工作台及实际AI人工验收。',
    conclusion='完成只读覆盖审计和人工验收准备；历史缺口、权限排除与旧snapshot解析缺口显式保留。',
    limitations=['人工/科学/第二物理机验收未执行。','旧Run缺失、历史输入变化与三份旧snapshot解析缺口未被索引补偿消除。'])
git=subprocess.run(['git','-c','safe.directory='+str(ROOT),'rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
run['code']={'commit':git.stdout.strip() if git.returncode==0 else None,'dirty':True}
run['quality_results']=[{'check':'baseline structure and immutable history','status':'passed'},
                        {'check':'four documents public readback','status':'passed'},
                        {'check':'human acceptance','status':'pending'}]
write(HERE/'run.json',run)
artifacts=['README.md','AUDIT_REPORT.md','HUMAN_CHECKLIST.md','audit-20260910T063348Z.json',
           'details-20260910T063550Z.json','raw-listings.json','recording-summary.json','recording-verification.json',
           'index-knowledge-initial.log','relations-refresh-initial.json','doctor.json']
args=['run-register',run['run_id'],'--input',str(HERE/'sources-before-audit.snapshot')]
for name in artifacts:
    args+=['--artifact',str(HERE/name)]
call('register',args)
request=FINAL/'reconcile-request.json'; write(request,{'vector':'auto'})
reconcile=call('memory-reconcile',['memory','reconcile','--request',str(request)])
legacy=call('legacy-index',['index-knowledge'])
relations=call('relations-refresh',['relations','refresh'])
view=call('relations-view',['relations','view','--format','json'])
call('navigation',['refresh-index'])
call('validate',['validate'])
db=sqlite3.connect((ROOT/'retrieval/generated/search.sqlite3').as_uri()+'?mode=ro',uri=True)
db.row_factory=sqlite3.Row
states=[dict(r) for r in db.execute('SELECT * FROM memory_index_state')]
statistics={'integrity':db.execute('PRAGMA quick_check').fetchone()[0],
            'memory_entries':db.execute('SELECT count(*) FROM memory_entries').fetchone()[0],
            'memory_fts':db.execute('SELECT count(*) FROM memory_fts').fetchone()[0],
            'legacy_states':dict(db.execute('SELECT state,count(*) FROM docs GROUP BY state'))}
write(FINAL/'summary.json',{'statistics':statistics,'index_states':states,'legacy_unavailable':legacy.get('unavailable'),
                          'relations':relations,'recording_verified':verified,'human_review':'pending'})
print(json.dumps(statistics,ensure_ascii=False))
