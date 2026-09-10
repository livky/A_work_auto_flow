> 后续实施定义已收敛到 [v0.2 契约、工作台与测试计划](../README.md)。G03 类型/实例、联想和维护以新版实施设计为准；本页与 Python v0.1 保留前一版设计，不代表产品已接入。

# 抽象接口设计 v0.1

先读[核心功能说明](CORE.md)：从具体定义和例子开始，解释内容保存、材料表示、索引更新，以及查询、补查、使用和修订的完整闭环。本目录定义十二组职责的40个领域方法，另有3个共享执行控制方法；72个数据结构覆盖固定身份、知识属性、范围、表示、候选、回执和修改计划。当前是可检查的设计包，尚未由产品运行链路引用。

| 文件 | 维护职责 |
|---|---|
| [CORE.md](CORE.md) | 面向阅读者的概念解释、输入输出与完整流程；术语首次出现时给出定义和例子 |
| [REPRESENTATION_AND_GRAPH.md](REPRESENTATION_AND_GRAPH.md) | 类型与实例的区分、L0–L4/双文稿组合、经验联想、AI分工和图生命周期；包含待进入下一版类型契约的提案 |
| [SPEC.md](SPEC.md) | 输入语义、行为约束、调用图、状态所有权与错误 |
| [contract_types.py](contract_types.py) | 数据字段与 Python 类型；业务 payload 复用注册 schema |
| [contract_ports.py](contract_ports.py) | 方法签名；仅依赖类型契约，无具体后端 |
| [function-catalog.json](function-catalog.json) | 每个函数的必要性、前后置条件、错误与实现落点；合并/预留/排除的候选 |
| [FUNCTIONS.md](FUNCTIONS.md) / [DATATYPES.md](DATATYPES.md) | 从类型和函数目录生成的可读视图，不单独手改 |
| [request-examples.json](request-examples.json) | 合成请求与反例，不包含真实来源或运行结果 |
| [check_contracts.py](check_contracts.py) | 静态一致性和合成请求检查；--write 刷新两个派生文档 |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | 当前代码映射、实施顺序与后续验收 |

从工作区根目录检查：

```powershell
.\automation\python.ps1 docs/design/representation-query-v0.2/baseline-v0.1/check_contracts.py
```

修改字段/方法后同步 SPEC 和函数目录，运行 `check_contracts.py --write`，再运行只读检查并审查差异。将设计落实到运行代码时，另建实施 Run，按实现与验收表逐步适配；不能将本目录的结构检查替代后端行为或检索质量验收。

本轮的 Project 默认策略、规则修改、测试及分层记忆保存由 `RUN-20260909T164914Z-D20A9406384A` 记录。本目录是可编辑的下一轮设计入口；本轮固定副本和引用由 Run 与 Project 规范记忆保存，后续修订不得覆盖旧版本。
