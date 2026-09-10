# 表示查询首期软件验证固定记录

Run：`RUN-20260909T194710Z-3CF36B2FDD60`，本机 Windows 11 x64、Python 3.12.10、Node 22.11.0。验证时源码含既有未提交修改，未创建新 Git 提交。本文件固定软件验证时点；后续项目文稿保存和 AI 页面审查另附回执，不据此预先宣布通过。

## 实际执行

| 层级 | 原始结果 | 固定依据 |
|---|---|---|
| quick v2 | 517 项：516 通过，1 项既有 B01 失败；其中 Python 473、类型 1、组件 29、Edge 14 | `testing/quick-attempt-01/results.json`；这是较早集成版本，不能替代最终 full |
| full v4 | 599 项：596 通过，2 失败、1 错误，无跳过；Python 555（552 通过），类型 1、组件 29、真实 Edge 14 均通过 | `testing/full-attempt-01/results.json` 及原始日志；整体状态保留 failed |
| C17 补测 | 测试夹具误用不存在 owner C；按真实 A/B 端点修正后 1/1 通过 | `inheritance-closure-final.json`；full 载入旧测试形成的 KeyError 原样保留 |
| 结构类型补测 | 关联 differences 字段未同步到 memory-v3.d.ts；用正式生成器同步后 11/11 契约检查通过 | `testing/memory-contracts-supplement-final.log` |
| 最终工作台构建 | 契约生成、前端契约、类型检查、Vite 构建 4 步通过 | `testing/build-attempt-03/results.json` 与资源指纹；先前 EPERM 失败回执保留 |
| 定向继承反例 | 范围、局部证据、召回、图、维护、复核和资源等按实际回执逐项映射 | `INHERITANCE_ACCEPTANCE.md`；方法存在不等于全部旧 DTO 或可选策略完成 |
| 六种表示成本 | 6/6 查询并组包 complete；累计读取 45,845–57,635 字节，输出 223–746 字符，模型调用 0 | `cost-attempt-02/results.json`、`COST_REVIEW.md`；合成小例，非独立性能基准 |

full 的程序、测试、schema、选择和资源指纹在原回执中冻结。补测只关闭对应问题，不改写 full 的原始结果，也不重复计算成 599 项全部通过。生成声明的更新不改变运行逻辑；最后一次工作台构建已含匹配的 JSON schema。

## 保留的故障与边界

B01 `test_b01_frozen_plan_self_test_leaves_assets_unchanged` 仍失败：历史冻结 fixture 的现有指纹差异与基线一致。没有更新冻结清单来制造通过，需另行追溯历史输入。当前不能将整个回归层宣布全绿。

真实 `setup.cmd` 扩展旧工作区测试已在 quick/full 执行，覆盖预览、升级、重复升级、恢复及损坏业务元数据/真实缺失工具拒绝。共享 fixture 包含多层目录、中文/空格、空目录、自定义工具/Skill、缓存边界及持久维护计划；按完整保护清单检查哈希与目录。该结果限本机隔离合成目录，第二台物理机尚未验收。

Python 锁和标准模型指纹未变，前端增加的 @types/node、undici-types 是开发依赖。使用端仍随源码接收预构建资源，升级入口为独立新版目录的 `setup.cmd --target "旧工作区路径" --register --open`。依赖/模型更新仍须配套离线 ZIP；本次没有生成或发布新依赖包。清单审查见 `PORTABILITY_REVIEW.md`，当前业务来源登记不得带入公共发行。

## 实际 AI 与人工

A07–A09 已有真实公开调用、材料阅读、逐项 AI 自查及失败尝试，分别验证表示缺口、结构类比与新反证维护；见 `actual-ai/` 和 `browser/partial-status/AI_UI_REVIEW.md`。这是合成案例中的实际 AI 使用，不是企业材料准确度结论。项目实现章节、完整过程稿和简报的当前回读及界面检查将在本文件冻结后单独登记。

人工验收、科学复核、独立检索质量题集、第二物理机及万条规模实验未因软件结果获得通过。未配置的模型/分词器、向量或其他可选策略仍按能力表显式不可用或降级；不能承诺任意后端/模型一键替换。未执行对外发布、企业连接或原始材料修改。
