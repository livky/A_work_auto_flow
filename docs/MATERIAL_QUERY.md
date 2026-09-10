# 材料查询、阅读与维护

材料查询把“找哪些材料”和“怎样呈现这些材料”分开。工作台导航的**材料查询**提供范围树、表示类型、用途、候选选择、组包及维护计划。规范内容仍保存在原有 memory-v3；一次查询不会改写原件、创建科学结论或替换历史版本。

## 主要概念

| 概念 | 含义与使用方式 |
|---|---|
| 表示类型 Definition | 一版阅读规则，如全文或摘要；不绑定具体材料。当前六类为 original、full、section、unit_digest、topic、domain |
| 表示实例 Realization | 固定材料按该类型可提供什么。direct可直接读，assemblable可组合已有字段，needs_generation缺少内容，stale表示过期，unsupported不支持 |
| 固定引用 FixedRef | 身份、修订与SHA256绑定材料；旧版不会随HEAD自动换新。文件以登记来源身份定位，不能传任意路径 |
| 查询 SearchReceipt | 保存范围、请求摘要、候选、缺口和到期时间；同一查询共享累计预算 |
| 材料包 MaterialPacket | 所选候选的直接材料、必要上下文、联想补充与缺口；canonical=false，不冒充规范记录 |
| 维护计划 MaintenancePlan | 把变化来源、受影响内容、阅读材料、建议动作及审查声明固定下来；通过预检后才可提交 |

L0–L4是规范知识层级，章节与完整/精简文稿使用独立类型，不强行分层。单元摘要来自已有检索说明或经验字段；主题与领域材料优先组合已有地图/文稿。需要新的统一解释时交给实际AI研究或审查，不能仅凭模板拼接标为已综合。

## 在工作台使用

1. 选择归属对象，或明确选择全局。默认空范围；高级筛选的null表示不限，[]表示没有匹配项。选定范围与范围上限相交，排除始终优先。
2. 填写问题，选阅读形式和用途。探索可提供未复核候选；正式用途须说明具体适用范围，并逐claim核验当前来源与复核状态。
3. 开始查询后可取消。先检查候选、表示可用性和缺口，再勾选组装。查询后改变条件会使旧选择失效，需重新查询。
4. 按需继续候选页，或从所选材料沿来源映射/已有关系加深。两者沿用原query_id、排除项、范围上限和累计预算。
5. 阅读包中固定来源与省略内容。预算不足时保留完整块，避免把公式、变量定义或适用条件截断后当完整内容引用。

已有关系联想只提供导航。相似、共同术语或accepted_navigation不能替代正式支持。当前确定性提供器开放identity与lexical；未注册的dense/sparse/graph通道会明确拒绝或返回partial缺口，短语/布尔不静默按普通关键词处理。旧记忆检索能力继续在原入口使用。

查询状态在当前服务进程内默认存活15分钟。服务重启或TTL到期返回EXPIRED；用户阅读时间不计执行墙钟。读取字节、输出文本、候选、图节点/边/跳数跨阶段累计。取消不能重置账本；新查询是新的操作，不能伪装成原查询无成本续接。

## 给AI与脚本的入口

常用提示：

- “用 material-query 按这些归属检索方法全文，先看缺口再组包。”
- “用 association-exploration 比较这两份固定材料的机制、差异和迁移条件。”
- “用 semantic-maintenance 实际阅读这个维护包，逐项判断并保存可复核草案。”

方法源在 `automation/workflows/<名称>/SKILL.md`，发现入口在 `.agents/skills/<名称>/SKILL.md`。安装器只补缺，遇到用户修改保留并提示差异。需要安装新入口时运行：

```powershell
.\automation\python.ps1 automation/scripts/install_workspace_skills.py --name material-query --name association-exploration --name semantic-maintenance --apply
.\workbench.cmd material-query --help
.\workbench.cmd material-query definitions
.\workbench.cmd material-query search --request .local/query.json --assemble
```

请求字段取自[运行JSON Schema](../automation/schemas/material-query.schema.json)与[Python契约](../automation/scripts/material_query/contracts.py)。CLI输出JSON；partial、拒绝、失败返回非零。`--assemble`显式选择本页全部候选，不隐式翻页；进程退出后该查询不能续接。交互式挑选/加深使用工作台HTTP会话。

HTTP沿用工作台随机前缀、localhost Host/Origin校验，动作使用POST JSON：`api/v1/materials/start`、`poll`、`resume`、`cancel`、`assemble`、`deepen`、`associations`、`association-decision`、`structure`及`maintenance-plan/review/apply/status`。只读类型列表为`api/v1/representations/definitions`，能力为`api/v1/materials/capabilities`。客户端不能注入授权Context或剩余预算。

