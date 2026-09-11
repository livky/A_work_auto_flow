---
name: material-query
description: 按内容来源、标准类型和版本查询已有研发材料，选择候选后展开正文或读取完整文稿，核对来源、预算和缺口；不自动生成新结论。
---

# 材料查询

可用标准 Owner 类型（research/project/knowledge/run/core-algorithm/report/data/tool）单选或多选；scope.owner_types 与具体身份相交。名称/ID 用于缩小结构导航，层级、日期和复核状态是其他可组合维度。默认 freshness=current，只用当前修订；用户要查旧结果时用 allow_stale，历史扫描有界且保留版本/未覆盖缺口。默认活动读取时间预算为 300000 ms（5分钟），其他预算单独受限。

content_source=all 包含所有已登记内容类型、文稿/章节、表示和原始登记，仍遵守读取授权、范围和预算，不把任意磁盘文件当作登记材料。默认继续使用 overview_experience。

完整文稿使用 `documents`，传本查询 candidate_ids 和 expected_request_digest，可选 document_type=research_process/research_report；CLI 为 `search --request 请求.json --documents research_process`。同一文稿合并命中列表，只读已有编排；不存在或固定依据不满足时保留缺口。`expand` 可传 include_packet=true 同时返回正文、必要上下文及已启用的既有关联补充；不会生成未经审查的关联。工作台操作位于候选上方，右侧显示本次输出和失败回执。

先选择 content_source：默认 overview_experience（概览与经验，L4/L3），process（研究经过，L2 narrative），technical（技术内容，L1 detail）；新请求用 full/1、fallback=reject，读取已有正文。不要把旧 event/map 改名充当新内容，缺正文如实说明。省略 content_source 的旧表示 original/full/section/unit_digest/topic/domain 接口仍兼容。

使用工作台“材料查询”，或 `workbench.cmd material-query search --request 请求.json --assemble`。JSON字段以 [运行契约](../../schemas/material-query.schema.json) 为准；类型清单可用 `workbench.cmd material-query definitions`。`--assemble`明确组装本页全部候选；需要挑选、续查与加深时使用工作台同一query_id。CLI退出后查询身份到期，不能跨进程续接。

范围来源于用户任务，不预设全局直接召回。null表示不限，空数组表示无结果；范围上限与排除项始终保留。工作台默认允许读取命中所引用的获准必要依据，scope_ceiling 与直接筛选分开；可关闭跨对象依据读取，不能绕过显式排除、服务端 ACL 或来源授权。默认累计读取16 MiB、文本输出8万字符；图示按固定文件随包返回并计读取字节。正式用途填写具体applicability，逐claim核验；导航采纳不是科学支持。不要仅凭 accepted 标签推断材料当前有效。

先读候选/缺口，再选固定候选组包。需要深入时用同一查询的 expand，target 为 process 或 technical，保留 candidate_ids 与 expected_request_digest；只沿明确固定关联，可从 L3 直接到 L1，不猜同 Owner 联系。CLI 可加 --expand technical --assemble，但它会选择本页全部候选。向用户提供直接材料、必要上下文、联想补充及缺口；保留固定ref/修订/指纹。budget、partial、cancelled、STALE、EXPIRED均按实际报告，不重新搜索来伪装原查询续接。输出不足时保留公式/定义完整块，明确省略。

如缺少内容，判断是未读取、来源不可访问还是需要新研究；只有任务需要时调用 [research-loop](../research-loop/SKILL.md)。详见[材料查询手册](../../../docs/MATERIAL_QUERY.md)。
