"""Archive the AI's explicit, already-read A05 observations and assessment.

No program infers acceptance from counts: expectation statuses and limitations
below are authored by the executing AI after reading the displayed evidence.
The recorder only freezes these declarations and checks their structure.
"""
import hashlib
import json
from pathlib import Path
import sys

run = Path(__file__).resolve().parent
root = run.parents[3]
sys.path.insert(0, str(root / 'automation/testing'))
import ai_review
state = ai_review.read_json(run / 'a05-supplement-state.json')
attempt = Path(state['attempt'])
a09 = run / 'actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7'
actor = 'Codex /root/frontier_review actual AI'
new_reads = []
for name, path, origin, observation in (
    ('read-empty-apply', attempt / 'outcomes/no-change-apply.json', 'public material-query maintenance-apply',
     '完整阅读公开应用结果：ok、commits为空、pending_items为空、indexed；实际read_bytes非零，保留原固定basis与owner_heads。'),
    ('read-source-missing', attempt / 'outcomes/missing-saturation-plan.json', 'public material-query maintenance-plan while one registered original is absent',
     '完整阅读实际rejected/SOURCE_MISSING、value=null、source_missing停止原因、Issue after_external_change和输出0；缺失没有被当作完整材料或无影响。'),
    ('read-source-restoration', attempt / 'outcomes/missing-saturation-plan-restoration.json', 'exact-byte restoration of the isolated synthetic original',
     '完整阅读恢复回执，原件恢复前后同SHA且bytes_restored=true；仅A05副本发生临时移动。'),
    ('read-snapshot-comparison', attempt / 'mechanical-verification.json', 'mechanical comparison of saved A05 snapshots and public outcomes',
     '完整阅读55个规范/来源文件在retain后及恢复后相同、公开owner结果相等，恢复计划5部分与已读内容相同；不把原F3并发A06新增列入本断言。'),
    ('read-a09-original-analysis', a09 / 'AI-ANALYSIS.md', 'existing A09 actual AI report; cross-reference only',
     '完整阅读原A09对局部修订、retain输入/定义、文稿独立事务、旧版保留和幂等的分析及限制；这不是本次重演。'),
    ('read-a09-document-receipt', a09 / 'document-update-receipt.json', 'existing A09 fixed dual-document execution receipt; cross-reference only',
     '完整阅读两文稿r2和各自SHA、历史r1仍完整、changes_after为空及scientific_review未评估；此事实属于原A09执行。'),
):
    event = attempt / 'authored-review' / (name + '.json')
    ai_review.write_new(event, {'actor': actor, 'origin': origin, 'capture_path': str(path),
        'locator': '完整文件', 'coverage': 'full', 'observation': observation})
    new_reads.append(str(ai_review.record_read(attempt, event)))

