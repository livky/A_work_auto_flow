# 数据结构与存储契约 v1

本文件规定首版实现目标。表中“必需”指提交时必须提供或由服务端生成；空值必须有约定含义。实际 JSON Schema 在 W01 实现。本文件中的新目录和类型尚未实现。

契约真源为计划中的 automation/schemas/memory-v1.schema.json。为保持基础记录功能在 core 环境可用，后端采用标准库实现并测试本项目限定的 schema 子集：type、const、enum、required、properties、additionalProperties、items、minLength、minItems、oneOf、$defs 和本地 $ref。遇到未支持关键字或外部 $ref 明确拒绝，不能静默忽略。跨字段、引用解析和状态转换由具名领域校验函数完成。前端从同一 schema 生成结构类型，领域约束调用后端预检，不复制第二套状态机。该校验器不宣称实现完整通用 JSON Schema 标准，不新增运行依赖。

## 1. 保留现有业务对象，新增统一入口

复用 [workspace_cli.py](../../../automation/scripts/workspace_cli.py) 的 ID、[evidence.py](../../../automation/scripts/evidence.py) 的结论及复核语义、[projection.py](../../../automation/scripts/workbench_app/projection.py) 的八类映射。

`OwnerDescriptor` 是记忆归属入口，不替代原业务 manifest：

| 字段 | 类型/必需性 | 定义与修改规则 |
|---|---|---|
| schema_version | integer，服务端固定 1 | 未知版本拒绝写入 |
| owner_id | string，必需 | 优先沿用 RUN/RES/PRJ/MOD/DATA/TOOL/REP/EVD 等已有身份，创建后不可改 |
| owner_type | enum，必需 | research、run、project、core-algorithm、knowledge、report、data、tool；扩展类型必须先登记契约与适配器 |
| native_ref | object，必需 | 原 manifest/文档相对路径及原身份字段；仅定位，不复制其全部字段 |
| memory_home | relative path，服务端生成 | 服务端根据适配器决定，拒绝调用者指定任意路径 |
| created_at / created_by | UTC 时间/Actor，服务端/调用者 | 入口创建信息；后续改显示标题不更换身份 |
| adapter_version | integer，服务端 | 解析语义版本；与业务 schema_version 分开 |

标题、业务生命周期从原对象读取；记录策略由独立 policy 记录承载，不在旧 manifest 中不断追加记忆进度。

目录适配规则：
- 有专属目录的 Run、Research、Project、核心算法：所属目录的 `memory/`。
- 平铺知识文档、报告清单、数据卡：原文件旁 `<完整文件名>.memory/`。
- tools/registry.json 中的条目：`tools/memory/<tool_id>/`，不在第三方工具原件里写入。
- 缺少稳定身份的旧知识文档：只读浏览可用临时定位；首次 `adopt-owner` 建旁目录，分配 `OBJ-<UUID>`，保存旧导航 ID 为别名。不得仅用路径散列冒充移动后稳定 ID。
- 同一 native_ref 不得由两个入口认领。名称大小写、Windows 保留名、联接/符号链接及目录越界在解析入口时检查。
- 第一次采用新增入口不改写原文件。移动必须通过迁移入口更新定位映射；手工移动导致的缺失要明确报告。

## 2. 每条记录的共同外壳

规范正文选择 **一条修订一个 UTF-8 JSON，正文使用 body_markdown 字符串**。不同时维护配套 Markdown 主正文。人类阅读 Markdown/HTML 由 render/export 生成；AI 写出的地图正文仍在规范 JSON 中，不属于缓存。

