# 表示查询与维护接口 v0.2：实施设计

状态：2026-09-10 已接入工作台、CLI/HTTP与AI工作流，正式整合验收以实施Run RUN-20260909T194710Z-3CF36B2FDD60 为准。本目录保留设计时点的契约与用例；实际接口和限制见[运行状态](RUNTIME_STATUS.md)与[使用手册](../../MATERIAL_QUERY.md)。现有memory-v3持久化格式继续有效，v0.2是应用服务契约版本。

用户操作是：**选择表示类型＋问题/关键词＋范围＋用途＋是否联想＋预算 → 搜索已有索引 → 选择实际内容 → 按类型组合输出**。查询不会因为换了问题就重建索引，也不会因为选择“摘要”就要求每篇材料已有一份独立摘要。

| 阅读目的 | 文件 |
|---|---|
| 正式开发文件清单、准备缺口与P0门槛 | [开发就绪核对](DEVELOPMENT_READINESS.md)、[逐项文件清单](development-files.json) |
| 数据定义、方法、调用顺序、兼容边界 | [接口规范](CONTRACTS.md)、[可检查类型与端口](contracts.py) |
| 工作台页面、控件、状态与 HTTP 请求 | [工作台交互](WORKBENCH.md) |
| 首期任务、依赖、退出门槛、切换与恢复 | [开发计划](IMPLEMENTATION.md) |
| 合成数据、完整用例、断言与测试层次 | [测试设计](TEST_DESIGN.md)、[逐项用例](test-cases.json) |
| 为什么首期采用简单方法、何时更换 | [根目录待开发计划](../../../待开发计划.md) |

维护规则：本目录contracts.py与CONTRACTS.md保留设计基线；运行字段以`automation/scripts/material_query/contracts.py`及其生成JSON/TypeScript为准。每个方法与状态变更同步HTTP、UI和测试用例，实际继承逐项记录。运行 `automation/python.ps1 docs/design/representation-query-v0.2/check_design.py` 只检查设计一致性，不能证明功能可用。

本设计继承上一版十二组职责G01–G12与共享执行控制：固定引用、内容/CAS、索引水位、召回、排序、图、编排、材料组包、视图、维护、证据。新定义替换G03的类型/实例混用，并细化G07–G11，其余约束继续有效。原讨论位于完整工作区的`projects/architecture-evolution/design/interfaces-v0.1/`；已冻结迁入本目录[公共基线](baseline-v0.1/README.md)，并在[继承映射](INHERITANCE.md)保留43方法和约束。公共源码无需依赖被排除的Project实例来读取这些基础定义。
