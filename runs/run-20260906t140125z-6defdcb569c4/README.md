# RUN-20260906T140125Z-6DEFDCB569C4：研发可靠性第一批实现与回归验证

本 Run 记录经用户同意实施的首批可靠性改进。执行成功表示实现与记录完成；复核保持 not-reviewed，未封存为公司算法的正式依据。

## 输入与实现范围

依据 [结构评审](../../research/agent-workspace-review/SYNTHESIS.md) 和 [实施计划](../../docs/design/evidence-controls-plan.md)，在既有目录、CLI、Run 和分阶段检索上增加结论级证据、适用范围、复核版本绑定、跨文档失效、正式上下文、Run 检查/封存，以及 doctor/verify。用法见 [手册](../../docs/EVIDENCE_CONTROLS.md)。

基线 commit 为 8b54b060dd8d0366baf049f4851a40a7edd522bf；本次修改尚未提交，dirty=true。当前脚本、测试与配置的文件哈希见 [输入快照](inputs.json)。未导入公司材料，合成测试在临时隔离工作区执行，未改变正式检索配置。

## 结果与验证

| 检查 | 实际结果 | 证据 |
|---|---|---|
| 最终 core 回归 | 72 项；65 通过、7 跳过、0 失败/错误；退出 0，passed-with-skips | [verify-core-v3.json](verify-core-v3.json) |
| full 严格模式实测 | 72 项；测试无失败/错误但跳过 7 项；缺 vector/OCR，退出 1 | [verify-full-v2.json](verify-full-v2.json) |
| 最终结构校验 | 0 错误、4 条原有历史链接警告 | [validate-final.txt](validate-final.txt) |
| 索引刷新 | 缺 qdrant_client，退出 2 | [index-attempt-final.txt](index-attempt-final.txt) |

新增 23 项测试覆盖正式输出不混入未复核正文、范围保留、输入/产物/正文漂移、撤回与多级依赖传播、背景及反证关系、循环/缺失、越界来源、预览及复核历史、封存后变更、跳过和损坏的质量检查。测试通过只能说明这些合成机制场景符合预期。

保留中间尝试以便复盘：[tests.txt](tests.txt) 是第一次完整回归，因模块名与参数名冲突出现 4 个错误，修正别名后通过；[verify-core.json](verify-core.json) 曾在测试无错误时因 PowerShell 预先创建空 JSON 输出文件使结构校验失败，后续先写 tmp 再移入 Run。[verify-core-final.json](verify-core-final.json)、[verify-full.json](verify-full.json) 是 71 项阶段记录；[verify-core-v2.json](verify-core-v2.json) 与 full-v2 已包含封存后输入/产物检查，core-v3 再补损坏质量条目的断言及换行规范化。

## 结论、限制与后续

事实：第一批 CLI 和证据检查已实现，core 按部分通过如实报告，full 未通过；当前 FTS 探针可用，向量/OCR/便携运行时缺失，真实评估集为 0。结构评审的旧记录原样保留，不能把本批实现回写为评审时已存在。

限制：未做真实公司算法、语料规模或跨电脑验证；未认证复核者身份；封存只检查记录与固定证据，不证明科学命题。任意 shell、外部编辑器、旧聊天和已发布报告不受 CLI 自动更正。未引入自动备份、调度服务或企业连接器。

下一步：恢复获准的本地依赖/模型后跑 full；以首批获准的算法说明、固定实现和历史结果开展真实试点，再依据领域复核建立答案验收集。