prefix = f'A05/{attempt.name}/'
assessment = {
    'actor': actor,
    'comparisons': [
        {'expectation_id': 'A05-E1', 'status': 'meets',
         'observation': '限定为交叉复用A09已经执行的明确影响路径和局部修订：我阅读原A09分析及独立源回执复审，定义/饱和输入保持r1，受影响两章节/文稿才更新。本次又完整读新计划5部分，对已处理的相同输入作三项retain并公开应用，未重复写正文。没有声称重演A09。',
         'evidence_refs': ['../../A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/AI-ANALYSIS.md',
             '../../A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/outcomes/impact-before-process.json',
             '../../A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/outcomes/impact-before-report.json',
             '../../../a05-cross-reference-review.md', 'delivered/no-new-evidence-plan.md', 'outcomes/no-change-apply.json']},
        {'expectation_id': 'A05-E2', 'status': 'meets',
         'observation': '限定为A09既有固定历史与双文稿回执，加本次独立副本的当前impact再读。原历史两稿仍r1/完整，当前两稿r2共同固定定义r1、模型r2、饱和r1，impact changes均空。原r1是A09显式创建的合成旧依据基线，不能冒充现实历史恢复。',
         'evidence_refs': ['../../A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/document-update-receipt.json',
             '../../A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/outcomes/historical-process-read.json',
             '../../A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/outcomes/historical-report-read.json',
             'outcomes/process-impact-current.json', 'outcomes/report-impact-current.json']},
        {'expectation_id': 'A05-E3', 'status': 'meets',
         'observation': '本次新增实际执行：无新证据计划→全文读取→AI三项retain→review→新request_id apply，ok且commits/pending均空；55份规范/来源哈希与公开owner前后相同。实际移走副本登记原件后计划rejected/SOURCE_MISSING，Issue要求after_external_change；恢复相同SHA后新计划交付相同5部分。旧A09同request_id幂等没有替代这两项新执行。',
         'evidence_refs': ['outcomes/no-new-evidence-plan-retry.json', 'delivered/no-new-evidence-plan.md',
             'outcomes/no-change-retain-review.json', 'outcomes/no-change-apply.json',
             'outcomes/missing-saturation-plan.json', 'outcomes/missing-saturation-plan-restoration.json',
             'outcomes/restored-source-plan.json', 'mechanical-verification.json']},
    ],
    'readable_artifacts': [
        {'title': 'A05实际补充阅读与逐项判断', 'path': prefix + 'AI-ANALYSIS.md'},
        {'title': '新计划五部分完整交付', 'path': prefix + 'delivered/no-new-evidence-plan.md'},
        {'title': '55文件与公开结果机械核对', 'path': prefix + 'mechanical-verification.json'},
    ],
    'limitations': [
        'A05-E1/E2复用并复审A09实际证据，非本次重新执行局部修订；旧双文稿为明确创建的合成基线。',
        '当前planner仍产生defer任务，是否retain来自实际AI判断；不宣称自动识别任意语义等价或全库无变化。',
        '无新正文时保留本地计划、审查和应用审计回执；无重复堆积仅指规范知识内容/修订。',
        '首条material-query前置--root参数调用解析失败保留；改用隔离cwd后另存新执行。',
        'A06在原F3的获准新增与本独立副本分开，不把原目录整个并发时段HEAD恒定作为断言。',
        '本机Windows合成TANK/SATURATION材料；未验证真实业务、语义向量质量、人工/科学结论或另一物理机。',
    ],
    'human_review': 'pending', 'scientific_review': 'not-reviewed',
}
authored = attempt / 'authored-review/assessment.json'
ai_review.write_new(authored, assessment)
assessment_path = ai_review.record_assessment(attempt, authored)
page = ai_review.render(run / 'actual-ai')
paths = [attempt / 'manifest.json', attempt / 'AI-ANALYSIS.md', assessment_path,
         attempt / 'mechanical-verification.json', attempt / 'outcomes/no-change-apply.json',
         attempt / 'outcomes/missing-saturation-plan.json', attempt / 'outcomes/missing-saturation-plan-restoration.json']
receipt = {'schema_version': 1, 'scenario': 'A05', 'attempt': str(attempt), 'workspace': state['workspace'],
    'assessment': str(assessment_path), 'human_report': str(page),
    'actual_calls': len(list((attempt / 'calls').glob('*/result.json'))),
    'reading_events': len(list((attempt / 'reads').glob('*/event.json'))),
    'ai_expectations': {'A05-E1': 'meets_by_explicit_A09_reuse_and_current_inspection',
                        'A05-E2': 'meets_by_explicit_A09_reuse_and_current_inspection',
                        'A05-E3': 'meets_by_new_isolated_public_execution'},
    'raw_failed_call_preserved': 'calls/call-e9bacd169f1841c5aafa619ea01259fb',
    'canonical_content_writes': 0, 'canonical_files_verified_unchanged': 55,
    'source_missing_observed': 'SOURCE_MISSING', 'source_bytes_restored': True,
    'human_review': 'pending', 'scientific_review': 'not-reviewed',
    'fingerprints': [{'path': str(path.relative_to(run)).replace('\\', '/'),
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths]}
ai_review.write_new(run / 'a05-supplement-receipt.json', receipt)
print(json.dumps(receipt, ensure_ascii=False, indent=2))
