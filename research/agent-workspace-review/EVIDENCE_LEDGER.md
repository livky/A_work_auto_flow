# 证据台账

日期：2026-09-06。作者：本任务助手。以下“高”表示对所述代码行为或官方文档表述的把握，不表示技术结论已获业务确认。
本地基线：8b54b060dd8d0366baf049f4851a40a7edd522bf；输入哈希见 Run 清单（历史记录已从 main 移除，原路径：`../../runs/run-20260906t130218z-252152e16bc5/inputs.json`）。

## 本地事实

| ID | 声明与证据 | 定位 | 置信度与限制 |
|---|---|---|---|
| L01 | 全局对象平级、project 可选，当前评审开始前无业务算法/Run/研究 | [ARCHITECTURE](../../ARCHITECTURE.md)、[NOW](../../context/NOW.md)；开始时导航为空 | 高；本轮新增研究/Run 后数量变化 |
| L02 | 复核状态、历史追加和父 Run 失效传播已实现 | [workspace_cli.py](../../automation/scripts/workspace_cli.py)：review_run 第 446 行、annotate_run_impacts 第 398 行 | 高；依赖已登记，复核者身份未认证 |
| L03 | 空输入/产物/验证结果的 succeeded Run 通过 validate | probe-results.json（历史记录已从 main 移除，原路径：`../../runs/run-20260906t130218z-252152e16bc5/probe-results.json`）：incomplete_succeeded_run | 高；合成目录，不表示 succeeded 被当 accepted |
| L04 | 同目录材料继承 Run 风险，跨研究综合不继承 | [retrieval.py](../../automation/scripts/retrieval.py)：assemble 第 508 行，sibling 第 584 行；probe 的 retraction_scope | 高；直接复现带链接综合全文且无 blockers |
| L05 | 敏感分级不作为通用索引过滤字段 | [retrieval.py](../../automation/scripts/retrieval.py)：discover 第 149 行、metadata 第 210 行；probe 的 sensitivity_metadata | 高；合成标签，不审计宿主/系统权限 |
| L06 | source_id 基于绝对路径；历史正文不在 revisions 保存 | [retrieval.py](../../automation/scripts/retrieval.py)：source_id 第 145 行、connect 第 102 行、index 第 274 行 | 高；已有指纹验证和 stale 检查，不是没有版本意识 |
| L07 | Git/环境为尽力记录，未实现统一执行与封存 | [workspace_cli.py](../../automation/scripts/workspace_cli.py)：detect_git_revision 第 236 行、create_run 第 283 行；[MEMORY](../../context/MEMORY.md) | 高；任意外部脚本是否已自带实验追踪不在审阅范围 |
| L08 | 两次阶段扩展、用户选择和缺失项已实现 | [context_engine.py](../../automation/scripts/context_engine.py)：create 第 200 行、feedback 第 255 行 | 高；AI/用户判断解决，不自动证明答案正确 |
| L09 | 评估仅路径召回/MRR，真实 cases 为空 | [retrieval.py](../../automation/scripts/retrieval.py)：evaluate 第 717 行；[eval.json](../../retrieval/eval.json) | 高；单元测试与业务评估必须区分 |
| L10 | 抽取保留定位及警告，OCR 不理解复杂图形，XLSX 使用缓存 | [material_extract.py](../../automation/scripts/material_extract.py)：material 第 40 行 | 高；本副本真实模型/OCR 集成未执行 |
| L11 | 当前 49 项测试，42 通过、7 跳过；索引缺 qdrant_client | tests.txt（历史记录已从 main 移除，原路径：`../../runs/run-20260906t130218z-252152e16bc5/tests.txt`）、index-attempt.txt（历史记录已从 main 移除，原路径：`../../runs/run-20260906t130218z-252152e16bc5/index-attempt.txt`） | 高；当前副本结果，不能撤销别处历史通过记录 |
| L12 | 原校验 0 错误、4 警告：历史证据路径缺失 | validate-before.txt（历史记录已从 main 移除，原路径：`../../runs/run-20260906t130218z-252152e16bc5/validate-before.txt`） | 高；不把历史本机产物当作已看到 |
| L13 | 本地 Qdrant 单写使用；协议接口未成为插件加载器 | [qdrant_backend.py](../../automation/scripts/qdrant_backend.py)、[retrieval_interfaces.py](../../automation/scripts/retrieval_interfaces.py) | 高；未做压力测试 |
| L14 | 自动备份、跨对象报告更正、日志捕获多属约定 | [MEMORY](../../context/MEMORY.md)、[RETENTION](../../governance/RETENTION_POLICY.md)、[报告工作流历史原文](../../projects/architecture-evolution/runs/run-20260910t210558z-aba265055ed3/verification/retired-skills/report-production.txt) | 高；Git 已存在，MEMORY 中“未配置 Git”文字滞后于当前 NOW；2026-09-11 仅调整已退休工作流的原文存放链接，原判断不变 |
| L15 | 一次上下文创建多次扫描索引；同模块/研究关系组构造全连接 | [retrieval.py](../../automation/scripts/retrieval.py)：search/assemble/relations | 高代码事实；规模影响是推断，尚无测量，不能虚构延迟 |

