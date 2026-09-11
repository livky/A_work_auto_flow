# 工作区 Skill 逐项审查

执行者：Codex；2026-09-11。范围为 workflows 方法源、安装器 NAMES 与 .agents/skills 发现入口的并集。实际阅读全文并比较当前契约；不包含全局插件、用户其他工作区或自定义内容。

| Skill | 处置与实际核对 |
|---|---|
| development-checks | 修改：六份文档及开发演进前后重读继续保留，增加每次开发结束逐项审查 Skill；不指定固定开发方法。发现描述同步 |
| material-query | 修改：标准类型/所有来源、current 与 allow_stale、5分钟/16 MiB/8万字符、documents、展开正文及必要依据上限；字段对照运行契约、CLI/HTTP，发现描述同步 |
| research-loop | 修改：合并诊断原因矩阵、V&V/UQ、固定证据报告与格式渲染检查；保留 v4 经过/经验/概览、v3 技术块与独立双文稿、真实审查，发现描述同步 |
| workspace-context | 已检查无需修改：目标算法与证据扩展，保留原 memory/CTX 两套请求边界；直接查字段不强制新建研究，分层与固定引用规则仍正确 |
| context-maintenance | 已检查无需修改：Run 登记、v3 技术块/v4 经过与经验、独立双文稿、CAS及索引待办仍适用；既有 narrative/stages 已是当前指导 |
| evidence-inspection | 已检查无需修改：保存/执行/复核分离，固定来源、撤回、只读监测及当前命令仍适用；不代写维护判断 |
| association-exploration | 已检查无需修改：实际读两端，比较结构与迁移边界，通过公开记忆入口保存导航；没有自动模型时不声称已执行语义推断 |
| semantic-maintenance | 已检查无需修改：实际阅读、保留不可变交付依据、真实 reviewer_kind、预检/提交/回读；索引和规范提交分离；旧层级迁移边界仍适用 |
| analysis-diagnosis | 退休：未在安装器/发现入口登记；诊断独特指导并入 research-loop，简单历史查看仍用 workspace-context |
| core-algorithm-design | 退休：未注册；准入由根/核心算法规则与 workspace-context 承载，设计与 V&V/UQ 并入 research-loop |
| report-production | 退休：未注册；固定证据/报告产物指导并入 research-loop，实际文件格式由相应技能处理；移除与任务无关的固定问答和额外审批要求 |

3份原文在 verification/retired-skills 保存，manifest 包含旧路径、替代入口和SHA-256。唯一普通历史链接改指向原文备份，冻结审计与指纹不改写。安装器8个NAMES未变；入口同步只针对与旧生成文本完全相同的3个受控文件，预检拒绝用户自定义差异。安装预览及4项原有安装行为测试验证登记、自定义保留与批次冲突边界；机械检查不代替本表语义审查。

开发闭环写入根 AGENTS、development-checks、DOCUMENTATION_MAINTENANCE 与工作流 README。旧目标升级可能保留原有未受控的退休方法文件；不批量删除旧工作区未知文件，它们不在当前默认登记内。
