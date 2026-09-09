# 开发任务卡与依赖

版本1.0。以下是待实现的代码交付物。测试材料准备不等于产品任务已通过。实际状态见[STATUS](STATUS.md)。

## 使用方法

一次选一个满足依赖的任务，先固定输入/故障场景，再实现结构、函数和算法，运行关联测试。完成状态：planned→active→implemented→verified；受阻为blocked。缺必要测试、失败或skipped不得verified。

契约修改先更新01/02、schema与配方，再检查下游任务。每批在固定Run中汇总代码版本、配置、输入hash、结果和限制，不为每个小步骤建立新项目。

## 可并行部分

- W03后W04证据、W05研究状态、W06索引可独立开发，均使用W01契约。
- W04以正式证据投影验收；完整上下文/工作台联动在Z02验收，避免基础模块依赖未完成的下游。
- W07依赖W04/W06；W08汇合证据、研究状态、索引和关系。
- W09后W10工作台与W11迁移可并行实施；W11最终发行/升级验收还需W10预构建资源完成。
- W12等待全部底层功能、界面与迁移完成后编写最终调用指导和Skill。W13执行完整链路、真实模型留出评价。
- 数学单元测试可用确定性向量；I08/M09必须真实离线模型。可并行是依赖关系，不要求创建多个AI任务。

## W00 执行基线与合成测试材料

**目的：** T01、T09。**前置：** 无。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `docs/design/system-memory/fixtures/`；`automation/tests/memory_fixture.py（待建）`。

**交付物：**

- 当前提交及差异、现有回归结果
- fixture.materialize/固定时钟ID/故障注入支持

**实施步骤：**

1. 保存现有行为与环境基线，不改变测试门槛。
2. 把recipes转为临时旧对象和待提交草案；最终hash由真实适配器计算。
3. 冻结查询分割；建立逐用例结果记录，不提前标pass。

