---
name: semantic-maintenance
description: 根据已变更材料的固定依据实际审查下游内容，形成保留、修订、重新综合、撤回或暂缓方案，并预检、提交和回读维护回执。
---

# 语义维护

使用工作台维护计划，或 `workbench.cmd material-query maintenance-plan --request 请求.json`。计划只定位候选与交付阅读材料，read_receipt仅证明内容已交付，不证明已理解。读取context_items和未检查区域，必要时按固定引用补齐正文后重新形成计划。

逐项比较新旧依据对适用域、结论、反证和下游表述的影响。给出retain/revise/resynthesize/retract/defer与具体理由；修改正文遵守现有memory-v3草案契约，未知或超范围项保持defer。原件只读，不直接改规范JSON或删除旧版本。

实际AI审查后填写reviewer_kind=ai、真实semantic_reviewer及review_note；只列本次读过且服务器交付的reviewed_refs。不把自己的审查标为human。将计划传入maintenance-review预检；基准HEAD或digest冲突时先重新读差异，不能强制覆盖。

在用户任务已有授权范围内用maintenance-apply提交；固定request_id使重试幂等。分别核对commits、pending_items、index_status与recovery_receipt，并回读保存版本。提交成功、复核有效、索引成功是不同状态。详见[材料查询手册](../../../docs/MATERIAL_QUERY.md)。
