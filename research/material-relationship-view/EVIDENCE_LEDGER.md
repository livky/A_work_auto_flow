# 证据台账

访问日期：2026-09-07。以下为官方文档/项目说明的功能核对，未安装外部产品或固定发行版；工程取舍见综合建议，保持未复核。

| ID | 来源与核对事实 | 适用限制 |
|---|---|---|
| W1 | [Obsidian Graph view](https://obsidian.md/help/plugins/graph)：笔记节点、内部链接、颜色分组、局部深度与布局力参数 | 颜色分组不等于算法发现主题，节点大小不代表结论正确 |
| W2 | [Obsidian Canvas](https://obsidian.md/help/plugins/canvas)：卡片、分组、带标签连接、JSON Canvas；纯文本卡片需转为文件才进入反向链接 | 画布位置表达整理意图，不能自动作为证据 |
| W3 | [Heptabase](https://heptabase.com/)：白板、卡片、双向链接和 PDF 标注 | 官网功能核对；未验证同步、导入或自动聚类能力 |
| W4 | [TheBrain](https://www.thebrain.com/km/limitless-mind-mapping)：多父节点、子节点、横向跳转和以当前想法为中心的网络导航 | 关系导航模式可借鉴，不照搬产品数据结构 |
| W5 | [Smart Connections 源项目](https://github.com/brianpetro/obsidian-smart-connections)：本地嵌入发现相关笔记，支持将选择整理成 AI 上下文 | 分数依赖模型；源代码可见不表示无条件开源许可；本方案不复制其代码 |
| W6 | [InfraNodus 方法](https://infranodus.com/about/how-it-works)：词项/概念共现成图，分析主题簇及结构；方法页描述 4-gram 窗口 | 共现不表示因果或证据支持，不把特定文本窗口直接作为本仓库参数 |
| W7 | [InfraNodus 结构缺口](https://infranodus.com/tutorial/content-gap-analysis)：识别主题簇间薄弱连接并生成研究问题 | 图中缺边可能来自未登记/过滤；不能据此断言真实知识缺口 |
| W8 | [D3 force](https://d3js.org/d3-force)：通过力模拟计算图节点位置 | 屏幕距离是布局结果，不是已校准的相关性或物理距离 |
| W9 | [Cytoscape.js](https://js.cytoscape.org/)：浏览器图展示、布局、复合节点、图遍历和 JSON 数据；核心 MIT 许可 | 适用性为工程判断；第三方扩展需分别检查版本/许可 |
| W10 | [Sigma.js](https://www.sigmajs.org/)：以 WebGL 展示图，和 Graphology 组合使用 | 适合大量节点的候选方案，未在本仓库实测性能 |
| W11 | [Microsoft GraphRAG dataflow](https://microsoft.github.io/graphrag/index/default_dataflow/)：实体关系抽取、层次社区、社区摘要和嵌入 | 是额外索引流程，不是纯展示功能；本次不引入 |

## 当前实现依据

| ID | 本地依据 | 核对结果 |
|---|---|---|
| L1 | [证据图](../../automation/scripts/evidence.py) 的 EvidenceGraph、refs、_connect | 从 Run/研究/算法/知识及报告旁文件收集 owner/claim；四种显式关系 supports/input/background/contradicts，前两类参与依赖失效传播 |
| L2 | [只读快照](../../automation/scripts/evidence_observer.py) 的 collect/downstream | 已包含来源引用、资产、指纹、风险、复核及报告影响路径；传播边含内部生成边，不能全部标成原文直接引用 |
| L3 | [检索关系](../../automation/scripts/retrieval.py) 的 relations | Markdown 链接和 sources.related 构建双向邻接；同算法/研究/Run 分组内部两两连接，输出丢失具体关系类型 |
| L4 | [上下文选择](../../automation/scripts/context_engine.py) 的 plan | 已按关联跳数扩展候选，保留预算与用户选择；理由主要为 relation-hop-N，没有完整的带类型路径解释 |
| L5 | [工作台](../../automation/scripts/workbench.py) 与 [HTTP 接口](../../automation/scripts/evidence_view.py) | 模块清单、证据快照、限定来源预览、固定操作；尚无全材料带类型图接口或 AI 关系导出按钮 |
| L6 | [本地向量后端](../../automation/scripts/qdrant_backend.py) | 文本分窗编码，保存来源/指纹/定位；已有检索能力不能直接等同于材料两两语义图 |
| L7 | 只读盘点（历史记录已从 main 移除，原路径：`../../runs/run-20260907t063633z-159b86592cdd/relationship-audit.json`） | 盘点时旧检索缓存 63 份材料、277 对无向邻接；含本次研究和 Run 的证据图 7 节点、0 claim、3 条传播边；既有合成沙盒 6 节点、1 claim、4 条有类型引用 |

L7 是盘点时的固定快照，随本次研究归档和重新索引会变化。没有公司业务算法/数据样本，不能据此证明业务有效性。未使用未能读取的 Juggl 文档作为论据；Heptabase 帮助域检索无结果，改以官网功能说明为据。
