"""Seal actual execution metadata and AI observations; keep human review pending."""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'automation/testing'))
import ai_review
read=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
attempt=read(HERE/'actual-ai-attempt.json')['attempt']
observation={'actor':'Codex主任务助手','origin':{'public_calls':'record_repair.py 的独立CLI回执；本次实际CUA工作台操作'},
    'capture_path':'recording-verification.json','locator':'新记录字段、四文稿完整性、冻结文件核对',
    'coverage':'summary','observation':'已实际阅读新章节的回读正文、固定引用和验证摘要；浮点文稿8章/4章、Project12章/4章均完整，无缺失。工作台已观察浮点8章目录、公式、正文和11个候选；未逐像素复核全部历史图示。',
    'unread_or_missing':['未逐段重读全部历史Project内容；导航fixture details/README.md有既存指纹差异，未将隔离例子全套复现记为通过。']}
if not (HERE/'ai-reading.json').exists():
    ai_review.write_new(HERE/'ai-reading.json',observation)
    ai_review.record_read(attempt,HERE/'ai-reading.json')
assessment={'actor':'Codex主任务助手','comparisons':[
    {'expectation_id':'A04-E1','status':'meets','observation':'两种浮点文稿和Project双文稿公开回读均complete=true；新增章节顺序和正文已核对。','evidence_refs':['recording-verification.json','project-brief-final.json','floating-process-final.json']},
    {'expectation_id':'A04-E2','status':'meets','observation':'新增完整章节和简报引用同一个固定技术单元，简报保留本机/合成数据/人工和科学未审限制。','evidence_refs':['repair-sections-request.json','project-brief-final.json']},
    {'expectation_id':'A04-E3','status':'cannot-assess','observation':'工作台实际看到8章目录、公式、正文和查询组包；本次未对所有历史图示及链接逐项做视觉复核，因此不把整项判为满足。','evidence_refs':['AI_REVIEW.md']}],
    'readable_artifacts':[{'title':'实际AI与人工入口','path':str(HERE/'actual-ai/AI_REVIEW.md')},
                          {'title':'修复分析','path':str(HERE/'actual-ai/REPAIR_ANALYSIS.md')}],
    'limitations':['实际用户故障路径已复测；完整历史图示视觉验收、人工及第二物理机未执行。'],
    'human_review':'pending','scientific_review':'not-reviewed'}
for name in ('AI_REVIEW.md','REPAIR_ANALYSIS.md'):
    (HERE/'actual-ai'/name).write_bytes((HERE/name).read_bytes())
ai_review.write_new(HERE/'ai-assessment-v3.json',assessment)
ai_review.record_assessment(attempt,HERE/'ai-assessment-v3.json')
ai_review.render(HERE/'actual-ai')
run=read(HERE/'run.json')
run.update(status='succeeded',started_at=run['created_at'],ended_at=datetime.now(timezone.utc).isoformat(),
    question='当前浮点研究为何不可读、不可检索，数据库是否损坏？',
    conclusion='数据库完整性正常；修复缺失来源及旧Run路径映射，恢复双文稿和全文/向量索引，用户查询返回候选且无索引覆盖警告。',
    limitations=['本机Windows x64及合成研究；人工、第二物理机和科学复核未执行。',
                  '冻结导航details/README.md存在指纹差异，本轮未修改其字节或宣称隔离例子全套复现通过。'],
    quality_results=[{'check':'selected quick regression','status':'passed'},
                     {'check':'live floating documents and queries','status':'passed'},
                     {'check':'real setup expanded workspace preservation','status':'passed'}])
run['code']={'commit':subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'dirty':True}
(HERE/'run.json').write_text(json.dumps(run,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
