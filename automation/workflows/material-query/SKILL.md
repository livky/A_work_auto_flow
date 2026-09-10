---
name: material-query
description: 按表示类型与固定范围查询已有研发材料，选择候选后组装正文，核对来源、预算和缺口；适合跨材料查询或阅读，不自动生成新结论。
---

# 材料查询

先将用户问题转换为所需阅读形式：原件 original、全文 full、章节 section、单元摘要 unit_digest、主题 topic、领域 domain。类型是阅读规则；候选的 realization 才说明某份材料是否具备该内容。不要把 needs_generation 当作已存在的总结。

使用工作台“材料查询”，或 `workbench.cmd material-query search --request 请求.json --assemble`。JSON字段以 [运行契约](../../schemas/material-query.schema.json) 为准；类型清单可用 `workbench.cmd material-query definitions`。`--assemble`明确组装本页全部候选；需要挑选、续查与加深时使用工作台同一query_id。CLI退出后查询身份到期，不能跨进程续接。

范围来源于用户任务，不预设全局读取。null表示不限，空数组表示无结果；范围上限与排除项始终保留。正式用途填写具体applicability，逐claim核验；导航采纳不是科学支持。不要仅凭 accepted 标签推断材料当前有效。

先读候选/缺口，再选固定候选组包。向用户提供直接材料、必要上下文、联想补充及缺口；保留固定ref/修订/指纹。budget、partial、cancelled、STALE、EXPIRED均按实际报告，不重新搜索来伪装原查询续接。输出不足时保留公式/定义完整块，明确省略。

如缺少内容，判断是未读取、来源不可访问还是需要新研究；只有任务需要时调用 [research-loop](../research-loop/SKILL.md)。详见[材料查询手册](../../../docs/MATERIAL_QUERY.md)。