| 字段 | 类型/来源 | 规则 |
|---|---|---|
| schema_version | integer=1，服务端 | 未知版本拒绝 |
| record_id | string，服务端分配 MEM-UUID | 同对象及全工作区唯一；合成测试可注入固定 ID |
| owner_id | string，必需 | 仅一个规范归属；不可用修订偷偷改归属 |
| kind | enum，必需 | 见下一节；禁止未知 kind |
| level | L0/L1/L2/L3/null，服务端按 kind 确定 | 辅助实体为 null；调用者传值不匹配则报错 |
| title | 非空 string，必需 | 标题不是身份；不限制中文 |
| keywords | string[]，可选，默认[] | 可检索关键词与别名；去重，不作为独立证据 |
| body_markdown | string，必需 | 叙述、摘要或地图正文；允许结构充分的辅助记录为空 |
| payload | object，必需 | kind 对应的专用结构；禁止未声明属性 |
| sources | SourceRef[]，必需 | 可为空，但空时 provenance_gap 必须说明依据为何缺失 |
| provenance_gap | string/null | null 表示无声明缺口；非空表示已知缺口，不伪造来源 |
| record_reason | 非空 string，必需 | 为什么值得保存 |
| discovery | owner_only/workspace_summary，必需 | 发现范围，不授予访问权限；默认继承 policy |
| sensitivity | public/internal/confidential/restricted，必需 | 与既有分类对齐；AI 不能借摘要降低来源限制 |
| created_at / created_by | UTC/Actor | 首次生成，后续修订不变 |
| revision / previous_revision | positive integer / integer或null，服务端 | 从 1 开始；新修订递增，首版 previous=null |
| updated_at / updated_by | UTC/Actor，服务端/调用者 | 本修订的变更时间与执行者 |
| change_reason | 非空 string | 首版可等于 record_reason；后续解释变更 |
| record_hash | SHA-256，服务端 | 对去掉 record_hash 的规范 JSON 序列化计算，用于完整性 |
| content_hash | SHA-256，服务端 | 对 owner_id、kind、level、title、keywords、body_markdown、payload、sources、provenance_gap、discovery、sensitivity 计算；不含作者时间、修订、变更理由 |

`Actor={kind:human|ai|workflow, id:非空字符串}`。此字段记录声明身份，不证明认证或证据真实性。UTC 格式为 RFC3339 的 Z 后缀；另有 occurred_at 时表示事件发生时间，未知用 null，不能拿保存时间伪装发生时间。

哈希序列化固定为 UTF-8、键排序、无多余空格、禁止 NaN/Infinity；数组顺序保留，正文不做隐式改写。同一 content_hash 的重复 put 为 no_change，不新建修订；要求记录一次独立操作时创建 event。

## 3. 专用结构、内容层与辅助实体

下表字段为 payload 必需项，空数组表示“当前没有已知项”；未知事实使用 `UnknownValue={value:null,reason:unknown|not_acquired|not_applicable,note:string}`，不得用空字符串混淆。

