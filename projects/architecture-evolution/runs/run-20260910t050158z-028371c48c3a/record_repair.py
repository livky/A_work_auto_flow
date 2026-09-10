"""公开保存助手编写的修复分析、事件、经验和双文稿；不生成科学复核。

每批请求与 UUID 先落盘；重复调用复用原请求，公开回读固定修订。脚本只
保存本次明确撰写的文字，历史章节和规范记录仍由原事务层维护。
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OWNER = 'PRJ-ARCHITECTURE-EVOLUTION'
sys.path.insert(0, str(ROOT / 'automation/testing'))
import ai_review

FIELDS = ('schema_version','owner_id','kind','level','title','body_markdown','keywords',
          'sources','provenance_gap','record_reason','discovery','sensitivity','payload')
attempt_file = HERE / 'actual-ai-attempt.json'
if attempt_file.exists():
    attempt = json.loads(attempt_file.read_text(encoding='utf-8'))['attempt']
else:
    task = HERE / 'actual-ai-task.txt'
    task.write_text('公开保存本次来源恢复分析与实际事件，接入Project完整过程和简报；回读浮点双文稿与项目新增章节，记录真实观察和人工待审。', encoding='utf-8')
    attempt = str(ai_review.initialize(HERE / 'actual-ai', 'A04', task_file=task,
        actor='Codex主任务助手', model=None, context_mode='continuous'))
    ai_review.write_new(attempt_file, {'attempt': attempt})


def call(label, arguments):
    request = arguments[arguments.index('--request') + 1] if '--request' in arguments else None
    folder, receipt = ai_review.capture_call(attempt, [sys.executable, str(ROOT / 'automation/scripts/workspace_cli.py'),
        *arguments], request=request, cwd=ROOT, timeout=180)
    if receipt['exit_code']:
        raise RuntimeError(str(folder))
    value = json.loads((folder / 'stdout.txt').read_text(encoding='utf-8-sig'))
    (HERE / (label + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    return value


def fixed(record):
    return {'target_kind':'record','target_id':record['record_id'],'revision':record['revision'],
            'sha256':record['record_hash'],'locator':'完整固定正文','relation':'references'}


def draft(template, **values):
    result = {k: deepcopy(template[k]) for k in FIELDS}
    result.update(values)
    return result


def submit(label, state, operations):
    path = HERE / (label + '-request.json')
    if not path.exists():
        ai_review.write_new(path, {'schema_version':3,'request_id':str(uuid.uuid4()),
            'actor':{'kind':'ai','id':'assistant'},'owner_id':OWNER,
            'expected_head':state['head']['commit_id'],'operations':operations})
    call(label + '-validation', ['memory','validate-draft','--request',str(path)])
    receipt = call(label + '-receipt', ['memory','commit','--request',str(path)])
    current = call(label + '-readback', ['memory','inspect',OWNER])
    refs = {(r.get('client_key') or r['record_id']): fixed(current['records'][r['record_id']]) for r in receipt['record_results']}
    return current, refs


registry_path = ROOT / 'retrieval/sources.json'
registry = json.loads(registry_path.read_text(encoding='utf-8-sig'))
sid = 'SRC-ARCH-FLOATING-REPAIR-20260910'
analysis = HERE / 'REPAIR_ANALYSIS.md'
if not any(s.get('source_id') == sid for s in registry['sources']):
    registry['sources'].append({'source_id':sid,'path':analysis.relative_to(ROOT).as_posix(),
        'enabled':True,'sensitivity':'internal','context_role':'project'})
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
source = {'target_kind':'file','target_id':sid,'revision':None,'sha256':hashlib.sha256(analysis.read_bytes()).hexdigest(),
          'locator':'完整修复分析','relation':'input'}
state = call('recording-before', ['memory','inspect',OWNER])
template = next(r for r in state['records'].values() if r['kind']=='detail')
base = draft(template, sources=[source], body_markdown='', keywords=['来源迁移','索引覆盖','固定引用修复'],
    record_reason='保存本次真实故障、修复和验证边界，供以后材料迁移复用。', provenance_gap=None)
unit = draft(base, title='来源搬迁后的固定读取与索引覆盖恢复', payload={
    'unit_type':'analysis','retrieval_description':{'question':'如何确认已保存材料在搬迁后仍能读取和检索？',
    'method':'固定指纹来源映射、分层状态检查、公开查询和真实升级回归。',
    'key_findings':['组件就绪不代表规范依赖和索引覆盖正常；旧路径应以固定字节映射恢复。'],
    'applicable':['本次工作区材料迁移及合成研究恢复'], 'not_applicable':['任意内容替换和科学正确性保证'],
    'limitations':['本机Windows x64，人工与第二物理机未验收。']}, 'run_ref':None, 'evidence_refs':[source],
    'blocks':[{'block_id':'repair','role':'methods','markdown':analysis.read_text(encoding='utf-8'),'requires_block_ids':[]}],
    'figures':[],'missing_refs':[]})
event = draft(base, kind='event',level='L2',title='恢复遗漏来源、历史定位与检索覆盖',payload={
    'occurred_at':None,'question_refs':[],'goal_ref':None,'route_ref':None,'action':'诊断、补登记、固定映射、全文/向量补偿和页面复测',
    'observation':'文稿恢复后索引仍因旧Run路径排除材料；补齐映射后查询返回11个候选且没有覆盖警告。',
    'decision':'保留旧Run字节，新增显式位置映射与拒绝回归。','decision_refs':[source],'run_refs':[],
    'failure':None,'claims':[],'missing_refs':[]})
experience = draft(base, kind='experience',level='L3',title='材料迁移验收要检查实际可读依赖与召回',payload={
    'problem_structure':'规范材料存在，但来源位置或派生索引遗漏导致用户不可读或不可搜。',
    'applicable':['工作区材料迁移和恢复'], 'prohibited':['用组件就绪或重建成功冒充全面覆盖'],
    'failure_modes':['来源ID遗漏','旧Run路径失联','只看索引成功而不检查missing'],
    'recommendation':'分别核验固定文稿、原件路径、全文/向量状态及实际查询候选；迁移绑定原字节。',
    'retry_conditions':['登记、目录或索引恢复后'], 'claim_refs':[],'claims':[],'missing_refs':[]})
state, refs = submit('repair-units', state, [{'op':'put_record','client_key':key,'draft':value}
    for key,value in [('unit',unit),('event',event),('experience',experience)]])
unit_ref = refs['unit']
section_template = next(r for r in state['records'].values() if r['kind']=='document_section')
sections=[]
for key in ('process','brief'):
    blocks = [{'type':'unit','ref':unit_ref,'block_ids':['repair']}] if key=='process' else [
        {'type':'prose','markdown':'本次修复了遗漏来源登记、历史Run旧路径定位和检索索引。浮点双文稿可读，全局探索查询返回11项且无覆盖警告。102项Python、8项组件、3项浏览器及类型检查通过；真实setup保留检查通过。仅验证本机软件与合成材料，人工和科学复核未完成。','evidence_refs':[unit_ref]}]
    value=draft(section_template,title='来源恢复与索引覆盖修复',sources=[unit_ref],payload={
        'section_key':'floating-repair-'+key,'title':'来源恢复与索引覆盖修复','role':'discussion',
        'blocks':blocks,'watch_refs':[],'missing_refs':[]})
    sections.append({'op':'put_record','client_key':key,'draft':value})
state, section_refs=submit('repair-sections', state, sections)
operations=[]
for key,rid in [('process','MEM-3264fce7-c63f-504e-bdb5-3aaa1169eb7b'),('brief','MEM-ef137680-afa6-59b8-a263-f2bb33d256c4')]:
    old=state['records'][rid]
    payload=deepcopy(old['payload'])
    payload['section_refs'].append(section_refs[key])
    value=draft(old,payload=payload,sources=old['sources']+[section_refs[key]])
    value['change_reason']='追加本次固定来源与索引修复记录，保留历史章节。'
    operations.append({'op':'put_record','record_id':rid,'expected_revision':old['revision'],'draft':value})
old=state['records']['MEM-d17b92e3-e99d-563b-bec1-507552ac42ba']
payload=deepcopy(old['payload'])
payload['result_refs']+=list(refs.values())
value=draft(old,payload=payload,sources=old['sources']+list(refs.values()))
value['change_reason']='追加本次材料位置恢复经验及证据入口。'
operations.append({'op':'put_record','record_id':old['record_id'],'expected_revision':old['revision'],'draft':value})
state, document_refs=submit('repair-documents-map',state,operations)
for kind in ('process','report'):
    call('floating-'+kind+'-final',['memory','document','--request',str(ROOT/'research/floating-point-summation/fixtures'/('read-'+kind+'.request.json'))])
for kind,document_type in [('process','research_process'),('brief','research_report')]:
    path=HERE/('project-'+kind+'-request.json')
    path.write_text(json.dumps({'owner_id':OWNER,'document_type':document_type}),encoding='utf-8')
    call('project-'+kind+'-final',['memory','document','--request',str(path)])
print(json.dumps({'attempt':attempt,'unit_refs':refs,'sections':section_refs,'documents':document_refs},ensure_ascii=False))