## 外部一手资料

以下均于 2026-09-06 读取。除 Letta 页面自带发布日期外，不推定网页内容属于特定已安装 release；未保存整站，也未将搜索引擎摘要当全文证据。

| ID | 文档事实与比较用途 | 官方来源 | 限制 |
|---|---|---|---|
| W01 | OpenClaw 使用可检查文件记忆；可见存储与语义可靠性需区分 | [Memory](https://docs.openclaw.ai/concepts/memory) | 文档陈述，非实机审计 |
| W02 | 来源准入、防回灌、写入协调可借鉴 | [Memory architecture](https://docs.openclaw.ai/concepts/memory-architecture) | 不证明科学结论有效 |
| W03 | 直接编辑、旧副本和未追踪改写不完全覆盖 | [Memory provenance](https://docs.openclaw.ai/concepts/memory-provenance) | 阻止“已完全解决污染”的过度结论 |
| W04 | 可选 wiki 提供结构化结论、证据与健康展示 | [Memory Wiki](https://docs.openclaw.ai/plugins/memory-wiki) | 需启用；不等于默认全部开启 |
| W05 | 自动化具备时序调度、状态和重试 | [Automations](https://docs.openclaw.ai/automation/cron-jobs) | 科研任务仍需自己的验收语义 |
| W06 | 安全模型以一个互信边界为基础 | [Security](https://docs.openclaw.ai/gateway/security) | 非敌对多租户隔离保证 |
| W07 | Letta Code 记忆 Git 版本与渐进装载 | [Context Repositories，2026-02-12](https://www.letta.com/blog/context-repositories/) | 厂商能力介绍，非记忆准确率对照实验 |
| W08 | LangGraph 区分检查点和跨会话 store | [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | 持久化不自动绑定数据版本 |
| W09 | 恢复可能使用更新后的图代码 | [Backward compatibility](https://docs.langchain.com/oss/python/langgraph/backward-compatibility) | 接入时仍需固定执行版本 |
| W10 | 副作用和恢复需要幂等设计 | [Functional API](https://docs.langchain.com/oss/python/langgraph/functional-api) | 无通用 exactly-once 保证 |
| W11 | Deep Agents 提供执行、上下文、委派和介入能力 | [Overview](https://docs.langchain.com/oss/python/deepagents/overview) | 属运行框架，不替代研发证据层 |
| W12 | OpenHands 可持久化事件/状态，行动策略可配置 | [Persistence](https://docs.openhands.dev/sdk/guides/convo-persistence)、[Security](https://docs.openhands.dev/sdk/arch/security) | 非已完成部署验证 |
| W13 | DVC 将命令/依赖/参数/产物纳入流水线版本 | [dvc.yaml / dvc.lock](https://doc.dvc.org/user-guide/project-structure/dvcyaml-files) | 非模型现实有效性保证 |

## 检索路径、冲突和停止

先查官方记忆/执行文档，再针对 OpenClaw 的来源治理与 wiki、LangGraph 恢复语义、OpenHands 持久化和 DVC 版本结构补证。普通互联网比较研究，未启动 Deep research 服务。
OpenClaw 旧印象与当前文档存在差异，采用当日官方表述并保留覆盖限制；无依据声称用户曾使用的版本已有这些功能。
OpenHands 最初尝试的泛化 API 页面无法读取，改用公开的 persistence/security 官方页面；该失败页不作为证据。
本地没有真实公司算法与验收问答；真实向量/OCR 集成因缺依赖未执行。以上明确为缺口，不以更宽泛搜索补齐。
主要能力维度已获得可定位证据，停止继续增加项目数量。后续只有真实试点或拟选部署框架时才做版本固定的实机对比。

## 结论状态

SYNTHESIS 中的路线、优先级和启动评估数量为本任务工程建议。探针观测是合成条件下代码事实。没有人工业务确认，也没有将建议晋升到正式算法卡或 ADR。