**验收：** [B01](04-acceptance.md#b01)、[B02](04-acceptance.md#b02)、[B03](04-acceptance.md#b03)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W01 统一数据契约

**目的：** T01、T02。**前置：** W00。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/contracts.py（待建）`；`automation/schemas/memory-v1.schema.json（待建）`。

**交付物：**

- MemoryRecord/Owner/Ref/Claim/请求回执schema
- 公共验证和前端类型生成

**实施步骤：**

1. 实现01文档字段和状态约束，补齐每个kind正反例。
2. 规范hash、未知值、类型登记与client_key批量解析。
3. 以同一schema生成前端类型，写失败字段定位。

**验收：** [C01](04-acceptance.md#c01)、[C02](04-acceptance.md#c02)、[C03](04-acceptance.md#c03)、[C04](04-acceptance.md#c04)、[C05](04-acceptance.md#c05)、[C06](04-acceptance.md#c06)、[C07](04-acceptance.md#c07)、[C08](04-acceptance.md#c08)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W02 版本存储与最小调用闭环

**目的：** T01、T02。**前置：** W01。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/store.py、service.py、cli.py、recovery.py（待建）`；`automation/scripts/workspace_cli.py`。

**交付物：**

- 不可变commit/HEAD/回执/锁/恢复
- inspect、validate-draft、commit、recover最小CLI

**实施步骤：**

1. 先实现首次保存、按ID读取与单记录修订。
2. 加入批次原子性、幂等ledger和no_change回执，再测试全部故障窗口。
3. 接入CLI JSON输出/失败码，索引以接口桩返回pending并可补偿。

**验收：** [S01](04-acceptance.md#s01)、[S02](04-acceptance.md#s02)、[S03](04-acceptance.md#s03)、[S04](04-acceptance.md#s04)、[S05](04-acceptance.md#s05)、[S06](04-acceptance.md#s06)、[S07](04-acceptance.md#s07)、[S08](04-acceptance.md#s08)、[S09](04-acceptance.md#s09)、[S10](04-acceptance.md#s10)、[S11](04-acceptance.md#s11)、[S12](04-acceptance.md#s12)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W03 八类旧对象适配

**目的：** T01、T09。**前置：** W02。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/owners.py、policy.py（待建）`；`automation/scripts/workbench_app/projection.py`。

**交付物：**

- 八类OwnerAdapter及adopt-owner
- 保留旧Run/CLM/文档身份的读取映射

**实施步骤：**

1. 按01文档分别实现专属目录、旁目录和tool映射。
2. 缺稳定ID文档按需采用，原正文和旧manifest不改。
3. 把已有Run作为事件视图，保留旧命令及复核指纹。

**验收：** [O01](04-acceptance.md#o01)、[O02](04-acceptance.md#o02)、[O03](04-acceptance.md#o03)、[O04](04-acceptance.md#o04)、[O05](04-acceptance.md#o05)、[O06](04-acceptance.md#o06)、[O07](04-acceptance.md#o07)、[O08](04-acceptance.md#o08)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W04 结论复核与失效传播

**目的：** T02、T05。**前置：** W03。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/evidence_adapter.py、impact.py（待建）`；`automation/scripts/evidence.py`。

**交付物：**

- memory CLM读取适配和ReviewEvent
- 正式证据检查与派生更新影响图

**实施步骤：**

1. 扩展EvidenceGraph读取，不修改旧fingerprint解释。
2. 绑定新claim到证据记录content_hash，动态状态独立。
3. 实现撤回/替代/来源变化回源及跨对象影响；处理循环、范围和混合状态。

**验收：** [E01](04-acceptance.md#e01)、[E02](04-acceptance.md#e02)、[E03](04-acceptance.md#e03)、[E04](04-acceptance.md#e04)、[E05](04-acceptance.md#e05)、[E06](04-acceptance.md#e06)、[E07](04-acceptance.md#e07)、[E08](04-acceptance.md#e08)、[E09](04-acceptance.md#e09)、[E10](04-acceptance.md#e10)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W05 问题、目标、路线与检查点

**目的：** T03、T06。**前置：** W03。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/research.py、policy.py（待建）`。

**交付物：**

- 状态转换函数、目标/路线版本、检查点
- 基础/积累/探索策略解析

**实施步骤：**

1. 先实现问题状态机及resolved/superseded依据。
2. 加入目标演进、路线阻碍/重开及四类失败。
3. 完成策略优先级和检查点提交；执行状态不自动驱动问题状态。

**验收：** [R01](04-acceptance.md#r01)、[R02](04-acceptance.md#r02)、[R03](04-acceptance.md#r03)、[R04](04-acceptance.md#r04)、[R05](04-acceptance.md#r05)、[R06](04-acceptance.md#r06)、[R07](04-acceptance.md#r07)、[R08](04-acceptance.md#r08)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W06 统一索引与多表示检索

**目的：** T04。**前置：** W03。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/index.py、search.py、evaluation.py（待建）`；`automation/scripts/retrieval.py、qdrant_backend.py`。

**交付物：**

- 新增SQLite派生表、索引水位和多表示
- FTS、向量适配、折叠排名与评价入口

**实施步骤：**

1. 先验收无模型FTS和可按ID重建。
2. 加入表示槽约束、通道内去重与RRF。
3. 加入现有向量后端与版本隔离，仅用32条开发查询调试；完整方案/留出集I08归W13，避免下游未完成就要求集成通过。

**验收：** [I01](04-acceptance.md#i01)、[I02](04-acceptance.md#i02)、[I03](04-acceptance.md#i03)、[I04](04-acceptance.md#i04)、[I05](04-acceptance.md#i05)、[I06](04-acceptance.md#i06)、[I07](04-acceptance.md#i07)、[I09](04-acceptance.md#i09)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W07 跨对象相关性与关系记录

**目的：** T04、T05。**前置：** W04、W06。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/associations.py（待建）`；`automation/scripts/workbench_app/analysis.py、projection.py`。

**交付物：**

- 关键词/语义/显式关系候选
- 单一关系写入、邻接遍历及过期检查

**实施步骤：**

1. 先读取/保存显式关系和两端版本。
2. 实现Jaccard/向量候选解释、处理状态和单边存储。
3. 实现有界图扩展、排除先行与循环去重，不自动建科学支持。

**验收：** [G01](04-acceptance.md#g01)、[G02](04-acceptance.md#g02)、[G03](04-acceptance.md#g03)、[G04](04-acceptance.md#g04)、[G05](04-acceptance.md#g05)、[G06](04-acceptance.md#g06)、[G07](04-acceptance.md#g07)、[G08](04-acceptance.md#g08)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W08 研究经过、检索包与AI续接

**目的：** T03、T04。**前置：** W04、W05、W06、W07。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/history.py、packets.py、summaries.py（待建）`；`automation/scripts/context_engine.py`。

**交付物：**

- history/resume/expand/context服务
- 角色分组、预算、两次反馈扩展、总结材料包

**实施步骤：**

1. 按目标和路线组装确定性经过，处理未知时间和分页。
2. 组装续接并重验来源，保留已完成和缺口。
3. 统一检索包预算与范围；复用context_engine反馈链，补入跨对象版本清单。

**验收：** [P01](04-acceptance.md#p01)、[P02](04-acceptance.md#p02)、[P03](04-acceptance.md#p03)、[P04](04-acceptance.md#p04)、[P05](04-acceptance.md#p05)、[P06](04-acceptance.md#p06)、[P07](04-acceptance.md#p07)、[P08](04-acceptance.md#p08)、[P09](04-acceptance.md#p09)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W09 价值触发、巩固与跨项目总结

**目的：** T05、T06。**前置：** W08。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/consolidation.py、summaries.py、feedback.py（待建）`。

**交付物：**

- prepare/apply变化清单与巩固水位
- L2/L3总结保存和采用结果反馈

**实施步骤：**

1. 计算changed/affected/remaining以及basis_hash。
2. 校验AI的revise/retain/defer，保留未处理项，拒绝过期依据。
3. 实现总结提交与新解释修订、去重/冲突候选、反馈关联到后续Run。

**验收：** [N01](04-acceptance.md#n01)、[N02](04-acceptance.md#n02)、[N03](04-acceptance.md#n03)、[N04](04-acceptance.md#n04)、[N05](04-acceptance.md#n05)、[N06](04-acceptance.md#n06)、[N07](04-acceptance.md#n07)、[N08](04-acceptance.md#n08)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W10 工作台与完整公共入口

**目的：** T07。**前置：** W09。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/workbench_app/web.py、service.py`；`automation/frontend/src/Memory.tsx、MemorySearch.tsx（待建）`；`automation/ui/workbench-assets/`。

**交付物：**

- /api/v1/memory固定服务路由
- 对象/检索/经过/总结/关系/续接页面和预构建资源

**实施步骤：**

1. 映射统一服务与错误契约，不在前端复制业务状态逻辑。
2. 完成查看、编辑冲突、索引补偿、复核、关联和复制续接。
3. 执行浏览器E2E、安全显示、构建与指纹检查。

**验收：** [U01](04-acceptance.md#u01)、[U02](04-acceptance.md#u02)、[U03](04-acceptance.md#u03)、[U04](04-acceptance.md#u04)、[U05](04-acceptance.md#u05)、[U06](04-acceptance.md#u06)、[U07](04-acceptance.md#u07)、[U08](04-acceptance.md#u08)、[U09](04-acceptance.md#u09)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W11 迁移、保护清单与离线交付

**目的：** T09。**前置：** W09。最终验收另需 W10 完成。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/scripts/memory/migration.py（待建）`；`automation/tests/upgrade_fixture.py`；`automation/scripts/deployment.py、portable.py`。

**交付物：**

- 记忆导出导入和旧材料显式采用
- 共享升级fixture扩展、受控发行清单、索引/依赖恢复

**实施步骤：**

1. 先实现导出依赖清单、预览/冲突/恢复与路径映射。
2. 扩展现有upgrade_fixture保护整个memory历史、旁目录和用户扩展。
3. 跑真实setup预览、升级、重复升级、源码恢复及完整离线依赖链路；补足嵌套计划/schema/测试素材的受控分发清单。

**验收：** [M01](04-acceptance.md#m01)、[M02](04-acceptance.md#m02)、[M03](04-acceptance.md#m03)、[M04](04-acceptance.md#m04)、[M05](04-acceptance.md#m05)、[M06](04-acceptance.md#m06)、[M07](04-acceptance.md#m07)、[M08](04-acceptance.md#m08)、[M09](04-acceptance.md#m09)、[M10](04-acceptance.md#m10)、[M11](04-acceptance.md#m11)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W12 正式调用指导与AI Skill

**目的：** T08。**前置：** W10、W11。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `automation/workflows/各相关SKILL.md`；`automation/scripts/install_workspace_skills.py`；`.agents/skills/相关入口（实施时维护）`；`docs/MEMORY_USAGE.md（待建）`。

**交付物：**

- 真实接口使用指南、示例、失败处理
- 更新workspace-context/context-maintenance/evidence-inspection与research-loop入口

**实施步骤：**

1. 所有底层数据结构/函数/算法验收后，从真实接口生成调用示例。
2. 按职责更新现有工作流；在执行时使用skill-creator约定，保留用户Skill。
3. 运行固定AI任务卡，进行第二轮仅凭落盘记录的续接评价。

**验收：** [K01](04-acceptance.md#k01)、[K02](04-acceptance.md#k02)、[K03](04-acceptance.md#k03)、[K04](04-acceptance.md#k04)、[K05](04-acceptance.md#k05)、[K06](04-acceptance.md#k06)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## W13 整体评价与交付核对

版本1.1增补：[人类可阅使用验收H01–H18](05-human-acceptance.md)。原技术测试保留，新增用例以[plan-extension.json](human-acceptance/plan-extension.json)和[cases.json](human-acceptance/cases.json)登记，不改原冻结work-packages.json。

交付增加：AI实际使用Skill/正式产品的原始返回、实际查阅内容及位置、预期与实际对照、逐项审查页和用户最终意见。执行规则为“真实操作→取得结果→AI实际阅读并留痕→AI自评→用户审查”。用户确认前保持待审查，不以AI自评代替最终通过。

H01–H18覆盖保存材料/分析/失败、找回修改、跨研究检索/关系/总结、问题与目标、完整经过、暂停续接、纠错、异常恢复、范围限制、工作台导出、迁移及阶段巩固。具体自然语言任务和预期见05文档；可复用同版本K/Z组真实证据，但必须补齐查阅留痕。

**目的：** T01、T02、T03、T04、T05、T06、T07、T08、T09。**前置：** W12。

**输入：** 前置契约与服务、固定合成配方、当前源码及环境指纹。数据结构见01，函数与算法见02。

**修改位置：** `README.md、docs/使用/部署手册`；`runs/<实际验收Run>/`；`docs/design/system-memory/STATUS.md`。

**交付物：**

- 固定验证Run与逐用例报告
- 源码/资源/依赖/README/恢复/发布准备核对

**实施步骤：**

1. 执行完整回归、留出评价、AI长链演练和规模测试。
2. 复查README概念、目录维护、知识导入、常用Skill和迁移命令。
3. 保存实际程序版本、输入/输出hash和限制；公开上传另按用户发布指令。

**验收：** [I08](04-acceptance.md#i08)、[Z01](04-acceptance.md#z01)、[Z02](04-acceptance.md#z02)、[Z03](04-acceptance.md#z03)、[Z04](04-acceptance.md#z04)、[Z05](04-acceptance.md#z05)、[Z06](04-acceptance.md#z06)。每例全部断言通过，保存回执/指纹差异与固定Run后才标verified。

**交接：** 实际修改文件/函数、测试ID与状态、失败原因、Run、剩余约束、精确下一步。当前状态：planned。

## 验证入口

计划新增测试文件：`test_memory_contracts.py`、`test_memory_store.py`、`test_memory_owners.py`、`test_memory_evidence.py`、`test_memory_research.py`、`test_memory_index.py`、`test_memory_associations.py`、`test_memory_packets.py`、`test_memory_consolidation.py`、`test_memory_http.py`、`test_memory_migration.py`。它们在实施任务中创建，本轮尚不存在。

从仓库根运行：

```powershell
.\automation\workspace.ps1 refresh-index
.\automation\workspace.ps1 validate
.\automation\python.ps1 -m unittest discover -s automation/tests -p "test_memory_*.py" -v
.\automation\python.ps1 -m unittest discover -s automation/tests -v
```

W10在automation/frontend执行contracts、typecheck、test、e2e、build及资源manifest；W11执行[升级测试约定](../../UPGRADE_TESTING.md)中的真实setup和完整依赖验收；W13在最终源码版本重跑必要集成。测试尚未创建时，“0 tests”不是通过。
