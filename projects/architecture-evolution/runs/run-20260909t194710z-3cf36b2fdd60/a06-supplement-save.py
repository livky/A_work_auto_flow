"""Record the already-authored A06 analysis via the public association CLI.

This helper transports explicit AI prose and refs already returned by a public
query. It does not invent readings or grade outcomes. Each product call is
captured append-only by ai_review, including nonzero save/index statuses.
"""
import json
import sys
import uuid
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
sys.path.insert(0, str(ROOT / 'automation/testing'))
import ai_review

attempt = Path(ai_review.read_json(RUN / 'a06-supplement-attempt.json')['attempt'])
fixture = ROOT / '.local/testing/material-query-f3-20260910-actual/workspace'
runtime = ROOT / 'services/qdrant/runtime/python.exe'
cli = ROOT / 'automation/scripts/workspace_cli.py'
actor = {'kind': 'ai', 'id': 'Codex /root/memory_review actual AI'}
capture = attempt / 'calls/call-47b56f1236744402a0d66f61a6eabce2/stdout.txt'
response = ai_review.read_json(capture)
packet = response['assembly']['value']
discovery = ai_review.read_json(attempt / 'calls/call-2eaaaa7e125a4b59b5cd13cab7c22294/stdout.txt')

# Project precisely the publicly delivered body, retaining duplicate necessary
# context as returned, instead of replacing it with the AI's own paraphrase.
delivered = attempt / 'delivered-full.md'
with delivered.open('x', encoding='utf-8') as stream:
    stream.write('# A06 固定全文实际交付\n\n')
    for part in packet['parts']:
        stream.write('## ' + part['heading'] + '\n\n')
        stream.write('固定依据：`' + json.dumps(part['refs'], ensure_ascii=False) + '`\n\n')
        stream.write(part['markdown'] + '\n\n')
event = {
    'actor': actor['id'], 'origin': 'public material-query search --assemble',
    'capture_path': str(capture), 'locator': 'assembly 全部五个内容部分，四个独立固定记录',
    'coverage': 'full',
    'observation': '已在工具输出实际读完水箱模型r2（原线性推导和新增饱和边界）、必要定义r1、APIr1、饱和输入r1；定义作为直接与必要上下文重复出现，不算独立证据。核对变量单位、API缺少状态方程、幂等/超时限制及水箱特定参数不可达。组包ok、complete=true；无现实试验。',
}
event_path = attempt / 'read-full.json'
ai_review.write_new(event_path, event)
read_path = ai_review.record_read(attempt, event_path)

refs = packet['contributors']
def legacy(ref):
    """Convert only the public ref field names required by the memory API."""
    return {'target_kind': ref['kind'], 'target_id': ref['id'],
            'revision': ref['revision'], 'sha256': ref['sha256'],
            'locator': ref.get('locator') or '', 'relation': 'references'}

# The selection order below follows the observed candidate list (model,
# definitions, API, saturation); it is checked against the actual delivered refs.
by_id = {ref['id']: legacy(ref) for ref in refs}
model = discovery['value']['candidates'][0]['refs'][0]
api = discovery['value']['candidates'][2]['refs'][0]
heads = dict(discovery['basis']['owner_heads'])
request = {
    'request_id': str(uuid.uuid4()), 'actor': actor, 'owner_id': 'RES-F3-RETRY',
    'expected_head': heads['RES-F3-RETRY'],
    'title': 'SYNTHETIC F3 重试分段检查的条件采用（词项发现补充）',
    'reason': '自然语言词项发现候选并实际固定读完后，保存当前模型r2的条件参考；未执行实验或科学复核',
    'discovery': 'workspace_summary', 'sensitivity': 'internal',
    'body_markdown': (attempt / 'ADOPTION.md').read_text(encoding='utf-8'),
    'payload': {
        'from': by_id[model['id']], 'to': by_id[api['id']],
        'relation': 'analogous_to', 'status': 'candidate',
        'explanation': '条件采用分段检查方法；不能从水箱连续模型推导API稳定、吞吐或最终成功。',
        'shared_structure': '先核对适用前提，再区分动作未触顶与触顶后的边界行为；不建立同一状态方程。',
        'transfer_limits': [
            '仅在幂等/去重、错误分类、超时、总耗时与重试计数约定明确后采用检查方法。',
            'K有流量对液位的单位，r无量纲；两者数值和动力学结论不能互换。',
            'API缺少服务端容量、到达率、队列和响应概率模型，不保证稳定、成功或最优吞吐。',
            '待用独立事件序列检查封顶、终止、连续失败及同步唤醒；本次未执行这些实验。',
        ],
        'basis_refs': [legacy(ref) for ref in refs],
    },
}
request_path = attempt / 'authored-requests/adoption-save.json'
ai_review.write_new(request_path, request)
call, receipt = ai_review.capture_call(attempt,
    [str(runtime), '-X', 'utf8', str(cli), '--root', str(fixture),
     'memory', 'associations-decide', '--request', str(request_path)],
    request=request_path, cwd=fixture)
ai_review.write_new(attempt / 'adoption-save-call.json',
                    {'call': str(call), 'exit_code': receipt['exit_code'], 'read': str(read_path)})
print(json.dumps({'call': str(call), 'exit_code': receipt['exit_code'],
                  'read': str(read_path)}, ensure_ascii=False))
