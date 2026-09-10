# 多表示与分阶段检索的接口启示

本页记录公开一手材料支持的机制及工程建议；它不表示现有工作区已经具备相应后端能力。资料读取日期为 2026-09-09；滚动官方文档没有稳定发布日期的，明确使用访问日期。

## 证据与对应能力

| 来源 | 直接支持的事实 | 对本设计的建议与边界 |
|---|---|---|
| [SQLite FTS5](https://www.sqlite.org/fts5.html#fts5_column_filters)，SQLite 官方，动态文档 | 支持按列限定 MATCH、短语、前缀及布尔条件；匹配字段可以独立于返回字段 | 单独定义检索字段和可查询语法；全文词法检索不等于全文逐文件扫描。分词/编码要带版本，不能承诺任意中文术语开箱即有最佳召回 |
| [Qdrant Hybrid and Multi-Stage Queries](https://qdrant.tech/documentation/search/hybrid-queries/)，Qdrant 官方，Query API 相关能力自 v1.10 起分批提供 | prefetch 支持分阶段候选；融合与后续重排是独立组合；同页还示范稠密粗筛与多向量精排 | 接口预留 channel、stage、candidate_limit、ranker_id、model/representation_version。多阶段属于可替换计划，不把 Qdrant 请求对象暴露到领域接口；当前安装版本支持哪些算子需另验 |
| [Multi-Representation Search Across Titles, Abstracts, and Chunks](https://qdrant.tech/documentation/tutorials-search-engineering/multi-representation-search/)，Qdrant 官方教程，动态文档 | 标题、摘要和片段可分别召回，再按文档身份融合分组；教程示例用摘要切片，不能当完整论文实测 | 同一内容允许多种搜索表示，并返回统一内容身份和实际命中的表示身份。避免把一个来源的多个摘要/片段当作多份独立证据 |
| [Phased Ranking](https://docs.vespa.ai/en/ranking/phased-ranking.html)，Vespa 官方，动态文档 | 便宜的候选阶段与较贵重排阶段分开，可对重排数量设上界 | 召回量、重排量、结果量分别限制；信息更少不自动保证端到端更快。预算记录实际耗时和工作量，不仅记录最后 Top-K |
| [An Analysis of Fusion Functions for Hybrid Retrieval](https://arxiv.org/abs/2210.11934v2)，Bruch、Gai、Ingber，2023-05-04 修订 | 在论文实验中，RRF 对参数敏感，调优的凸组合有优于 RRF 的结果 | 融合接口必须可替换并保留各路排名/分数及参数；RRF 可作初始基线，不能被认作普遍最优 |
| [Adaptive-RAG](https://aclanthology.org/2024.naacl-long.389/)，Jeong 等，NAACL 2024 | 按问题复杂度选择无检索、单步或迭代检索，在开放域 QA 实验比较质量与效率 | 可预留 QueryPlanner/ExpansionPolicy；初期用可解释规则，后续分类器是替换策略。企业证据任务是否可无检索须由任务政策规定，论文不授予绕过来源的权限 |

## 由证据推导的设计选择

“抽象程度”应暴露为材料表示选择，而非将一个速度标签同时用于内容层级、召回方法和返回形式。候选表示从原始材料、完整内容、结构片段、单条检索摘要延伸到专题与领域综合；关键词卡、关系图和两类研究文稿通过视图类型表达。表示之间可以有固定 drill-down 引用，但不保证每份材料都有每层表示。

上层表示通常降低匹配文本与后续阅读量；它是否降低候选数量，还取决于聚合单位和物理索引。短摘要若每条原记录仍各存一个，条目数量并未减少；若现场调用模型生成摘要，响应可能更慢。对未建立表示的请求应返回明确缺口，或按显式允许的回退策略使用已有表示。

逐步查询至少沿两个方向展开：扩大语料范围，以及从粗表示深入固定原文。二者都必须保留排除项、权限、实际依据、预算和停止原因；它们不能被一个越来越大的 limit 替代。最终上下文应保留必要定义、反例和省略信息，不由召回器直接生成新的事实结论。

本轮未运行这些外部系统、模型或数据集，没有本地延迟、准确率或内存数字。后续比较应在相同语料、候选范围、索引水位、模型与总预算下进行，并把索引成本与在线查询成本分开。
