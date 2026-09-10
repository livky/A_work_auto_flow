# Windows 迁移检查（2026-09-06）
<!-- architecture-evolution-timepoint:start -->
> 时点说明（2026-09-09 整理）：本页形成时的设计、审查或实施记录；文中的“当前”“已完成”“尚未”等只对应该批次。历史正文保留，不据本次整理重新判定功能或验收状态。
> 现行入口：[架构总览](../../ARCHITECTURE.md)、[研究记录标准](../RESEARCH_RECORDING.md)。完整 checkout 中的[文档演进记录](../../projects/architecture-evolution/docs/DOCUMENT_HISTORY.md)按时间串联各批次；公共源码包不含此 Project。
> 未随源码分发的历史 Run/附件仅保留追溯线索，不能据当前源码包独立复核其结果。
<!-- architecture-evolution-timepoint:end -->

目标：完整工作区可在 Windows x64 间压缩传递，解压后使用自身运行时。

计划：检查入口和路径；增加打包预览与自检；生成 ZIP 并解压到中文空格新路径，运行离线检查；执行回归、刷新索引和记录结果。

发现：运行时 `_pth` 和模型配置已使用相对路径。检索缓存及历史证据中存在绝对路径，因此包排除可重建数据库，保留历史。系统 Codex、外部原件不属于框架便携包。

状态：实现与本机迁移验证完成。

验证证据（AI 执行，2026-09-06）：

- ZIP 实际解压至 `tmp/迁移 验证/workspace`，使用该目录的 Python、模型和依赖完成自检：384 维嵌入、OCR 推理、临时 Qdrant 查询、结构校验，0 错误/0 警告。修正后的自检通过 cwd 显式定位解压目录。
- 解压副本执行 `index-knowledge`：13 个来源、18 个向量点，unavailable 为空。创建缓存最初被执行沙箱拒绝，获准重试后成功。
- 47 项测试全部通过（13.545 秒），包含新打包边界回归；`refresh-index` 完成，`validate` 0 错误/0 警告。
- 新增 `portable.cmd`、`automation/scripts/portable.py` 与迁移指南；验证器排除根目录 tmp/dist，避免把迁移副本当控制平面重复审计。

范围：这是同一 Windows 主机的新路径验证，不冒充另一台电脑实测。接收端自检仍必要。运行时输出 FastEmbed mean pooling 提示为已有提示，未升级模型或依赖。旧查询中的绝对路径仅保留为历史，外部来源当前为空。
