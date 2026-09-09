"""冻结跨研究配方在既有知识材料中保存，检查归属、旧版本与复核边界。

平铺知识文件由正式adopt入口分配OBJ身份；KNW-SYN-CROSS只是冻结配方
中的逻辑标签，测试显式保存二者映射，不手写owner.json或重造业务卡。
"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import uuid

from memory_fixture import materialize, snapshot
from memory import owners, packets, research, summaries
from memory.service import MemoryService


class FrozenSummaryTests(unittest.TestCase):
    def test_N05_N06_frozen_cross_summary_adopted_knowledge_and_new_interpretation(self):
        with tempfile.TemporaryDirectory(prefix='SYNTHETIC 跨研究总结 ') as temporary:
            fixture = materialize(Path(temporary)/'工作区', isolation_root=temporary)
            service = MemoryService(fixture.root)
            ids = {}
            for theme in ('THERMAL', 'PRESSURE'):
                selected = ['MEM-SRC-'+theme, 'MEM-EXP-'+theme]
                if theme == 'THERMAL':
                    selected.append('MEM-Q-OPEN')
                receipt = service.commit(fixture.request(selected))
                ids.update({row['client_key']: row['record_id'] for row in receipt['record_results']})
            native = fixture.owners['KNW-SYN-CROSS']['path']
            original = (fixture.root/native).read_bytes()
            view = next(row for row in owners.list_owners(fixture.root) if row['native_ref']['path'] == native)
            target = owners.adopt_owner(fixture.root, view['native_ref'], view['fingerprint'])['owner_id']
            self.assertTrue(target.startswith('OBJ-'))
            self.assertEqual((fixture.root/native).read_bytes(), original)
            donor_ids = ['RES-SYN-THERMAL', 'RES-SYN-PRESSURE']
            before = {oid: service.inspect(oid) for oid in donor_ids}
            protected = {name: digest for name, digest in snapshot(fixture.root)['files'].items()
                         if name.startswith(('synthetic-sources/', 'research/', 'runs/'))}
            prepared = summaries.prepare(service, '比较前置条件和禁止迁移边界', donor_ids,
                                         16000, {'stage': 'wide'})
            request = fixture.request(['MEM-EXP-CROSS', 'MEM-MAP-CROSS'], reference_ids=ids)
            request['owner_id'] = target
            for operation in request['operations']:
                operation['draft']['owner_id'] = target
            request['basis_heads'] = prepared['basis_heads']
            saved = summaries.save(service, request)
            rows = service.inspect(target)['records']
            # Frozen recipes intentionally retain v1 stored layers. They are
            # not new unversioned drafts and must not be silently upgraded.
            self.assertEqual({row['schema_version'] for row in rows.values()}, {1})
            self.assertEqual({row['level'] for row in rows.values()}, {'L2', 'L3'})
            self.assertEqual({row['owner_id'] for row in rows.values()}, {target})
            self.assertEqual(len(rows), 2)
            exp = next(row for row in rows.values() if row['kind'] == 'experience')
            theme_map = next(row for row in rows.values() if row['kind'] == 'map')
            expected = {ids['MEM-EXP-THERMAL'], ids['MEM-EXP-PRESSURE']}
            self.assertEqual({ref['target_id'] for ref in exp['sources']}, expected)
            self.assertTrue(expected <= {ref['target_id'] for ref in theme_map['payload']['result_refs']})
            self.assertEqual((fixture.root/native).read_bytes(), original)
            for oid in donor_ids:
                self.assertEqual(service.inspect(oid), before[oid])

            # 来源不变，仅解释边界有变化，允许同一记录产生新修订。
            # 新断言保持未复核；保存动作不为它创建接受记录。
            changed = research._draft(exp)
            self.assertEqual(changed['schema_version'], 1)
            self.assertEqual(changed['level'], 'L2')
            changed['body_markdown'] += '\n参数单位与操作含义不同，不能由标题相似推导换算关系。'
            changed['payload']['prohibited'].append('不同操作量纲不可由名称相似推导换算')
            changed['payload']['claims'] = [{'claim_id': 'CLM-SYN-CROSS-INTERPRETATION',
                'statement': '已有两份合成来源未提供时间与次数的换算依据', 'kind': 'inference',
                'scope': 'synthetic:cross', 'evidence_refs': deepcopy(exp['sources'])}]
            changed['change_reason'] = '同一来源版本下明确参数含义与换算证据限制'
            updated = summaries.save(service, {'schema_version': 1, 'request_id': str(uuid.uuid4()),
                'actor': {'kind': 'ai', 'id': 'synthetic-summary-test'}, 'owner_id': target,
                'expected_head': saved['commit_id'], 'record_id': exp['record_id'],
                'expected_revision': 1, 'draft': changed, 'basis_heads': prepared['basis_heads']})
            current = service.inspect(target, record_id=exp['record_id'])['record']
            old = service.inspect(target, 1, record_id=exp['record_id'])['record']
            self.assertEqual(old, exp)
            self.assertEqual(current['revision'], 2)
            self.assertEqual((current['schema_version'], current['level']), (1, 'L2'))
            self.assertEqual(current['sources'], old['sources'])
            self.assertNotEqual(updated['commit_id'], saved['commit_id'])
            self.assertIn('不同操作量纲', current['payload']['prohibited'][-1])
            state = packets.Snapshot(service).adapter.claim_state('CLM-SYN-CROSS-INTERPRETATION')
            self.assertEqual(state['review_state'], 'not-reviewed')
            after = snapshot(fixture.root)['files']
            self.assertEqual({name: after[name] for name in protected}, protected)
            # 全部规范副本只能存在于此知识对象；两端研究不能产生第二份总结。
            occurrences = [(owner['owner_id'], record['record_id'])
                           for owner in owners.list_owners(fixture.root)
                           for record in service.inspect(owner['owner_id'])['records'].values()
                           if record['record_id'] in {exp['record_id'], theme_map['record_id']}]
            self.assertEqual(set(occurrences), {(target, exp['record_id']), (target, theme_map['record_id'])})
            self.assertEqual(len(occurrences), 2)


if __name__ == '__main__':
    unittest.main()
