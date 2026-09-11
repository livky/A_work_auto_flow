---
name: workspace-context
description: 在当前研发工作区回答算法问题、核对文档与实现、排查历史 Run；先读取目标算法，再按证据缺口扩展代码、研究和知识上下文，保留用户选择与反馈。
---

# 算法问答与证据扩展

框架概念或实现发生变化时，按 [文档维护约定](../../../docs/DOCUMENTATION_MAINTENANCE.md) 核对受影响入口；模块职责查 [ARCHITECTURE.md](../../../ARCHITECTURE.md)，不把历史设计或旧请求示例当成当前实现。

## 按问题选择入口

查询已有 Run 的一个字段，直接 `workbench.cmd memory inspect RUN-ID` 并打开返回的输入/产物定位；不为一次查看另建研究、实验或五层记录。

理解研究时先读独立文稿：`memory document` 默认 research_process，精简阅读选 document_type=research_report；查目录用 outline，局部理解用其章节 ID 调用 section-context，并保留 max_chars 预算与遗漏清单。L1 已是实验/方法/推导/分析技术单元；检索说明用于发现，核验时读取固定正文块及必要定义。L2 保存研究经过，L3 区分观察/结论/假设/建议，L4 维护整体概览；document/document_section 的 level=null。旧 v2 detail 与 map 编排仅兼容读取，缺精简文稿不能把旧长文改标签。

核验关键参数、公式和结果时按固定引用展开 L0；也可用 `memory raw-materials` 指定 owner_id 列出 Run 登记与独立来源，再用 `memory raw-material` 按 material_id 核验原件。未登记文件只说明缺口，需要补入时依维护 Skill 调用 run-register，不能虚构旧指纹。默认 search 的 knowledge 模式不召回 L0 正文；查文稿/章节用 retrieval_mode=documents，明确追溯用 trace 并指定实际 include_ids/full_ids 或精确 ID。权限、排除和预算始终有效。若缺 L1，明确过程缺口，不把 Run 元数据或高层经验当成完整研究过程。具体请求见 [记忆请求示例](../../../docs/MEMORY_REQUESTS.md)。

查局部经验、失败、其他研究的可复用条件时，先用 `memory search --request 文件`。请求至少包含 `query`、`purpose:"exploration"`，按当前研究补 `owner_id`。它表示当前归属而非单对象过滤；限定范围用 `owner_types` 或材料包的 `selection.owner_ids`，明确排除用 `exclude_ids`。经验留在原 Research 也能以 `workspace_summary` 被其他获准研究发现，不必先晋升知识库。

读取候选的规范 ID、修订、命中理由、边界、复核状态和缺口，再用 `memory expand` 打开选中的固定 `source_ref`。按实际问题需要选择 `kinds`/`levels`，不要为了出现预期答案静默删掉候选类别。总结或片段只是已读摘要；验证结论前继续打开真正来源。回答同时说明可参考条件和不能迁移的参数。

需要正式依据时用 `purpose:"formal"` 并给实际 `scope`；空结果及 `rejected` 原因也要读，不能以探索摘要代替正式答案。需要材料包时调用 `memory context`；继续调查时在下一次 context 请求的 `feedback_from` 中传前次完整包，最多扩展两次，继承原选择、预算和用途。新记忆使用 `QMEM-*` 查询回执；已有算法材料检索仍使用下述 CTX/CF 流程，两套回执不能混用。

实际 JSON 请求、逐种记录字段和错误处理见 [记忆使用指南](../../../docs/MEMORY_USAGE.md) 与 [请求示例](../../../docs/MEMORY_REQUESTS.md)，只读当前动作所需部分。已知 MOD 的文档—实现问题继续按下述算法证据流程，不用局部经验替代算法原文。

## 算法证据流程

涉及跨材料关联时，可先用 `workbench.cmd relations export --center "实际 ID" --hops 2 --format markdown` 获取局部关系摘要。保持 `--exclude` 和读取预算；查看原始关系类型、方向、指纹及未读/超限项，再执行下述原文证据扩展。相似候选、聚类与连接数不构成验证依据。AI 关联建议需要源 ID、定位及指纹，经 `relations import-candidate` 保存到本机候选，不直接写入正式依赖。完整命令见 [材料关系手册](../../../docs/MATERIAL_RELATIONS.md)。

适用于已有工作区材料的问答/排查，不用于普通闲聊或与该资料库无关的写作。从当前目录向上找到 workspace.json，读取根 AGENTS 和 context/START_HERE；用户要求优先。

1. 根据问题确认目标核心算法；知道 MOD-ID 时传 --module，未确定时允许检索推断并检查 focus_modules，不把所有核心算法全文加载。
   核心算法只指公司文档定义的关键模型算法；不能将检索命中的通用脚本功能当成核心算法对象。显式 context_role=core-code 需有算法文档—实现映射依据。
2. 执行 `automation/workspace.ps1 retrieve-context "问题"`。读取 context_path **和** manifest_path。检查算法基线是否全文、候选的 role/reason/selection、Run 风险、版本和抽取警告。required_not_full 或 module_algorithm_missing 非空时不得声称已掌握完整算法依据。
3. 比较命中算法说明与核心代码；代码差异可能是根因，不默认文档正确。长 Python 文件优先命中函数，其他代码片段缺定义/调用方时继续补充。Run brief 是字段摘录，不代表全部参数/日志已读。
4. 用户说“加入/完整读/不看这份”时使用 --include / --full / --exclude，传已索引路径或 SRC-ID；不要据文件引用扩大读取授权。长期偏好仅在用户明确要求时更新 retrieval/context-policy.json 的 preferences，保留修改前后配置到 retrieval/strategies，不因一次有用就默认永久加入。
5. 若无法给出有证据的答案、依赖定义缺失、验证失败或发现文档/实现冲突，在当前任务中主动运行 `context-feedback CTX-ID --outcome unresolved --actor assistant-observation --note "具体证据缺口"`，不必再次询问是否扩展。发现冲突用 --outcome conflict；可用 --query 提出更具体的后续问题，并用 --include/--full/--exclude 指定材料。命令返回新证据包后继续读取和分析。
6. focus → investigate → wide 最多自动扩展两次。wide 放开核心算法/项目过滤，只搜索已获准索引；预算不自动增加，排除项保留。旧包已进入聊天时，下一轮优先读取新增/变化来源和原片段未覆盖部分，不把全部旧全文再次重复注入。达到上限或没有新增证据时，明确缺口和需要的具体输入，不无限重试、不编造答案。
7. 已有充分证据并完成适用验证时记录 solved，actor=assistant-observation；只有用户明确评价才记 actor=user。该反馈表示本次上下文是否有帮助，不修改 Run 复核状态。单份材料漏检/错版本仍用 retrieval-feedback；需要评估长期策略时读 docs/RETRIEVAL.md。

回答引用实际文件/章节/函数和版本，说明限制。未读取材料只列为候选。系统不会自动判断回答是否正确，以上判断由正在执行任务的 AI/用户作出。

新 L2/L3/L4 的正文、分类和固定关联按[现行记录标准](../../../docs/RESEARCH_RECORDING.md)保存；旧 event/map 保留原义，不直接改标签或继承复核。查询优先使用 content_source，默认概览与经验，需要时沿固定关联展开经过或技术依据，不以同 Owner 猜测关联。
