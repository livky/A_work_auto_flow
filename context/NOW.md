# 当前状态

更新日期：2026-09-10。本页只保留当前能力、限制与续接入口；实现细节见[架构说明](../ARCHITECTURE.md)。

## 当前实现

- 版本记忆已采用 v3：L1 为实验/方法/推导/分析技术单元，检索说明与完整正文块分离；`document_section` 和 `document` 独立保存章节、完整研究过程与精简研究报告，`level=null`。L4 继续是知识地图；v1/v2 历史按兼容方式读取。
- Run 优先保存在实际所属对象内。`run-execute` / `run-register` 保存执行材料与当前指纹，L0 自动投影；不是后台捕获任意程序，也不会自动编写技术文稿。
- 材料检索与规范记忆检索两条路径并存；共用 SQLite 文件但分表、分回执和部分策略。默认知识搜索排除 L0 正文；文稿与原始追溯使用对应模式。新记忆完整图扩展目前属于评估链路，不能推断默认 context 已自动执行。
- 工作台提供材料关系、版本记忆、研究文稿与续接、证据查看和监测。监测需显式开启，仅生成观察和维护候选。
- 材料查询应用已接通六类表示、逻辑/存储树、固定候选选择与组包、已有关系加深和语义维护任务包；查询复用规范记忆，未引入第二套正文存储。范围硬上限、累计预算、局部证据和事务恢复均有显式回执。当前策略及限制见[材料查询手册](../docs/MATERIAL_QUERY.md)与[运行继承状态](../docs/design/representation-query-v0.2/RUNTIME_STATUS.md)。
- Windows 升级仍由新版源码中的 `setup.cmd --target` 更新旧工作区，保留业务对象、规范记忆、自定义 Skill 和可恢复回执。依赖/模型按配套包离线核验，当前自动模型迁移限于约定路径/名称与兼容 384 维。
- 完整 checkout 保留浮点求和开发例子；公共 `git archive` 排除研究、项目和 Run 实例。当前工作区来源登记以固定 SHA 和显式旧路径映射支持直接回读；数值复现的准备脚本仍只在 `.local/examples/` 恢复旧布局。

当前使用入口：[记忆指南](../docs/MEMORY_USAGE.md)、[研究记录标准](../docs/RESEARCH_RECORDING.md)、[Run 捕获](../docs/RUN_CAPTURE.md)、[检索手册](../docs/RETRIEVAL.md)。

## 最近完成

浮点研究读取与检索现场修复：补回 23 个来源 ID 和 27 个冻结历史文件的位置映射，保留原 Run/记忆字节。全文/向量索引补偿完成，完整过程 8 章可读，“浮点数”全局完整研究探索查询返回 11 项且无覆盖警告。102 项 Python、8 项组件、3 项浏览器及类型检查通过；真实 setup 预览/升级/重复/恢复保留检查通过。记录见 RUN-20260910T050158Z-028371C48C3A；人工、第二物理机与科学复核独立待审。

[表示查询 v0.2](../docs/design/representation-query-v0.2/README.md)已从实施准备进入实际开发与整合验收。工作台已接入，三个AI Skill已安装；具体软件回归、实际AI使用、历史故障及待验收项分别保存于实施 Run：RUN-20260909T194710Z-3CF36B2FDD60。实施准备 Run RUN-20260909T190818Z-8ADA1DF3337B 保留为历史设计证据。


根据用户后续问题，[CORE说明](../projects/architecture-evolution/design/interfaces-v0.1/CORE.md)及[专项提案](../projects/architecture-evolution/design/interfaces-v0.1/REPRESENTATION_AND_GRAPH.md)区分表示类型、实例和查询组合，补齐L0–L4/双文稿配方、经验联想、AI与确定性维护分工、关系图字段和更新触发。`RUN-20260909T184202Z-6E13D341B986`保存当时尚未实施的提案和相关文稿r3，旧版保留；其后形成v0.2契约，本轮运行接入与验证见上方实施Run。

接口契约v0.1已形成[核心简版](../projects/architecture-evolution/design/interfaces-v0.1/CORE.md)、完整签名/数据结构与实施映射；所有未显式覆盖的Project默认采用Research同等explore/fine、L0–L4与总结建议。`RUN-20260909T164914Z-D20A9406384A`保存实际默认策略变化及24条分层/文稿记录的回读：两文稿均覆盖8个技术单元。quick为135项Python通过、1项既有冻结夹具失败、19项前端未运行；真实setup扩展旧工作区测试通过。页面检查受浏览器ERR_BLOCKED_BY_CLIENT限制，人工及第二台物理机验收仍待完成。

框架文档与模块影响同步已完成，记录于 `PRJ-ARCHITECTURE-EVOLUTION`，目录为 `projects/architecture-evolution/`。本轮按 docs 的声明时间、合入时间及实际代码修正 README/AGENTS、手册和 Skill；现行影响图位于该项目的 `context/MODULE_IMPACT.md`，执行 Run 为 `RUN-20260909T151004Z-A68FBA9F176D`。74 文件时间盘点及本地链接/指纹检查通过；quick 的 12 项 Python 通过、12 项前端因缺开发依赖未执行，整体 incomplete。历史 fixture 清单的三个既有指纹差异保留待追溯。

后续开发先按[文档与模块影响维护](../docs/DOCUMENTATION_MAINTENANCE.md)检查关联。Project 是本工作区的研发数据，公共源码包不携带该实例；发行仍保留通用维护入口。

## 尚未完成的验收与风险

- 历史检索独立题集质量未通过，万条规模测试按此前授权暂缓；没有真实公司材料上的准确度或大规模性能承诺。
- 实际 AI 检查、人工意见和第二台物理机验收分别记录；软件回归不能替代。历史详情见[状态台账](../docs/design/system-memory/STATUS.md)。
- 来源、旧修订与文稿引用不自动换成新版；已进入旧聊天的内容也不会撤回。
- 当前没有自动远程备份、通用代码影响监听器或企业连接器。文件与自然语言规则不能替代备份、实际权限和审计。

## 下一步

当前用户验收入口：[本地登记与索引审计](../projects/architecture-evolution/runs/run-20260910t063103z-902da8123205/AUDIT_REPORT.md)、[29项工作台与A01–A09检查表](../projects/architecture-evolution/runs/run-20260910t063103z-902da8123205/HUMAN_CHECKLIST.md)。先做正式区只读检查，再用独立演示区检验写入/维护；人工结果单独追加。审计发现的历史源码指纹变化、未分发旧Run及snapshot旧解析缺口保持显式，不用索引补偿消除历史风险。

P0–P6首期实现和整合记录已收口，见[实施Run](../projects/architecture-evolution/runs/run-20260909t194710z-3cf36b2fdd60/README.md)。full原始596/599通过，两项已补测关闭，既有B01冻结指纹故障保留；Project双文稿r5及实际页面检查已完成。后续策略优化见[待开发计划](../待开发计划.md)。人工及第二机器验收独立待审；冻结的开发清单与v0.1基线保留设计时点。

此前逐批 NOW 记录原样保存在本轮 Run 的 `baseline/NOW.md.snapshot`；docs 时间线位于 Project 的 `docs/DOCUMENT_HISTORY.md`，旧 Git 历史和未分发 Run 的缺失边界继续保留。不要把历史某批“当前/下一步/未发布”当成今天的能力状态。