底层适配使用 `POST api/v1/materials/foundation/<action>`，`foundation/capabilities` 返回逐方法映射及动作列表。读取、验证、提交和索引动作绑定实际query_id，在同一会话内执行。CLI可用 `material-query foundation-capabilities` 查看，或以 `material-query foundation --request request.json` 执行单次动作；文件为 `{ "query": <QueryRequest>, "action": "describe", "request": { "refs": [<FixedRef>] } }`，query_id由该进程建立并注入。跨步骤计划与提交使用持久HTTP会话。

旧定义名使用无材料读取的 `POST api/v1/materials/foundation/definition-resolve`：请求为 `{"source_contract_version":"0.1","key":"topic_synthesis","target_definition_version":"1"}`，返回带 `mapping_version` 的 `topic/1`；`domain_synthesis` 对应 `domain/1`，其余四个原名称保持。将返回的 `definition` 用于新查询，来源、回退和生成边界仍按原请求核验。此动作不需要query_id；未知名称/版本明确拒绝，不按相近字符串猜测。能力回执的 `model_providers=[]`、`tokenizers=[]` 明示当前没有已注册模型或分词计量策略，四个模型预算维度只是各自的硬上限。

图关系同时保留 `references`、`input`、`same_entity`、`mentions` 和新版关系。同一固定端点对之间的不同关系分别返回；`legacy_relation` 保留原关系字段，`evidence_relations` 与固定证据按序对应。图节点按固定身份去重，同名不会自动合并；未登记的规范关系作为缺口报告。导航关系与科学复核仍分别处理。

主范围决定候选和输出，scope_ceiling.owner_ids与服务端权限的交集决定依赖正文的读取硬上限。必要依赖在硬上限外时，父材料也会被省略并报告缺口；扩大主范围不会自动扩大硬上限，显式排除始终优先。来源文件另受登记授权约束，owner范围不替代文件授权。

每次读取的basis包含固定引用、owner HEAD、索引水位、observed_at与basis_id。它记录实际观察，跨owner不表示全局同时快照。issues把局部问题拆为code、message、affected_refs和retry；只有已授权读取的对象才附固定引用。retry区分原请求重试、重新计划、等待外部条件变化和不可重试，warnings仍保留供阅读。

## 语义维护的责任边界

计划先交付实际正文context_items及read_receipt，默认动作defer。read_receipt只证明交付，不证明理解。人工或AI需要真正阅读、比较影响，填真实身份、reviewer_kind、说明和已读引用，再提交maintenance-review。AI不得把自己的判断标为人工意见。

review固定依据、原文和摘要，检查草案；apply按owner使用原服务的CAS和幂等request_id写新修订。旧版保留，撤回通过既有复核记录表达。跨owner不承诺全局原子性；分别检查已提交项、待办、索引状态与恢复回执。HEAD冲突后重新读取差异，不覆盖后来修改。索引失败不改变已提交事实，也不能报告整个维护完成。

需要新的摘要解释或重新综合时，首期由实际AI/人工在计划项的 `draft_json` 中提出完整memory-v3草案，再走 `maintenance-review → maintenance-apply → 固定版本读回`。review只保存不可变审查计划，apply之后才有新的规范内容身份。这是已有内容的外部AI维护路径；底层表示builder只组合已存字段，其 `content_proposals=[]` 不代表自动生成了新解释。

## 开发与迁移

`automation/scripts/material_query/`维护运行契约、预算、读取、策略和应用编排；`memory/`继续负责规范schema、存储和事务。生成器`material_query/generate_types.py`输出JSON/TypeScript契约，`--check`检查漂移。前端在`automation/frontend/`，构建资源及指纹在`automation/ui/workbench-assets/`；使用端无需Node。

为保留旧分类与关系语义，memory-v3兼容增加可选knowledge_facets以及same_entity/mentions引用关系；旧记录无需补字段或改写历史字节。分类中的尝试结果、知识角色和所声明置信度分别保存，不能从复核状态推断。缺分类的旧材料仍为unknown，允许纳入时在候选上标出未知维度。

分类字段、六种支持的v3内容、固定评估目标、旧数据映射及条件筛选边界见[知识分类手册](KNOWLEDGE_FACETS.md)。当前条件数组只匹配明确标签，不代替旧完整Applicability请求的业务时间与目标版本条件。

本功能不变更Python依赖或384维模型。前端开发新增的Node类型声明只用于构建，不进入Python依赖包。升级仍从独立新版目录执行`setup.cmd --target "旧工作区路径" --register --open`，保留旧工作数据、自定义Skill和回滚记录；不能直接覆盖旧目录。

v0.1目标与43方法的继承关系见[继承映射](design/representation-query-v0.2/INHERITANCE.md)。实现验证、未注册策略、历史冻结fixture及尚待人工/第二台物理机验收的限制，在本轮固定Run和当前状态中分别记录；合成软件回归不证明真实业务模型有效。