| kind / level | payload 字段与类型 | 关键约束 |
|---|---|---|
| source / L0 | source_ref:SourceRef, acquisition:original_link|verbatim_export|excerpt, completeness:complete|partial|unknown, acquired_at:UTC或null | 原件不复制；原文摘录必须有定位；新归纳不能标成 verbatim_export |
| event / L1 | occurred_at:UTC或null, question_refs:Ref[], goal_ref:Ref或null, route_ref:Ref或null, action:string, observation:string或UnknownValue, decision:string或null, decision_refs:Ref[], run_refs:Ref[], failure:Failure或null, claims:Claim[] | decision 非空须有依据或明确缺口；已有 Run 直接适配为事件，不再复制等价 event |
| experience / L2 | problem_structure:string, recommendation:string, applicable:非空string[], prohibited:string[], failure_modes:string[], retry_conditions:string[], claim_refs:Ref[], claims:Claim[] | 主张如需正式使用必须有 CLM；不能只保存建议而不保存边界 |
| map / L3 | topic:string, goal_refs:Ref[], route_refs:Ref[], result_refs:Ref[], question_refs:Ref[], conflict_refs:Ref[], next_steps:string[], coverage:object | coverage 含 owner_ids、source_versions、missing；地图是导航/综合，不独立获得重复复核 |
| question / null | question:string, status:枚举, decision_affected:string, missing_evidence:string[], resolution_refs:Ref[], replacement_ref:Ref或null, reopen_reason:string或null | resolved 必须有有效答案/决策引用；superseded 必须指向不同问题 |
| goal / null | objective:string, constraints:string[], success_criteria:string[], previous_goal_ref:Ref或null, change_impact:string | 更换目标新建目标修订，旧尝试继续引用旧版本 |
| route / null | goal_ref:Ref, hypothesis:string, status:planned|active|blocked|closed|superseded, attempt_refs:Ref[], blocker:string或null, next_step:string, reopen_condition:string, replacement_ref:Ref或null | blocked 须 blocker；更换路线不删除旧尝试 |
| checkpoint / null | goal_ref:Ref, route_refs:Ref[], completed_refs:Ref[], question_refs:Ref[], next_step:string, prerequisites:string[], stop_reason:string, budget_remaining:object或UnknownValue | 保存当时快照；恢复必须重验引用，不凭检查点自动重复实验 |
| association / null | from:Ref, to:Ref, relation:枚举, explanation:string, shared_structure:string或null, transfer_limits:string[], basis_refs:Ref[], status:candidate|accepted|rejected|withdrawn | 类比必须填共同结构与不可迁移部分；禁止自动创建科学支持 |
| representation / null | target:Ref, slot:title|result|problem|trigger|failure|boundary, text:string, boundary_refs:Ref[] | 每个 target ID+slot 一个当前规范表示；修订绑定源版本；不复制 CLM |
| policy / null | mode:basic|accumulate|explore, overrides:object | overrides 允许 retain、granularity、auto_summary、discovery、auto_deepen、checkpoint；缺省继承，明确 false 不得被默认覆盖 |
| consolidation / null | basis_heads:map, trigger:string, affected_refs:Ref[], decisions:ConsolidationDecision[], remaining_refs:Ref[] | decision 的 action 为 revise|retain|defer，并有理由；defer 留在 remaining |
| feedback / null | query_id:string, target:Ref, label:枚举, note:string, adopted_in:Ref或null | label 为 missing、irrelevant、invalid_analogy、lost_boundary、stale、adopted、outcome；adopted 不更改复核 |
| review / null | target_claim_id:string, target_content_hash:string, state:ReviewState, reviewer:Actor, reason:string, evidence_refs:Ref[], scope:string或null, replacement_claim_id:string或null | 专用 review 服务创建；普通 commit 禁止通过 payload 自行写 accepted |

`Failure={category:execution|no_improvement|counterexample|insufficient_evidence, tested_scope:string, result:string, cannot_infer:string, retry_conditions:string[]}`。

verbatim_export 必须给出可取得文本的精确行段/字符区间，并将正文与所选原文逐字比较；不一致报 INVALID_SCHEMA。无法直接比较的二进制原件使用 original_link；OCR/AI 提取结果注明取得方式和缺口，不通过文字自我声明获得原始证据身份。每种 payload 都允许 missing_refs:UnresolvedRef[]，默认[]，除此之外禁止未声明扩展键。

`Claim={claim_id:CLM-稳定ID, statement:string, kind:fact|calculation|inference|recommendation, scope:string, evidence_refs:SourceRef[]}`。仅 event/experience 可内含新 claim；map/representation 通过 claim_refs 或来源引用已有 claim。旧 Run/Research/知识旁文件里的 CLM 原位保留，新适配器不能再创建第二个 CLM 身份。

## 4. 引用与状态

`Ref={target_kind:owner|record|claim|file, target_id:string, revision:integer或null, sha256:string或null, locator:string, relation:string}`。
- record 必须固定 revision，可选 sha256 指向该修订的 record_hash（不是用于去重与复核的 content_hash）；claim/旧 owner/文件必须提供内容指纹；引用旧目标版本不自动升级到当前版本。
- file 的 target_id 必须是获准来源登记 ID；通过 registry 解析，不接受正文任意路径授权。
- relation 的证据语义仅 supports、input、contradicts、background；导航可用 derived_from、refines、same_problem、same_failure_mode、prerequisite、analogous_to、used_in、references。
- 新输入包内引用尚未创建的记录，使用 `client_key`；预检解析整批，再分配正式 ID，回执返回映射。正式修订中不得残留临时键。
- 真正缺失目标的新引用默认拒绝；用户明确允许保留缺口时以 `UnresolvedRef={requested_target,reason,observed_at}` 放入 payload 的 missing_refs 扩展槽，只用于探索，不作为有效 supports/input。既有引用后来不可访问则保留原引用、报告缺口。

