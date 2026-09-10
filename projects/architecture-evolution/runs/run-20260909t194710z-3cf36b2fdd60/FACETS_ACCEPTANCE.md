# C03 知识分类继承修复与验证

本子项已按限定范围完成。角色、多个实际尝试结果、具体目标的置信评估保存在可选的规范 payload.knowledge_facets；复核状态和当前有效性继续由原证据服务计算。旧内容不补分类、不重算旧哈希，正文“成功”标签不作为尝试结果依据。

## 实际修改

- memory-v3 schema：event、experience、detail、map、document、document_section 增加可选分类；event/experience 的 v3 payload 单独定义，v1/v2 原定义保持不变；重新生成 memory-v3.d.ts。
- memory/facets.py 与 contracts.py：校验分类依据、固定 SHA、principle 子类型、时间区间及概率校准依据。分类中的引用仍沿原公开保存校验和读取权限闭包。
- material_query/facets.py 与 coordinator 筛选段：同维度 OR、跨维度 AND；多个 outcome 保留；未知显式纳入；空集永不变不限；置信与同一 claim 的复核/有效性交叉，不借用兄弟 claim。
- unknown_facets helper 与主集成候选输出：只标匹配所依赖的未知维度，不携带来源身份、标题、路径或数量。
- 使用说明位于 docs/KNOWLEDGE_FACETS.md，并从 MATERIAL_QUERY 链接。README 已检查，现有材料查询手册入口可到达，无需重复增加定义。

## 执行回执

最终命令：

```powershell
.\automation\python.ps1 -m unittest discover -s automation/tests -p test_material_facets.py -v
```

最终 8/8 通过，48.262 秒，退出码 0；日志：[facets-final-20260910.log](testing/facets-final-20260910.log)。初轮 8/8 通过、48.587 秒，后续增加 unknown 标注断言后才形成最终复验。

- `test_material_facets.MaterialFacetTests.test_applicability_uses_exact_structured_conditions_and_exclusions`
- `test_material_facets.MaterialFacetTests.test_confidence_targets_exact_claim_and_never_promotes_review`
- `test_material_facets.MaterialFacetTests.test_facet_basis_is_in_real_source_permission_and_revocation_closure`
- `test_material_facets.MaterialFacetTests.test_legacy_v1_v2_save_and_fixed_read_need_no_backfill_or_new_field`
- `test_material_facets.MaterialFacetTests.test_public_roundtrip_preserves_multiple_attempts_confidence_and_old_revision`
- `test_material_facets.MaterialFacetTests.test_public_validation_rejects_unfixed_unbased_uncalibrated_and_invalid_facets`
- `test_material_facets.MaterialFacetTests.test_role_multiple_outcomes_review_and_validity_intersect_independently`
- `test_material_facets.MaterialFacetTests.test_unknown_is_explicit_and_empty_filters_never_become_unrestricted`

相关 memory contracts 11/11 通过，0.048 秒；生成类型 --check 和限定 diff --check 通过。定向测试中的内容、修订和 review 均通过公开 memory API，未伪造 HEAD、复核状态或来源哈希。

## 影响处置与边界

需修改并已完成：MEM schema/校验/生成类型，RET 分类投影与组合筛选，GUIDE 当前使用说明，QA 定向真实测试。已检查无需修改：旧 CONTENT_FIELDS 和存储哈希算法、memory 索引数据库结构（仍从规范记录判断）、原来源权限入口、README 现有导航。没有新增依赖、模型、缓存或后台服务。

主任务统一处理：catalog 登记、总清单/影响图、quick/full、真实 setup 升级与恢复、发行清单和人工首页。本地 v1/v2 保存与固定回读测试通过不等于真实升级全部通过。

旧完整 Applicability 请求 DTO 的业务时间、目标版本条件尚未接入；本次只完整保存规范适用字段，并以现有条件/排除数组精确匹配标签，不将此边界改称全字段兼容。置信度保存不等于科学有效性认可。

机器回执与源码指纹：[facets-acceptance.json](facets-acceptance.json)。
