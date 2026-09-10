"""经公开CLI保存本轮审计正文/事件及双文稿入口，不写人工评价。

仅适用于此Run；每次调用保留独立stdout/stderr和退出码。固定请求可重试，
失败则停止，不自行覆盖冲突版本。运行：automation/python.ps1 <本脚本>。
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OWNER='PRJ-ARCHITECTURE-EVOLUTION'
FIELDS=('schema_version','owner_id','kind','level','title','body_markdown','keywords','sources','provenance_gap','record_reason','discovery','sensitivity','payload')
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def call(label,args):
    home=HERE/'public-calls'/str(uuid.uuid4())
    home.mkdir(parents=True)
    command=[sys.executable,str(ROOT/'automation/scripts/workspace_cli.py'),*args]
    result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=240)
    (home/'stdout.txt').write_bytes(result.stdout)
    (home/'stderr.txt').write_bytes(result.stderr)
    write(home/'receipt.json',{'command':command,'exit_code':result.returncode})
    if result.returncode:
        raise RuntimeError(str(home))
    value=json.loads(result.stdout.decode('utf-8-sig'))
    write(HERE/(label+'.json'),value)
    return value
def draft(template,**changes):
    value={k:deepcopy(template[k]) for k in FIELDS}
    value.update(changes)
    return value
def fixed(record):
    return {'target_kind':'record','target_id':record['record_id'],'revision':record['revision'],'sha256':record['record_hash'],'locator':'完整固定正文','relation':'references'}
def submit(label,state,operations):
    path=HERE/(label+'-request.json')
    if not path.exists():
        write(path,{'schema_version':3,'request_id':str(uuid.uuid4()),'actor':{'kind':'ai','id':'assistant'},'owner_id':OWNER,'expected_head':state['head']['commit_id'],'operations':operations})
    call(label+'-validation',['memory','validate-draft','--request',str(path)])
    receipt=call(label+'-receipt',['memory','commit','--request',str(path)])
    state=call(label+'-readback',['memory','inspect',OWNER])
    return state,{(r.get('client_key') or r['record_id']):fixed(state['records'][r['record_id']]) for r in receipt['record_results']}

analysis=HERE/'AUDIT_REPORT.md'
registry_path=ROOT/'retrieval/sources.json'
registry=read(registry_path)
sid='SRC-LOCAL-COVERAGE-AUDIT-20260910'
if not any(s.get('source_id')==sid for s in registry['sources']):
    # 新增本轮固定来源；保留登记前副本，不修改任何旧来源与授权。
    (HERE/'sources-before-audit.snapshot').write_bytes(registry_path.read_bytes())
    registry['sources'].append({'source_id':sid,'path':analysis.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(analysis.read_bytes()).hexdigest(),'enabled':True,'sensitivity':'internal','context_role':'project','discovery':'trace_only'})
    write(registry_path,registry)
source={'target_kind':'file','target_id':sid,'revision':None,'sha256':hashlib.sha256(analysis.read_bytes()).hexdigest(),'locator':'登记覆盖审计正文','relation':'input'}
state=call('recording-before',['memory','inspect',OWNER])
template=next(r for r in state['records'].values() if r['kind']=='detail')
base=draft(template,sources=[source],body_markdown='',keywords=['登记审计','索引覆盖','人工验收'],record_reason='保存本地覆盖核验事实、缺口和人工操作安排。',provenance_gap=None)
unit=draft(base,title='本地登记、双索引与人工验收覆盖审计',payload={'unit_type':'analysis','retrieval_description':{
    'question':'当前本地数据是否均有登记和索引，如何完成工作台及AI最终验收？','method':'对比业务登记、固定文件哈希、记忆提交链、预期投影和公开文稿回读。',
    'key_findings':['登记主体和4份文稿可读，但历史输入变化、旧Run缺失与snapshot解析缺口仍须区分。'],
    'applicable':['当前工作区的小规模本地登记审计与人工验收安排'],'not_applicable':['整个电脑文件覆盖、科学结论确认或检索质量保证'],'limitations':['人工评价、第二物理机和业务检索评测未执行。']},
    'run_ref':None,'evidence_refs':[source],'blocks':[{'block_id':'audit','role':'methods','markdown':analysis.read_text(encoding='utf-8'),'requires_block_ids':[]}],'figures':[],'missing_refs':[]})
event=draft(base,kind='event',level='L2',title='完成覆盖基线核对并安排分批人工验收',payload={'occurred_at':None,'question_refs':[],'goal_ref':None,'route_ref':None,
    'action':'只读对账、公开文稿回读、派生材料索引和关系刷新、准备人工清单',
    'observation':'71个来源存在，498个Run登记文件可解析，8个历史输入与当前源码不同；3个snapshot旧索引不可用。',
    'decision':'保留历史哈希和权限，区分缺口与合理排除；真实区只读、演示区写操作。','decision_refs':[source],'run_refs':[],'failure':None,'claims':[],'missing_refs':[]})
state,refs=submit('audit-units',state,[{'op':'put_record','client_key':k,'draft':v} for k,v in [('unit',unit),('event',event)]])
section_template=next(r for r in state['records'].values() if r['kind']=='document_section')
operations=[]
for key in ('process','brief'):
    blocks=[{'type':'unit','ref':refs['unit'],'block_ids':['audit']}] if key=='process' else [{'type':'prose','markdown':'本地审计确认主体和四份文稿可读；保留历史源码指纹变化、两项旧Run缺失及三份snapshot旧解析缺口。人工验收分真实区阅读、演示区交互和实际AI旅程，所有人工判断待审。','evidence_refs':[refs['unit']]}]
    operations.append({'op':'put_record','client_key':key,'draft':draft(section_template,title='本地覆盖审计与人工验收安排',sources=[refs['unit']],payload={'section_key':'local-audit-'+key,'title':'本地覆盖审计与人工验收安排','role':'discussion','blocks':blocks,'watch_refs':[],'missing_refs':[]})})
state,sections=submit('audit-sections',state,operations)
operations=[]
for key,rid in [('process','MEM-3264fce7-c63f-504e-bdb5-3aaa1169eb7b'),('brief','MEM-ef137680-afa6-59b8-a263-f2bb33d256c4')]:
    old=state['records'][rid]; payload=deepcopy(old['payload']); payload['section_refs'].append(sections[key])
    value=draft(old,payload=payload,sources=old['sources']+[sections[key]],change_reason='追加本轮固定覆盖审计，历史章节保持原引用。')
    operations.append({'op':'put_record','record_id':rid,'expected_revision':old['revision'],'draft':value})
old=state['records']['MEM-d17b92e3-e99d-563b-bec1-507552ac42ba']; payload=deepcopy(old['payload']); payload['result_refs']+=list(refs.values())
operations.append({'op':'put_record','record_id':old['record_id'],'expected_revision':old['revision'],'draft':draft(old,payload=payload,sources=old['sources']+list(refs.values()),change_reason='新增审计技术单元与事件入口，L3复用既有覆盖检查经验。')})
state,documents=submit('audit-documents-map',state,operations)
write(HERE/'recording-summary.json',{'records':refs,'sections':sections,'documents':documents,'human_review':'pending'})
print(json.dumps({'records':refs,'documents':documents},ensure_ascii=False))
