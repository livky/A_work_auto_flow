"""W08/W09 材料包行为：真实规范保存、版本水位、预算和只读边界。"""
from copy import deepcopy
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

import test_memory_research as research_fixture
from memory import history, packets, research, summaries
from memory.errors import MemoryError
from memory.service import MemoryService


class PacketTests(unittest.TestCase):
    setUp = research_fixture.ResearchTests.setUp
    put = research_fixture.ResearchTests.put
    operation = research_fixture.ResearchTests.operation
    request = research_fixture.ResearchTests.request
    save = research_fixture.ResearchTests.save
    goal = research_fixture.ResearchTests.goal
    event = research_fixture.ResearchTests.event
    route = research_fixture.ResearchTests.route
    question = research_fixture.ResearchTests.question

    def experience(self, text='先检查输入，再决定方法'):
        return {'problem_structure': '同类合成输入条件', 'recommendation': text,
                'applicable': ['只适用当前合成输入'], 'prohibited': ['禁止跨温度直接迁移😀'],
                'failure_modes': ['未取得输入'], 'retry_conditions': ['有新的固定输入'],
                'claim_refs': [], 'claims': []}

    def seed_history(self):
        old = self.save(research.set_goal('RES-R', self.goal(), metadata=self.metadata))
        first_route = self.save(self.operation('route', self.route(old)))
        done = self.save(self.operation('event', self.event(goal_ref=research.fixed_ref(old), route_ref=research.fixed_ref(first_route),
                                                          action='完成 A 的合成计算', observation='A 已取得结果')))
        failed = self.save(self.operation('event', self.event(goal_ref=research.fixed_ref(old), failure={
            'category': 'insufficient_evidence', 'tested_scope': 'B 输入', 'result': '未取得 B 输入',
            'cannot_infer': '不能宣称 B 已完成', 'retry_conditions': ['取得 B 输入']})))
        question = self.save(self.operation('question', self.question('blocked', question='B 输入何时可取得')))
        check = self.save(research.checkpoint('RES-R', {'goal_ref': research.fixed_ref(old), 'route_refs': [research.fixed_ref(first_route)],
                    'completed_refs': [research.fixed_ref(done)], 'question_refs': [research.fixed_ref(question)],
                    'next_step': '取得 B 输入并先核对，A 不无理由重做', 'prerequisites': ['只读原件', 'B 输入尚未取得'],
                    'stop_reason': '等待输入', 'budget_remaining': {'value': None, 'reason': 'unknown', 'note': '尚未提供预算'}}, metadata=self.metadata))
        new = self.save(research.set_goal('RES-R', self.goal('新目标 B', constraints=['只读原件', '不得宣称 B 已完成'],
                      change_impact='A 仍按旧目标评价，新增 B 的输入条件'), previous=old, metadata=self.metadata))
        second_route = self.save(self.operation('route', self.route(new, hypothesis='B 新路线')))
        self.put('runs/attempt/run.json', {'run_id': 'RUN-R', 'status': 'running', 'claims': [],
                                         'related_research_ids': ['RES-R'], 'goal_ref': research.fixed_ref(old)})
        return old, new, check, done

    def test_p01_history_pages_cover_all_fixed_revisions_and_one_legacy_run(self):
        old, new, _check, _done = self.seed_history()
        replacement = self.save(self.operation('question', self.question(question='替代后研究问题')))
        obsolete = self.save(self.operation('question', self.question(question='待替代问题')))
        self.save(research.transition_question(obsolete, 1, 'superseded', {
            'change_reason': '真实替代关系回归', 'replacement_ref': research.fixed_ref(replacement)}))
        self.save(self.operation('event', self.event(claims=[{'claim_id': 'CLM-HISTORY',
            'statement': '历史撤回合成结论', 'kind': 'inference', 'scope': 'synthetic:only', 'evidence_refs': []}])))
        self.service.review({'schema_version': 1, 'request_id': str(uuid.uuid4()), 'target_claim_id': 'CLM-HISTORY',
            'state': 'retracted', 'actor': {'kind': 'workflow', 'id': 'synthetic-test'}, 'reason': '历史撤回回归',
            'scope': 'synthetic:only', 'evidence_refs': [], 'expected_head': self.service.inspect('RES-R')['head']['commit_id']})
        whole = history.build_history(self.service, 'RES-R', limit=500)
        combined, offset = [], 0
        while offset is not None:
            page = history.build_history(self.service, 'RES-R', offset=offset, limit=3, basis_heads=whole['basis_heads'])
            combined.extend(page['items'])
            offset = page['next_offset']
        self.assertEqual([x['id'] for x in combined], [x['id'] for x in whole['items']])
        self.assertEqual(len(combined), len({x['id'] for x in combined}))
        self.assertEqual(sum(x['canonical_id'] == 'RUN-R' for x in combined), 1)
        self.assertEqual({x['revision'] for x in combined if x['canonical_id'] == old['record_id']}, {1, 2})
        self.assertTrue(all(x['occurred_label'] == '发生时间未知' for x in combined))
        self.assertTrue(any(x['role'] == 'failure' for x in combined))
        self.assertTrue(any(x['role'] == 'unresolved_question' for x in combined))
        self.assertTrue(any(x['role'] == 'question_superseded' for x in combined))
        self.assertTrue(any(x['kind'] == 'review' and x['record']['payload']['state'] == 'retracted' for x in combined))
        self.assertEqual(new['payload']['previous_goal_ref']['revision'], 1)

    def test_p02_resume_keeps_new_goal_old_checkpoint_and_real_pause(self):
        old, new, check, done = self.seed_history()
        result = history.resume(self.service, 'RES-R', budget=16000, selection={'stage': 'wide'})
        text = result['context_text']
        for expected in ('新目标 B', '只读原件', 'B 输入尚未取得', 'A 不无理由重做', done['record_id']):
            self.assertIn(expected, text)
        self.assertTrue(result['manifest']['resume']['checkpoint_goal_mismatch'])
        self.assertFalse(result['manifest']['resume']['execution_started'])
        self.assertEqual(self.service.inspect('RES-R', 1, record_id=old['record_id'])['record'], old)
        self.assertIn(check['record_id'], result['manifest']['selection']['full_ids'])

    def test_p03_resume_reports_changed_input_retracted_answer_and_removed_registration(self):
        measured = self.put('data/source.txt', '原测量\n')
        removed = self.put('data/removed.txt', '移除登记来源\n')
        source = {'target_kind': 'file', 'target_id': 'SRC-P03', 'revision': None,
                  'sha256': hashlib.sha256(measured.read_bytes()).hexdigest(), 'locator': 'lines:1-1', 'relation': 'input'}
        other = {**source, 'target_id': 'SRC-REMOVED', 'sha256': hashlib.sha256(removed.read_bytes()).hexdigest()}
        self.put('retrieval/sources.json', {'sources': [
            {'source_id': 'SRC-P03', 'path': 'data/source.txt', 'enabled': True, 'sensitivity': 'internal'},
            {'source_id': 'SRC-REMOVED', 'path': 'data/removed.txt', 'enabled': True, 'sensitivity': 'internal'}]})
        goal = self.save(research.set_goal('RES-R', self.goal(), metadata=self.metadata))
        claim = {'claim_id': 'CLM-P03', 'statement': '合成答案仅用于撤回检查', 'kind': 'inference',
                 'scope': 'synthetic:only', 'evidence_refs': [source]}
        answer = self.save(self.operation('event', self.event(claims=[claim]), sources=[source, other], provenance_gap=None))
        question = self.save(self.operation('question', self.question('resolved', resolution_refs=[research.fixed_ref(answer)])))
        checkpoint = self.save(research.checkpoint('RES-R', {'goal_ref': research.fixed_ref(goal), 'route_refs': [],
            'completed_refs': [research.fixed_ref(answer)], 'question_refs': [research.fixed_ref(question)],
            'next_step': '核对两份输入与答案后才选择下一步', 'prerequisites': ['当前答案仍有效'], 'stop_reason': '等待复查',
            'budget_remaining': {'value': None, 'reason': 'unknown', 'note': '预算未知'}}, metadata=self.metadata))
        review = {'schema_version': 1, 'request_id': str(uuid.uuid4()), 'target_claim_id': 'CLM-P03',
                  'state': 'retracted', 'actor': {'kind': 'workflow', 'id': 'synthetic-test'}, 'reason': '合成撤回操作',
                  'scope': 'synthetic:only', 'evidence_refs': [], 'expected_head': self.service.inspect('RES-R')['head']['commit_id']}
        self.service.review(review)
        measured.write_text('已变更测量\n', encoding='utf-8')
        self.put('retrieval/sources.json', {'sources': [{'source_id': 'SRC-P03', 'path': 'data/source.txt', 'enabled': True, 'sensitivity': 'internal'}]})
        result = history.resume(self.service, 'RES-R', budget=16000, selection={'stage': 'wide'})
        risks = json.dumps(result['manifest']['missing'], ensure_ascii=False)
        self.assertIn('SRC-REMOVED', risks)
        self.assertIn('SRC-P03', risks)
        self.assertIn('CLM-P03', risks)
        self.assertIn('EVIDENCE_INELIGIBLE', risks)
        self.assertNotEqual(result['manifest']['status'], 'complete')
        self.assertEqual(self.service.inspect('RES-R', 1, record_id=checkpoint['record_id'])['record'], checkpoint)
        formal = packets.expand(self.service, [research.fixed_ref(answer)], {'owner_id': 'RES-R', 'purpose': 'formal', 'scope': 'synthetic:only'})
        self.assertEqual(formal['context_text'], '')

    def test_p04_p05_unicode_whole_records_and_required_budget(self):
        record = self.save(self.operation('experience', self.experience(), body_markdown='中文😀边界完整。'))
        settings = {'owner_id': 'RES-R', 'full_ids': [record['record_id']]}
        full = packets.expand(self.service, [research.fixed_ref(record)], settings, budget=16000)
        length = len(full['context_text'])
        exact = packets.expand(self.service, [research.fixed_ref(record)], settings, budget=length)
        self.assertEqual(exact['context_text'], full['context_text'])
        self.assertEqual(exact['manifest']['budget']['used'], length)
        for budget in (length - 1, 1, 0):
            packet = packets.expand(self.service, [research.fixed_ref(record)], settings, budget=budget)
            self.assertEqual(packet['context_text'], '')
            self.assertEqual(packet['manifest']['status'], 'insufficient_budget')
            self.assertIn(record['record_id'], packet['manifest']['required_not_full'])
        self.put('retrieval/config.json', {'context_chars': length - 1})
        bounded = packets.expand(self.service, [research.fixed_ref(record)], settings, budget=length * 2)
        self.assertEqual(bounded['manifest']['budget']['effective'], length - 1)
        self.assertEqual(bounded['context_text'], '')
        # 实际运行 JavaScript Array.from；接收端 core 无 Node 不依赖此开发断言。
        node = shutil.which('node')
        if node:
            result = subprocess.run([node, '-e', 'let s="";process.stdin.setEncoding("utf8");process.stdin.on("data",x=>s+=x);process.stdin.on("end",()=>console.log(Array.from(s).length));'],
                                    input=full['context_text'].encode('utf-8'), capture_output=True, check=True)
            self.assertEqual(int(result.stdout.strip()), length)

    def test_p04_u07_native_newlines_exact_budget_short_form_and_idempotence(self):
        first = self.save(self.operation('experience', self.experience(), body_markdown='第一行😀\n第二行\r\n第三行\r结束'))
        second = self.save(self.operation('experience', self.experience(), body_markdown='另一个记录\n中文🙂'))
        refs = [research.fixed_ref(first), research.fixed_ref(second)]
        selection = {'owner_id': 'RES-R', 'full_ids': [first['record_id'], second['record_id']]}
        complete = packets.expand(self.service, refs, selection, 16000)
        text = complete['context_text']
        self.assertEqual(packets.normalize_context_text(text), text)
        if os.name == 'nt':
            self.assertIn('\r\n', text)
            self.assertIsNone(re.search(r'(?<!\r)\n|\r(?!\n)', text))
        else:
            self.assertNotIn('\r', text)
        self.assertEqual(complete['manifest']['budget']['used'], len(text))
        self.assertEqual(sum(row['codepoints'] for row in complete['manifest']['items']) + len(packets.PART_SEPARATOR), len(text))
        exact = packets.expand(self.service, refs, selection, len(text))
        self.assertEqual(exact['context_text'], text)
        tight = packets.expand(self.service, refs, selection, len(text)-1)
        self.assertLessEqual(tight['manifest']['budget']['used'], len(text)-1)
        self.assertTrue(tight['manifest']['required_not_full'])
        for record in (first, second):
            self.assertEqual(self.service.inspect('RES-R', 1, record_id=record['record_id'])['record'], record)
        long_record = self.save(self.operation('experience', self.experience(), body_markdown='长正文😀\n'*4000))
        representation = {'target': research.fixed_ref(long_record), 'slot': 'result',
                          'text': '已存短表示\r\n中文🙂\n边界完整', 'boundary_refs': long_record['sources']}
        self.save(self.operation('representation', representation))
        shorter = packets.expand(self.service, [research.fixed_ref(long_record)], {'owner_id':'RES-R'}, 2500)
        self.assertEqual(shorter['manifest']['items'][0]['mode'], 'short')
        self.assertEqual(shorter['manifest']['items'][0]['codepoints'], len(shorter['context_text']))
        self.assertEqual(packets.normalize_context_text(shorter['context_text']), shorter['context_text'])
        self.assertIn('禁止跨温度直接迁移😀', shorter['context_text'])

    def test_p06_feedback_preserves_formal_scope_selection_budget_and_stops(self):
        record = self.save(self.operation('event', self.event(), body_markdown='不应进入正式正文'))
        requested = {'refs': [research.fixed_ref(record)], 'owner_id': 'RES-R', 'purpose': 'formal', 'scope': 'synthetic:only',
                     'include_ids': [record['record_id']], 'full_ids': [record['record_id']],
                     'exclude_ids': [record['record_id']], 'budget': 1000}
        first = packets.build_context(self.service, requested)
        second = packets.build_context(self.service, {'feedback_from': first})
        third = packets.build_context(self.service, {'feedback_from': second})
        for index, result in enumerate((first, second, third)):
            manifest = result['manifest']
            self.assertEqual(manifest['stage'], ('focus', 'investigate', 'wide')[index])
            self.assertEqual(manifest['expansion_count'], index)
            self.assertEqual(manifest['purpose'], 'formal')
            self.assertEqual(manifest['scope'], 'synthetic:only')
            self.assertEqual(manifest['budget']['requested'], 1000)
            self.assertEqual(manifest['selection']['full_ids'], [record['record_id']])
            self.assertEqual(result['context_text'], '')
        with self.assertRaises(MemoryError):
            packets.build_context(self.service, {'feedback_from': third})
        with self.assertRaises(MemoryError):
            packets.build_context(self.service, {'feedback_from': first, 'purpose': 'exploration'})

    def test_p07_roles_deduplicate_representations_without_hidden_body(self):
        exp = self.save(self.operation('experience', self.experience(), body_markdown='独特正文 marker-😀'))
        question = self.save(self.operation('question', self.question()))
        fail = self.save(self.operation('event', self.event(failure={'category': 'counterexample', 'tested_scope': '测试输入',
                    'result': '得到反例', 'cannot_infer': '不代表其他输入', 'retry_conditions': []})))
        representation = self.save(self.operation('representation', {'target': research.fixed_ref(exp), 'slot': 'boundary',
                    'text': '已保存短表示', 'boundary_refs': []}))
        relation = self.save(self.operation('association', {'from': research.fixed_ref(exp), 'to': research.fixed_ref(fail),
                    'relation': 'analogous_to', 'explanation': '错误类比候选', 'shared_structure': '合成共有条件',
                    'transfer_limits': ['禁止跨域迁移'], 'basis_refs': [], 'status': 'rejected'}))
        packet = packets.expand(self.service, [research.fixed_ref(exp), research.fixed_ref(representation),
                    research.fixed_ref(fail), research.fixed_ref(question), research.fixed_ref(relation)],
                    {'owner_id': 'RES-R', 'stage': 'wide'}, budget=16000)
        identities = [item['canonical_id'] for item in packet['manifest']['items']]
        self.assertEqual(identities.count(exp['record_id']), 1)
        self.assertNotIn(representation['record_id'], identities)
        roles = {item['role'] for item in packet['manifest']['items']}
        self.assertTrue({'unreviewed_experience', 'counterevidence', 'unresolved_question', 'analogy_rejected'} <= roles)
        self.assertIn('禁止跨温度直接迁移😀', packet['context_text'])
        self.assertNotIn('marker-😀', json.dumps(packet['manifest'], ensure_ascii=False))

    def test_p08_fixed_heads_reject_concurrent_change_and_page_drift(self):
        event = self.save(self.operation('event', self.event()))
        first = history.build_history(self.service, 'RES-R', limit=1)
        self.save(self.operation('event', self.event(action='新增事件')))
        with self.assertRaises(MemoryError) as ctx:
            history.build_history(self.service, 'RES-R', offset=1, limit=1, basis_heads=first['basis_heads'])
        self.assertEqual(ctx.exception.code, 'STALE_BASIS')
        missing = packets.expand(self.service, [{**research.fixed_ref(event), 'revision': 999}], {'owner_id': 'RES-R'})
        self.assertEqual(missing['context_text'], '')
        self.assertTrue(missing['manifest']['missing'])
        self.put('research/second/research.json', {'research_id': 'RES-SECOND', 'title': '第二快照对象', 'claims': [], 'dependencies': []})
        second_operation = self.operation('event', self.event(action='第二对象的固定结果'))
        second_operation['draft']['owner_id'] = 'RES-SECOND'
        second_receipt = self.service.commit({'schema_version': 1, 'request_id': str(uuid.uuid4()),
            'actor': {'kind': 'workflow', 'id': 'test'}, 'owner_id': 'RES-SECOND', 'expected_head': None,
            'operations': [second_operation]})
        second = self.service.inspect('RES-SECOND', record_id=second_receipt['record_results'][0]['record_id'])['record']
        stable = packets.expand(self.service, [research.fixed_ref(event), research.fixed_ref(second)],
                                {'owner_ids': ['RES-R', 'RES-SECOND']})
        self.assertEqual(set(stable['manifest']['basis_heads']), {'RES-R', 'RES-SECOND'})
        original = packets.Snapshot.recheck
        fired = []
        def change_then_recheck(snapshot, expected=None):
            if not fired:
                fired.append(True)
                self.save(self.operation('event', self.event(action='并发真实提交')))
            return original(snapshot, expected)
        with patch.object(packets.Snapshot, 'recheck', change_then_recheck), self.assertRaises(MemoryError) as ctx:
            packets.expand(self.service, [research.fixed_ref(event), research.fixed_ref(second)],
                           {'owner_ids': ['RES-R', 'RES-SECOND']})
        self.assertEqual(ctx.exception.code, 'STALE_BASIS')

    def test_p10_summary_balances_selected_owners_without_duplicate_report_prose(self):
        # A selected owner can accumulate long experiments and old embedded
        # reports before another owner is selected. Real material from both
        # must get a budget floor; merely printing both owner names is not enough.
        from test_memory_contracts import examples
        from test_memory_documents_v3 import unit_payload
        from memory.documents import fixed_ref
        unit = self.save(self.operation('detail', unit_payload(), schema_version=3, body_markdown=''))
        for number in range(8):
            self.save(self.operation('event', self.event(action=f'长实验 {number}'),
                                    body_markdown='THERMAL_LONG_EXPERIMENT ' + '热学过程 ' * 450))
        payload = examples()['map']
        payload['report'] = {'version': 1, 'title': '旧长篇报告', 'sections': [{'section_id': 'old',
            'title': '完整过程', 'role': 'introduction', 'blocks': [{'type': 'prose',
            'markdown': 'DUPLICATED_REPORT_PROSE ' + '完整旧报告 ' * 5000, 'evidence_refs': [fixed_ref(unit)]}]}]}
        mapping = self.save(self.operation('map', payload, schema_version=2, body_markdown='DUPLICATED_MAP_BODY ' + '旧综合 ' * 5000))
        self.put('research/pressure/research.json', {'research_id': 'RES-PRESSURE', 'title': '合成压力', 'claims': [], 'dependencies': []})
        other = self.operation('experience', self.experience('PRESSURE_STRUCTURE'), body_markdown='PRESSURE_ACTUAL_MATERIAL')
        other['draft']['owner_id'] = 'RES-PRESSURE'
        other['draft']['payload']['prohibited'] = ['PRESSURE_DO_NOT_TRANSFER_TO_THERMAL']
        receipt = self.service.commit({'schema_version': 1, 'request_id': str(uuid.uuid4()),
            'actor': {'kind': 'workflow', 'id': 'test'}, 'owner_id': 'RES-PRESSURE', 'expected_head': None, 'operations': [other]})
        pressure_id = receipt['record_results'][0]['record_id']
        for budget in (16000, 3500):
            value = summaries.prepare(self.service, '共同条件', ['RES-R', 'RES-PRESSURE'], budget)
            self.assertLessEqual(len(value['context_text']), budget)
            self.assertIn('PRESSURE_ACTUAL_MATERIAL', value['context_text'])
            self.assertIn('PRESSURE_DO_NOT_TRANSFER_TO_THERMAL', value['context_text'])
            self.assertNotIn('DUPLICATED_REPORT_PROSE', value['context_text'])
            self.assertNotIn('DUPLICATED_MAP_BODY', value['context_text'])
            self.assertNotIn('ONLY_FULL_RESULT', value['context_text'])
            self.assertEqual({row['owner_id'] for row in value['manifest']['items']}, {'RES-R', 'RES-PRESSURE'})
            self.assertTrue(all(row['status'] == 'covered' for row in value['manifest']['summary']['owner_coverage']))
        full = summaries.prepare(self.service, '共同条件', ['RES-R', 'RES-PRESSURE'], 16000,
                                 {'full_ids': [mapping['record_id']]})
        self.assertIn(mapping['record_id'], full['manifest']['required_not_full'])
        self.assertIn('PRESSURE_ACTUAL_MATERIAL', full['context_text'])
        excluded = summaries.prepare(self.service, '共同条件', ['RES-R', 'RES-PRESSURE'], 16000,
                                     {'exclude_ids': [pressure_id]})
        self.assertNotIn('PRESSURE_ACTUAL_MATERIAL', excluded['context_text'])
        self.assertEqual(excluded['manifest']['summary']['owner_coverage'][1]['status'], 'not_in_packet')
        tiny = summaries.prepare(self.service, '共同条件', ['RES-R', 'RES-PRESSURE'], 20)
        self.assertLessEqual(len(tiny['context_text']), 20)
        self.assertTrue(tiny['manifest']['missing'])

    def test_p09_summary_prepare_fixed_selected_results_and_single_owner_save(self):
        a = self.save(self.operation('experience', self.experience('主题共性 A'), body_markdown='A 与 B 共有问题条件'))
        excluded = self.save(self.operation('event', self.event(), body_markdown='excluded-private-marker'))
        self.put('research/other/research.json', {'research_id': 'RES-B', 'title': '合成 B', 'claims': [], 'dependencies': []})
        operation = self.operation('experience', self.experience('主题差异 B'), body_markdown='B 有自己的迁移边界')
        operation['draft']['owner_id'] = 'RES-B'
        request = {'schema_version': 1, 'request_id': str(uuid.uuid4()), 'actor': {'kind': 'workflow', 'id': 'test'},
                   'owner_id': 'RES-B', 'expected_head': None, 'operations': [operation]}
        self.service.commit(request)
        self.put('research/unselected/research.json', {'research_id': 'RES-UNSELECTED', 'title': '未选归属', 'claims': [], 'dependencies': []})
        outside = deepcopy(operation)
        outside['draft'].update(owner_id='RES-UNSELECTED', body_markdown='主题 outside-summary-corpus-marker')
        self.service.commit({**request, 'request_id': str(uuid.uuid4()), 'owner_id': 'RES-UNSELECTED', 'operations': [outside]})
        before = {p: p.read_bytes() for p in self.root.glob('research/*/research.json')}
        prepared = summaries.prepare(self.service, '主题', ['RES-R', 'RES-B'], 16000,
                    {'stage': 'wide', 'exclude_ids': [excluded['record_id']]})
        self.assertIn('主题共性 A', prepared['context_text'])
        self.assertIn('主题差异 B', prepared['context_text'])
        self.assertNotIn('excluded-private-marker', prepared['context_text'])
        self.assertNotIn('outside-summary-corpus-marker', prepared['context_text'])
        self.assertTrue(all(item['owner_id'] in {'RES-R', 'RES-B'} for item in prepared['manifest']['items']))
        self.assertFalse(prepared['manifest']['summary']['ai_summary_completed'])
        self.assertTrue({'RES-R', 'RES-B'} <= set(prepared['basis_heads']))
        self.assertTrue(prepared['source_refs'])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.put('research/target/research.json', {'research_id': 'RES-TARGET', 'title': '总结归属', 'claims': [], 'dependencies': []})
        draft = self.operation('experience', self.experience('用户给出的新综合'), body_markdown='人工提供的跨研究说明')['draft']
        draft.update(owner_id='RES-TARGET', sources=prepared['source_refs'], provenance_gap=None)
        draft['payload']['claims'] = [{'claim_id': 'CLM-SUMMARY', 'statement': '未复核的合成解释', 'kind': 'inference',
                                      'scope': 'synthetic:only', 'evidence_refs': prepared['source_refs']}]
        save_request = {'request_id': str(uuid.uuid4()), 'actor': {'kind': 'ai', 'id': 'test'},
                'owner_id': 'RES-TARGET', 'expected_head': None, 'draft': draft, 'basis_heads': prepared['basis_heads']}
        saved = summaries.save(self.service, save_request)
        replay = summaries.save(self.service, save_request)
        self.assertEqual(replay['commit_id'], saved['commit_id'])
        row = self.service.inspect('RES-TARGET', record_id=saved['record_results'][0]['record_id'])['record']
        self.assertEqual(row['level'], 'L3')
        self.assertEqual(row['owner_id'], 'RES-TARGET')
        self.assertEqual(packets.Snapshot(self.service).adapter.claim_state('CLM-SUMMARY')['review_state'], 'not-reviewed')
        changed = research._draft(row)
        changed['payload']['prohibited'].append('新增解释边界')
        changed['change_reason'] = '相同来源版本下补充明确禁用条件'
        updated = summaries.save(self.service, {'request_id': str(uuid.uuid4()), 'actor': {'kind': 'ai', 'id': 'test'},
                'owner_id': 'RES-TARGET', 'expected_head': saved['commit_id'], 'record_id': row['record_id'],
                'expected_revision': 1, 'draft': changed, 'basis_heads': prepared['basis_heads']})
        self.assertEqual(updated['record_results'][0]['revision'], 2)
        self.assertEqual(self.service.inspect('RES-TARGET', 1, record_id=row['record_id'])['record'], row)
        import test_memory_contracts
        map_draft = self.operation('map', test_memory_contracts.examples()['map'])['draft']
        map_draft.update(owner_id='RES-TARGET', sources=prepared['source_refs'], provenance_gap=None)
        map_draft['payload'].update(result_refs=prepared['source_refs'])
        map_request = {'request_id': str(uuid.uuid4()), 'actor': {'kind': 'ai', 'id': 'test'},
                      'owner_id': 'RES-TARGET', 'expected_head': updated['commit_id'],
                      'draft': map_draft, 'basis_heads': prepared['basis_heads']}
        mapped = summaries.save(self.service, map_request)
        map_row = self.service.inspect('RES-TARGET', record_id=mapped['record_results'][0]['record_id'])['record']
        self.assertEqual(map_row['level'], 'L4')
        self.save(self.operation('event', self.event(action='总结准备后真实来源提交')))
        stale_request = {**map_request, 'request_id': str(uuid.uuid4()), 'expected_head': mapped['commit_id']}
        with self.assertRaises(MemoryError) as ctx:
            summaries.save(self.service, stale_request)
        self.assertEqual(ctx.exception.code, 'STALE_BASIS')


if __name__ == '__main__':
    unittest.main()
