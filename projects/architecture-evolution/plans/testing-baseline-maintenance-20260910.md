# 测试基线维护规则与依据补录

日期：2026-09-10。用户同意补齐测试基线准入、复审与退出规则，并在已有清单保存逐项风险依据。范围为开发规范和 catalog 元数据，不改选择器、测试断言、产品代码或基线成员。

目标：明确测试点从行为/故障产生，区分登记与风险覆盖；为当前 24 项 quick 基线补录风险、保留原因和复审触发条件，不推测历史选入理由，不声称本轮重新执行了这些用例。

验证选择：定向检查 JSON、旧字段保持、全部 quick/full 及各能力选择一致、baseline 字段完整、盘点登记入口。文档检查链接和当前工具描述。仅规范/元数据变化，无安装、恢复、扫描逻辑或模型依赖变化，不运行真实 setup、浏览器或 full；不新增镜像实现的测试。

影响：GUIDE 与 QA 的说明和清单；模块职责、契约、发布文件边界和 Windows x64 运行依赖不变。保留旧 catalog 到本机 catalog-history，revision/history 留痕；历史选择与测试结果不改。

## 结果与文档处置

已完成：catalog 从 revision 47 升为 48，为 24 项基线增加风险、保留理由、复审触发条件与静态复审身份/时间。history 保存前后依据；原清单逐字节备份在 `.local/testing/catalog-history/revision-47-6972aa946b52454b9f6dbc60ad57886a.json`。测试 ID、依赖、权限和 quick/full 等原字段不变。

实际验证（本机 Windows，2026-09-10）：

- `testing audit` 通过：603 项登记，601 项静态发现，未分类/缺失/错误均为空。另两项不是静态用例，不由发现器枚举。
- `.local/testing/baseline-maintenance-20260910/verify_catalog.py` 通过：24 项依据字段完整；原字段和历史保留；quick/full 各自对默认范围及 15 个能力共 32 组选择比较一致。回读结果为同目录 `verification.json`。这是清单兼容检查，不是 24 项基线的执行结果。
- `refresh-index` 完成；`validate` 为 0 错误、0 警告；`git diff --check` 通过，仅有仓库既有换行转换提示。
- 本轮没有运行 quick/full、真实 setup、浏览器、实际 AI 场景或人工验收。没有修改运行代码/依赖/安装边界；不宣称第二物理机验证。

开发前后已完整回读六份入口和开发历史。逐项处置：README 增加基线维护入口；ARCHITECTURE 已核对无需修改（QA/GUIDE 职责不变）；CORE 已核对无需修改（产品功能未变）；docs/README 更新测试导航；DOCUMENTATION_MAINTENANCE 已核对无需修改（唯一清单原则一致）；TESTING 增加生成与准入/复审/退出规则。TESTING_REFERENCE 同步真实工具边界；DEVELOPMENT_HISTORY 增加 D07；Project PLAN 与 NOW 链接本记录。development-checks 源/发现入口已核对无需修改，已将 TESTING 作为必读规范；没有引入新的固定命令链。

限制与延期：新材料查询全部风险与基线的对照不是本轮全面审查目标；不能用这次依据补录声明全功能覆盖。baseline 元数据目前由开发审查维护，audit 不强制检查字段，也不自动判断准入/退出；本轮未扩展测试器。历史选择受 catalog 指纹更新影响时，按规范新建选择，不回写旧计划。
