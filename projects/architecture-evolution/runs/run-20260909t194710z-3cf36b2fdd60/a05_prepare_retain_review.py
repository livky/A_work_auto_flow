"""Serialize the agent-authored A05 decisions after actual full packet reading.

The prose below is the AI's explicit reviewed input, not a generated judgement
from test booleans. Protected plan/basis/context fields are copied unchanged.
"""
import json
from pathlib import Path
import sys

run = Path(__file__).resolve().parent
root = run.parents[3]
sys.path.insert(0, str(root / 'automation/testing'))
import ai_review
state = ai_review.read_json(run / 'a05-supplement-state.json')
attempt = Path(state['attempt'])
plan = ai_review.read_json(attempt / 'outcomes/no-new-evidence-plan-retry.json')['result']['value']
expected = plan['plan_digest']
decisions = {
    'MEM-6f7931dc-84bc-510e-b865-60a6d530e3ef': '实际读到同一饱和输入r1与原件：仍是qmax=0.15、目标2、c=0.1的合成约束，没有新参数、实验或修订；保留输入原记录。',
    'MEM-2810407a-91e3-5114-b909-9a737b5e7885': '实际读完r2原线性段与saturation_boundary：已包含qreq=0.20>0.15、hsat=1.5与0.5m偏差，并保留未饱和条件；此次相同固定输入未产生新的内容要求，保留r2，不再堆积同一边界段。',
    'MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a': '实际读完定义r1和水箱原件，面积、流量、K单位、误差及clip定义与当前r2一致；新输入没有改变字典，保留固定定义r1。',
}
for item in plan['items']:
    item.update(action='retain', reasons=[decisions[item['ref']['id']]], draft_json=None)
refs = []
for part in plan['context_items']:
    refs.extend(part['refs'])
plan['reviewed_refs'] = refs
plan['semantic_reviewer'] = 'Codex /root/frontier_review actual AI'
plan['reviewer_kind'] = 'ai'
plan['review_note'] = '本次实际完整阅读5个交付部分及各固定引用。A09已把同一饱和输入纳入模型r2，本次无新证据，三个detail全部retain；双文稿当前impact均changes=[]。不修改受保护原上下文/未检查范围。未重新进行现实试验、科学review或完整语义召回；其他主题未检查。A05-E1/E2仅交叉复审A09，不伪装重新执行其修订。'
review = attempt / 'authored-review/retain-plan.json'
ai_review.write_new(review, {'plan': plan, 'expected_digest': expected})

for label, capture, origin, coverage, observation in (
    ('read-new-plan', attempt / 'delivered/no-new-evidence-plan.md',
     'public material-query maintenance-plan, no-new-evidence-plan-retry', 'full',
     '实际阅读全部5部分、三个规范对象和两份已登记原件，omitted均为空；模型r2已包含相同饱和约束，故逐项决定retain。'),
    ('read-a09-cross-reference', run / 'a05-cross-reference-review.md',
     'readonly independent review of existing A09 artifacts', 'full',
     '完整阅读子代理对E1/E2的路径、旧/新SHA、双文稿一致、未变记录和幂等回执的交叉复审；这些是复用既有执行，不声称本次重演。'),
    ('read-current-process-impact', attempt / 'outcomes/process-impact-current.json',
     'public memory document-impact on isolated final process r2', 'full',
     '实际读到changes/affected_section_ids/uncovered_unit_ids均空，写入0，共同依据为定义r1、模型r2、饱和r1。'),
    ('read-current-report-impact', attempt / 'outcomes/report-impact-current.json',
     'public memory document-impact on isolated final report r2', 'full',
     '实际读到changes/affected_section_ids/uncovered_unit_ids均空，写入0，与完整稿相同共同依据。'),
):
    event = attempt / 'authored-review' / (label + '.json')
    ai_review.write_new(event, {'actor': 'Codex /root/frontier_review actual AI', 'origin': origin,
        'capture_path': str(capture), 'locator': '完整文件', 'coverage': coverage, 'observation': observation})
    print(ai_review.record_read(attempt, event))
print(review)
