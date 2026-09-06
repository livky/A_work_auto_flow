---
name: workspace-context
description: 在当前研发工作区回答算法问题、核对文档与实现、排查历史 Run；先读取目标算法，再按证据缺口扩展代码、研究和知识上下文，保留用户选择与反馈。
---

# 算法问答与证据扩展

适用于已有工作区材料的问答/排查，不用于普通闲聊或与该资料库无关的写作。从当前目录向上找到 workspace.json，读取根 AGENTS 和 context/START_HERE；用户要求优先。

1. 根据问题确认目标核心算法；知道 MOD-ID 时传 --module，未确定时允许检索推断并检查 focus_modules，不把所有核心算法全文加载。
   核心算法只指公司文档定义的关键模型算法/测校项；不能将检索命中的通用脚本功能当成核心算法对象。显式 context_role=core-code 需有算法文档—实现映射依据。
2. 执行 `automation/workspace.ps1 retrieve-context "问题"`。读取 context_path **和** manifest_path。检查算法基线是否全文、候选的 role/reason/selection、Run 风险、版本和抽取警告。required_not_full 或 module_algorithm_missing 非空时不得声称已掌握完整算法依据。
3. 比较命中算法说明与核心代码；代码差异可能是根因，不默认文档正确。长 Python 文件优先命中函数，其他代码片段缺定义/调用方时继续补充。Run brief 是字段摘录，不代表全部参数/日志已读。
4. 用户说“加入/完整读/不看这份”时使用 --include / --full / --exclude，传已索引路径或 SRC-ID；不要据文件引用扩大读取授权。长期偏好仅在用户明确要求时更新 retrieval/context-policy.json 的 preferences，保留修改前后配置到 retrieval/strategies，不因一次有用就默认永久加入。
5. 若无法给出有证据的答案、依赖定义缺失、验证失败或发现文档/实现冲突，在当前任务中主动运行 `context-feedback CTX-ID --outcome unresolved --actor assistant-observation --note "具体证据缺口"`，不必再次询问是否扩展。发现冲突用 --outcome conflict；可用 --query 提出更具体的后续问题，并用 --include/--full/--exclude 指定材料。命令返回新证据包后继续读取和分析。
6. focus → investigate → wide 最多自动扩展两次。wide 放开核心算法/项目过滤，只搜索已获准索引；预算不自动增加，排除项保留。旧包已进入聊天时，下一轮优先读取新增/变化来源和原片段未覆盖部分，不把全部旧全文再次重复注入。达到上限或没有新增证据时，明确缺口和需要的具体输入，不无限重试、不编造答案。
7. 已有充分证据并完成适用验证时记录 solved，actor=assistant-observation；只有用户明确评价才记 actor=user。该反馈表示本次上下文是否有帮助，不修改 Run 复核状态。单份材料漏检/错版本仍用 retrieval-feedback；需要评估长期策略时读 docs/RETRIEVAL.md。

回答引用实际文件/章节/函数和版本，说明限制。未读取材料只列为候选。系统不会自动判断回答是否正确，以上判断由正在执行任务的 AI/用户作出。