问题状态允许：open→investigating/blocked/resolved/superseded；investigating→open/blocked/resolved/superseded；blocked→open/investigating/resolved/superseded；resolved/superseded→open/investigating 需 reopen_reason。所有变更写新修订；resolved 必须有答案/决策的非缺失固定引用，后来失效时派生 resolution_needs_revalidation，不悄悄覆写历史 resolved。

复核沿用 not-reviewed/accepted/disputed/retracted/superseded。accepted 必须匹配结论内容、范围和依据；superseded 指向存在的不同 claim。复核历史独立于正文修订；撤回不改 Run succeeded。新 memory claim 的依据范围绑定所属 event/experience 的 content_hash，不绑定整个 Research 的动态记忆。

## 5. 规范存储与事务边界

建议布局（示意路径由适配器生成）：

```text
research/<slug>/memory/
  owner.json
  HEAD.json
  request-receipts/<request-id>.json  # no_change等无内容修订回执；独占/原子写入
  commits/<commit-id>/
    manifest.json
    records/<record-id>.json
    receipt.json
  staging/<request-id>/       # 未提交中间件；恢复后可归档，读者不当作记录
```

每个不可变 manifest 包含 schema_version、commit_id、parent_commit_id、generation、owner_id、完整的 record_heads 映射、当前 policy/goal/checkpoint 指针、request_ledger 映射、changed_ids、来源核验快照和索引待办。record_heads 指向具体 commit 下的记录文件、revision、record_hash；未修改项仍引用先前 commit。首版不压缩旧 manifest，性能用例明确检测对象记录增长的成本。

HEAD 只包含当前 commit_id、generation、manifest_hash。读者只从 HEAD 进入完整快照，不直接扫描 staging 或把孤立 commit 当成已提交。新 revision 写新文件，旧文件不改。

单次事务限一个 owner，可包含多条记录及关系。关系规范归属由创建者显式选择，必须是已登记对象；两端固定引用，反向关系由索引派生。跨对象更新不承诺全局事务，返回按对象回执；不以“整体失败”掩盖已经提交的对象。

索引失败不回滚已提交内容；每个 commit 的索引待办持久保存，索引保存处理水位，可通过 rebuild/reconcile 补偿。AI 日常提交不要求用户逐次批准；dry-run 校验不产生业务目录、请求回执或索引。

## 6. 派生数据库与历史边界

继续使用 retrieval/generated 下的 SQLite；新增表与现有 docs/chunks/terms 分开版本迁移：

| 表 | 主键与主要字段 | 用途 |
|---|---|---|
| memory_owners | owner_id PK；type、native_ref、head、generation | 对象定位缓存 |
| memory_records | record_id PK；owner_id、kind、level、revision、content_hash、title、body、discovery | 当前记录目录 |
| memory_representations | (target_id,slot) PK；representation_id、source_revision、text | 多表示去重与回源 |
| memory_edges | association_id PK；from_id、to_id、relation、status、source_versions | 邻接与反向引用 |
| memory_fts | FTS5；record/representation key、title、text | 关键词召回 |
| memory_index_state | owner_id PK；indexed_generation、encoder_version、error | 索引水位及补偿 |

检索默认当前修订；历史修订只能显式按 ID+revision 展开或使用 history 模式。历史不全量灌入当前向量排名。来源撤回、权限收窄、删除登记必须在正式导出时回源再检，不能依赖旧数据库状态。

新向量集合按模型指纹、编码器版本及记忆 schema 隔离，仍使用既有 384 维模型契约。内容或表示变化增量更新；元数据限制变化也触发清除旧可见条目。缺模型时返回可用的关键词结果与降级说明，禁止静默联网安装。

## 7. 兼容与规范写入约束

原对象、旧复核语义和绝对来源登记先通过适配读取，安装不自动补写全部历史。手工改 JSON 导致 hash 不一致要拒读正式内容并报告损坏，不自动“修好指纹”。转换旧 Markdown 的 AI 提取是显式导入，不伪造发生时间或复核过程。

所有字段验证、ID 解析、状态转换和引用检查使用同一服务契约；CLI、HTTP、Skill 不复制实现。扩展 kind 或 owner_type 必须同步 schema、适配器、测试材料和升级清单。
