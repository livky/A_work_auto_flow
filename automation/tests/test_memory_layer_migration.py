"""层级迁移使用真实事务：当前身份唯一，旧依据仍按原字节可读。"""
from copy import deepcopy
import unittest
import test_memory_store as store_tests
from test_memory_store import request, snapshot_files
from test_memory_contracts import draft
from memory import owners


class LayerMigrationTests(unittest.TestCase):
    # 复用隔离工作区搭建，不重复继承原有测试方法。
    setUp = store_tests.MemoryStoreTests.setUp
    tearDown = store_tests.MemoryStoreTests.tearDown
    assert_code = store_tests.MemoryStoreTests.assert_code
    def test_explicit_migration_preserves_history_and_rejects_incomplete_drafts(self):
        for before, after in (("event", "narrative"), ("map", "overview")):
            value = draft(before)
            value["owner_id"] = "RES-TEST"
            head = self.service.inspect("RES-TEST")["head"]
            receipt = self.service.commit(request(value, head=head["commit_id"] if head else None))
            rid = receipt["record_results"][0]["record_id"]
            old = self.service.inspect("RES-TEST", record_id=rid)["record"]
            home = self.root / owners.resolve_owner(self.root, "RES-TEST")["memory_home"]
            hashes = snapshot_files(home / "commits")
            revised = deepcopy(value)
            revised.update(kind=after, schema_version=4, change_reason="实际整理旧内容到统一层级",
                           sources=[dict(target_kind="record", target_id=rid, revision=old["revision"],
                                         sha256=old["record_hash"], locator="", relation="references")])
            common = dict(question="合成问题", claims=[], process_refs=[], technical_refs=[],
                          experience_refs=[], limitations=["无科学结论"])
            revised["payload"] = dict(common, **(
                dict(stages=[dict(situation="原阶段", action="读取", reason="整理", outcome="保存", evidence_refs=[])])
                if after == "narrative" else
                dict(methods=["读取"], results=["合成"], current_stage="整理", open_questions=[])))
            if after == "narrative":
                revised["payload"].update(occurred_at="2026-09-01T01:00:00Z", failure=dict(
                    category="execution", result="合成失败", tested_scope="合成环境",
                    cannot_infer="不代表数值方法失败", retry_conditions=["修复合成环境"]))
            for field, bad_value in (("sources", []), ("body_markdown", ""), ("change_reason", ""), ("kind", "experience")):
                invalid = deepcopy(revised)
                invalid[field] = bad_value
                self.assert_code("INVALID_SCHEMA", lambda: self.service.commit(request(
                    invalid, head=receipt["commit_id"], rid=rid, revision=old["revision"])))
            committed = self.service.commit(request(revised, head=receipt["commit_id"], rid=rid, revision=old["revision"]))
            current = self.service.inspect("RES-TEST", record_id=rid)["record"]
            self.assertEqual((current["kind"], current["revision"]), (after, old["revision"] + 1))
            if after == "narrative":
                from memory.history import _row
                from material_query.facets import authored
                self.assertEqual(_row(current)["occurred_at"], "2026-09-01T01:00:00Z")
                self.assertEqual(_row(current)["role"], "failure")
                self.assertEqual(authored(current)["outcomes"], ("failure",))
            self.assertEqual(old, self.service.inspect("RES-TEST", old["revision"], record_id=rid)["record"])
            for path, digest in hashes.items():
                self.assertEqual(digest, snapshot_files(home / "commits")[path])
            self.assert_code("VERSION_CONFLICT", lambda: self.service.commit(request(
                revised, head=committed["commit_id"], rid=rid, revision=old["revision"])))
