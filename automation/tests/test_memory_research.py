"""W05：通过真实 MemoryService 提交检查研究状态和版本，不模拟实验成功。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from memory import research, policy
from memory.errors import MemoryError
from memory.service import MemoryService


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='memory-research-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.put('research/topic/research.json', {'research_id': 'RES-R', 'title': 'SYNTHETIC ONLY',
                                                'status': 'active', 'claims': [], 'dependencies': []})
        self.put('runs/attempt/run.json', {'run_id': 'RUN-R', 'status': 'running', 'claims': []})
        self.service = MemoryService(self.root)
        self.metadata = {'record_reason': 'SYNTHETIC ONLY 研究状态回归',
                         'provenance_gap': '合成软件状态，不代表现实业务证据',
                         'sources': [], 'discovery': 'owner_only', 'sensitivity': 'internal'}

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value, encoding='utf-8')
        return path

    def operation(self, kind, payload, **metadata):
        return {'op': 'put_record', 'client_key': str(uuid.uuid4()),
                'draft': {'owner_id': 'RES-R', 'kind': kind, 'title': 'SYNTHETIC ONLY ' + kind,
                          'body_markdown': '', **self.metadata, **metadata, 'payload': deepcopy(payload)}}

    def request(self, operations):
        head = self.service.inspect('RES-R')['head']
        return {'schema_version': 1, 'request_id': str(uuid.uuid4()), 'owner_id': 'RES-R',
                'actor': {'kind': 'workflow', 'id': 'synthetic-research-test'},
                'expected_head': head['commit_id'] if head else None, 'operations': operations}

    def save(self, operation):
        receipt = self.service.commit(self.request([operation]))
        self.assertIn(receipt['save_status'], {'committed', 'no_change'})
        result = receipt['record_results'][0]
        return self.service.inspect('RES-R', result['revision'], record_id=result['record_id'])['record']

    def question(self, state='open', **overrides):
        return {'question': '合成问题是否解决', 'status': state, 'decision_affected': '下一步选择',
                'missing_evidence': ['需要当前版本测量'], 'resolution_refs': [],
                'replacement_ref': None, 'reopen_reason': None, **overrides}

    def event(self, **overrides):
        return {'occurred_at': None, 'question_refs': [], 'goal_ref': None, 'route_ref': None,
                'action': '记录合成观察', 'observation': '软件断言的输入', 'decision': None,
                'decision_refs': [], 'run_refs': [], 'failure': None, 'claims': [], **overrides}

    def goal(self, objective='目标 A', **overrides):
        return {'objective': objective, 'constraints': ['约束 A'], 'success_criteria': ['通过合成检查'],
                'previous_goal_ref': None, 'change_impact': '初始合成目标', **overrides}

    def route(self, goal, **overrides):
        return {'goal_ref': research.fixed_ref(goal), 'hypothesis': '合成路线假设', 'status': 'planned',
                'attempt_refs': [], 'blocker': None, 'next_step': '检查获准输入',
                'reopen_condition': '出现新的固定测量依据', 'replacement_ref': None, **overrides}

    def test_r01_every_legal_question_transition_has_one_new_revision(self):
        answer = self.save(self.operation('event', self.event(decision='按实际合成观察选择方案 A')))
        substitute = self.save(self.operation('question', self.question()))
        answer_ref, replacement = research.fixed_ref(answer), research.fixed_ref(substitute)
        for start, destinations in research.QUESTION_TRANSITIONS.items():
            for end in sorted(destinations):
                with self.subTest(start=start, end=end):
                    initial = self.question(start, resolution_refs=[answer_ref] if start == 'resolved' else [],
                                            replacement_ref=replacement if start == 'superseded' else None)
                    old = self.save(self.operation('question', initial))
                    basis = {'change_reason': '合成合法状态转换'}
                    if end == 'resolved':
                        basis['resolution_refs'] = [answer_ref]
                    if end == 'superseded':
                        basis['replacement_ref'] = replacement
                    if start in {'resolved', 'superseded'}:
                        basis['reopen_reason'] = '获得新的合成测量，需要重新调查'
                    current = self.save(research.transition_question(old, 1, end, basis))
                    self.assertEqual(current['revision'], 2)
                    self.assertEqual(current['payload']['status'], end)
                    history = self.service.inspect('RES-R', 1, record_id=old['record_id'])['record']
                    self.assertEqual(history, old)

    def test_r01_invalid_resolution_replacement_and_reopening_preserve_history(self):
        answer = self.save(self.operation('event', self.event(decision='合成答案')))
        question = self.save(self.operation('question', self.question()))
        other_question = self.save(self.operation('question', self.question()))
        for end, basis in [
                ('resolved', {'change_reason': '无答案'}),
                ('superseded', {'change_reason': '自我替代', 'replacement_ref': research.fixed_ref(question)}),
                ('superseded', {'change_reason': '错类别替代', 'replacement_ref': research.fixed_ref(answer)}),
                ('resolved', {'change_reason': '不能自我解决', 'resolution_refs': [research.fixed_ref(question)]}),
                ('resolved', {'change_reason': '另一个未决问题不是答案', 'resolution_refs': [research.fixed_ref(other_question)]})]:
            before = self.service.inspect('RES-R')['head']
            with self.subTest(end=end, basis=basis), self.assertRaises(MemoryError) as ctx:
                self.save(research.transition_question(question, 1, end, basis))
            self.assertEqual(ctx.exception.code, 'INVALID_TRANSITION')
            self.assertEqual(self.service.inspect('RES-R')['head'], before)
        resolved = self.save(research.transition_question(question, 1, 'resolved',
                             {'change_reason': '合成答案可取得', 'resolution_refs': [research.fixed_ref(answer)]}))
        for end in ('open', 'investigating', 'blocked', 'superseded'):
            before = self.service.inspect('RES-R')['head']
            with self.subTest(end=end), self.assertRaises(MemoryError):
                self.save(research.transition_question(resolved, 2, end, {'change_reason': '缺重开理由'}))
            self.assertEqual(self.service.inspect('RES-R')['head'], before)
        # 直接 put 也必须走领域门；不能通过绕过便捷构造器制造非法终态跳转。
        draft = research._draft(resolved)
        draft['payload']['status'] = 'blocked'
        with self.assertRaises(MemoryError) as ctx:
            self.save({'op': 'put_record', 'record_id': resolved['record_id'], 'expected_revision': 2, 'draft': draft})
        self.assertEqual(ctx.exception.code, 'INVALID_TRANSITION')
        superseded = self.save(research.transition_question(other_question, 1, 'superseded',
                               {'change_reason': '另一个问题替代', 'replacement_ref': research.fixed_ref(resolved)}))
        for end in ('open', 'investigating'):
            before = self.service.inspect('RES-R')['head']
            with self.subTest(superseded_to=end), self.assertRaises(MemoryError) as ctx:
                self.save(research.transition_question(superseded, 2, end, {'change_reason': '缺重开理由'}))
            self.assertEqual(ctx.exception.code, 'INVALID_TRANSITION')
            self.assertEqual(self.service.inspect('RES-R')['head'], before)

    def test_r02_completed_native_objects_do_not_close_or_hide_questions(self):
        records = [self.save(self.operation('question', self.question(state))) for state in ('open', 'investigating', 'blocked')]
        view = research.question_view(self.service.inspect('RES-R')['records'])
        self.put('runs/attempt/run.json', {'run_id': 'RUN-R', 'status': 'succeeded', 'claims': []})
        self.put('research/topic/research.json', {'research_id': 'RES-R', 'title': 'SYNTHETIC ONLY',
                                                'status': 'completed', 'claims': [], 'dependencies': []})
        current = research.question_view(self.service.inspect('RES-R')['records'])
        self.assertEqual(view, current)
        self.assertEqual(sum(item['unresolved'] for item in current), 3)
        self.assertEqual({record['payload']['status'] for record in records}, {'open', 'investigating', 'blocked'})

    def test_r03_goal_revision_keeps_old_attempt_and_route_versions(self):
        original = self.save(research.set_goal('RES-R', self.goal(), metadata=self.metadata))
        route = self.save(self.operation('route', self.route(original)))
        attempt = self.save(self.operation('event', self.event(goal_ref=research.fixed_ref(original), route_ref=research.fixed_ref(route))))
        new = self.save(research.set_goal('RES-R', self.goal('目标 B', constraints=['约束 B'], change_impact='旧尝试仍按 A 评价，B 新增约束'),
                                          previous=original, metadata=self.metadata))
        self.assertEqual(new['record_id'], original['record_id'])
        self.assertEqual(new['revision'], 2)
        self.assertEqual(new['payload']['previous_goal_ref']['revision'], 1)
        self.assertEqual(new['payload']['previous_goal_ref']['target_id'], original['record_id'])
        for record in (route, attempt):
            current = self.service.inspect('RES-R', record_id=record['record_id'])['record']
            self.assertEqual(current, record)
            self.assertEqual(current['payload']['goal_ref']['revision'], 1)
        old = self.service.inspect('RES-R', 1, record_id=original['record_id'])['record']
        self.assertEqual(old['payload']['constraints'], ['约束 A'])
        self.assertEqual(new['payload']['constraints'], ['约束 B'])
        self.assertEqual(self.save({'op': 'put_record', 'record_id': new['record_id'], 'expected_revision': 2,
                                   'draft': research._draft(new)})['revision'], 2)

    def test_r04_route_block_reopen_and_close_preserve_attempts(self):
        goal = self.save(research.set_goal('RES-R', self.goal(), metadata=self.metadata))
        attempt = self.save(self.operation('event', self.event(goal_ref=research.fixed_ref(goal))))
        route = self.save(self.operation('route', self.route(goal, attempt_refs=[research.fixed_ref(attempt)])))
        with self.assertRaises(MemoryError):
            research.route_transition(route, 1, 'blocked', {'change_reason': '缺具体阻碍'})
        blocked = self.save(research.route_transition(route, 1, 'blocked',
                            {'change_reason': '输入尚未到达', 'blocker': '缺少本次测量文件', 'next_step': '等待用户取得测量文件'}))
        with self.assertRaises(MemoryError):
            research.route_transition(blocked, 2, 'active', {'change_reason': '不能只说可以继续', 'evidence_changes': '未附固定依据'})
        evidence = self.save(self.operation('event', self.event(decision='合成输入已补齐，可继续人工评估')))
        active = self.save(research.route_transition(blocked, 2, 'active',
                           {'change_reason': '阻碍条件已补齐', 'evidence_changes': '取得当前测量记录',
                            'basis_refs': [research.fixed_ref(evidence)], 'next_step': '核对测量版本后由用户选择执行'}))
        closed = self.save(research.route_transition(active, 3, 'closed',
                           {'change_reason': '合成路线已结束', 'next_step': '保留记录，等待新的研究要求'}))
        self.assertEqual(closed['revision'], 4)
        self.assertIsNone(closed['payload']['blocker'])
        self.assertEqual(closed['payload']['attempt_refs'], route['payload']['attempt_refs'])
        self.assertIn('依据变化', active['change_reason'])
        self.assertEqual(self.service.inspect('RES-R', 2, record_id=route['record_id'])['record'], blocked)

    def test_r05_four_failure_categories_are_not_reclassified(self):
        for category in ('execution', 'no_improvement', 'counterexample', 'insufficient_evidence'):
            failure = {'category': category, 'tested_scope': '合成作用域', 'result': '本次没有得到目标结果',
                       'cannot_infer': '不能推及未测试输入', 'retry_conditions': ['有独立新依据才重试']}
            saved = self.save(self.operation('event', self.event(failure=failure)))
            self.assertEqual(saved['payload']['failure'], failure)
            bad = deepcopy(failure)
            del bad['cannot_infer']
            before = self.service.inspect('RES-R')['head']
            with self.subTest(category=category), self.assertRaises(MemoryError) as ctx:
                self.save(self.operation('event', self.event(failure=bad)))
            self.assertEqual(ctx.exception.code, 'INVALID_SCHEMA')
            self.assertEqual(self.service.inspect('RES-R')['head'], before)

    def test_r06_checkpoint_preserves_unknown_budget_and_pause_conditions(self):
        goal = self.save(research.set_goal('RES-R', self.goal(), metadata=self.metadata))
        question = self.save(self.operation('question', self.question('blocked')))
        done = self.save(self.operation('event', self.event(goal_ref=research.fixed_ref(goal))))
        budget = {'value': None, 'reason': 'not_acquired', 'note': '用户未提供剩余预算'}
        payload = {'goal_ref': research.fixed_ref(goal), 'route_refs': [], 'completed_refs': [research.fixed_ref(done)],
                   'question_refs': [research.fixed_ref(question)], 'next_step': '取得输入后先核验版本',
                   'prerequisites': ['需要测量文件'], 'stop_reason': '输入缺失暂停', 'budget_remaining': budget}
        saved = self.save(research.checkpoint('RES-R', payload, metadata=self.metadata))
        resolved = research.checkpoint_view(saved, resolve_ref=lambda ref: self.service._resolve_ref(ref, {}, []))
        self.assertEqual(resolved['payload']['budget_remaining'], budget)
        self.assertEqual(resolved['payload']['completed_refs'], payload['completed_refs'])
        self.assertEqual(resolved['payload']['stop_reason'], '输入缺失暂停')
        self.assertEqual(resolved['risks'], [])
        self.assertFalse(resolved['execution_started'])
        self.assertFalse(any(path.name in {'automation.toml', 'scheduled-tasks.json'} for path in self.root.rglob('*')))

    def test_r07_explicit_retention_and_false_do_not_force_extra_layers(self):
        saved_policy = self.save(self.operation('policy', {'mode': 'basic', 'overrides': {'retain': ['独立反例'], 'auto_deepen': False}}))
        repetitive = self.save(self.operation('event', self.event(), body_markdown='重复过程。' * 1000))
        failure = {'category': 'counterexample', 'tested_scope': '单个合成输入', 'result': '与预期不一致',
                   'cannot_infer': '不能推广其他输入', 'retry_conditions': []}
        retained = self.save(self.operation('event', self.event(failure=failure), body_markdown='短反例', record_reason='用户明确要求保留独立反例'))
        inspected = self.service.inspect('RES-R')
        self.assertFalse(inspected['policy']['values']['auto_deepen'])
        self.assertEqual(inspected['policy']['values']['retain'], ['独立反例'])
        self.assertEqual({row['kind'] for row in inspected['records'].values()}, {'event', 'policy'})
        self.assertEqual(len(inspected['records']), 3)
        self.assertEqual(retained['record_reason'], '用户明确要求保留独立反例')
        override = policy.resolve(inspected['owner'], {'retain': ['指定边界'], 'auto_deepen': False}, owner_policy=saved_policy['payload'])
        self.assertEqual(override['values']['retain'], ['指定边界'])
        self.assertEqual(override['sources']['retain'], 'request')

    def test_r08_partial_conversation_and_missing_earlier_context_remain_read_only(self):
        document = self.put('data/dialogue.txt', '实际导出第一行\n实际导出第二行\n')
        before = document.read_bytes()
        fingerprint = hashlib.sha256(before).hexdigest()
        self.put('retrieval/sources.json', {'sources': [{'source_id': 'SRC-DIALOGUE', 'path': 'data/dialogue.txt', 'enabled': True, 'sensitivity': 'internal'}]})
        ref = {'target_kind': 'file', 'target_id': 'SRC-DIALOGUE', 'revision': None, 'sha256': fingerprint,
               'locator': 'lines:1-2', 'relation': 'background'}
        payload = {'source_ref': ref, 'acquisition': 'verbatim_export', 'completeness': 'partial', 'acquired_at': None,
                   'missing_refs': [{'requested_target': '未取得的更早聊天', 'reason': '用户仅提供当前导出片段', 'observed_at': '2026-01-01T00:00:00Z'}]}
        metadata = {**self.metadata, 'body_markdown': before.decode('utf-8'), 'sources': [ref],
                    'provenance_gap': '更早聊天尚未取得'}
        saved = self.save(research.ingest_source('RES-R', payload, title='实际取得片段', metadata=metadata))
        self.assertEqual(saved['payload']['completeness'], 'partial')
        self.assertEqual(saved['payload']['source_ref']['locator'], 'lines:1-2')
        self.assertEqual(saved['payload']['missing_refs'], payload['missing_refs'])
        self.assertEqual(saved['body_markdown'], before.decode('utf-8'))
        with self.assertRaises(MemoryError) as ctx:
            research.ingest_source('RES-R', payload, title='非法覆盖', metadata=metadata, overwrite_original=True)
        self.assertEqual(ctx.exception.code, 'INVALID_ARGUMENT')
        missing = deepcopy(payload)
        missing['source_ref']['target_id'] = 'SRC-EARLIER-NOT-REGISTERED'
        with self.assertRaises(MemoryError) as ctx:
            self.save(research.ingest_source('RES-R', missing, title='未取得聊天', metadata=metadata))
        self.assertEqual(ctx.exception.code, 'UNRESOLVED_REFERENCE')
        self.assertEqual(document.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
