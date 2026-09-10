# 本轮模块影响处置

Run：`RUN-20260909T151004Z-A68FBA9F176D`。目标是文档同步与影响维护，不改变产品实现。现行图见[MODULE_IMPACT.md](../../context/MODULE_IMPACT.md)。

| 模块/变化原因 | 处置 | 实际检查与结果 |
|---|---|---|
| MEM：默认 v3、旧 detail/map.report 兼容 | 需修改，文档已改 | schema/contracts/service 已读；MEMORY_USAGE/REQUESTS、根规则和术语更新；不改规范提交或历史哈希 |
| DOC：L1 四类技术单元、完整块和双文稿 | 需修改，文档已改 | technical_units/documents 已读；对齐独立章节、research_process/research_report、默认选择和局部预算；L4 保留地图职责 |
| OBJ：对象内 Run、L0 自动登记 | 需修改，文档已改 | workspace_cli/manifest_discovery/run_capture/raw_materials 已核对；修正新 Run 根目录旧说明和不存在的自动递归假设 |
| EVD：当前权限、固定引用和复核边界 | 已检查，说明补充 | 现行手册区分保存/执行/复核；文稿影响只提示复查；未改变证据状态或失效算法 |
| RET：材料/记忆双路径与图扩展 | 需修改，文档已改 | 对齐 Q/CTX 与 QMEM/PKT、knowledge/documents/trace、search auto/context off；完整图扩展注明属于评估链路 |
| APP：CLI/API/工作台说明 | 需修改，文档已改；代码无需修改 | 对齐实际动作、文稿入口和类型；未改前端源码、生成类型或预构建资源 |
| GUIDE：重复定义和历史时点混淆 | 需修改，文档已改 | README/AGENTS/context/五个工作流使用集中定义与维护入口；历史设计只加顶部时点说明；原 NOW 保存快照 |
| QA：验证、部署和发行边界 | 已检查，手册同步 | 测试定义/代码未改；Windows 路线统一 setup --target；Project 实例继续排除公共包，通用维护手册随源码交付 |
| 架构性能优化、统一查询接口、图联想 | 延期到后续设计/实施 | 本轮仅定位实际边界，不因文档修正宣称已经重构或提高召回/速度 |

## 检查状态

- 开发前 testing audit 与选择校验通过。
- quick 第一次执行：12 个 Python 检查通过，含真实 setup 升级/恢复；12 个前端选择因缺 `frontend-dev` 未执行，整体 `incomplete`。详见[执行回执](testing/attempt-01/README.md)。未修改选择来制造通过。
- 文档示例由协作 AI 实际读取并做 JSON/Python 语法及当前契约校验；最终统一文档检查结果另存本 Run 的 REVIEW.md。
- 未改产品可执行代码、模型/依赖锁、schema、前端资源、旧 Run 或规范 memory。
- 历史 fixture 清单有三个既有指纹差异，与 HEAD 同字节，原因未确认；详见[时间线的缺口记录](../../docs/DOCUMENT_HISTORY.md#本次检查与历史验证缺口)。保留原文件与清单，不把本轮检查当其通过证明。

人工审查：待审。科学复核：不适用；本次未产生业务模型结论。
