# 可选项目视图规则

project.json、README 和 context/MODULE_MAP.md 组织目标、里程碑及全局核心算法/研究/Run 引用，不复制对象正文。项目局部 AGENTS 只补本目标的约束。

Project用于系统级或大型工作；通用核心算法与独立研究可继续在根目录管理并由项目引用。项目直接开展的计算用 `new-run --owner PRJ-ID` 保存到项目内 runs/；研究、算法等对象的计算保存在各自 runs/，根 runs/作为无归属轻量任务的默认目录。不为创建 Run 建空项目，不复制跨对象共用的 Run。旧项目布局和旧根Run保持兼容、保留原ID及历史。

所有 Project 默认按[研究分层记录标准](../docs/RESEARCH_RECORDING.md)保存实质工作，不停留于 Run/L0：每轮维护 L1 完整技术单元与 L2 事件/决策，阶段结束维护 L3/L4、独立章节和完整/精简文稿。父项目引用其他对象的固定单元，不复制其正文。历史补写注明真实整理时间；没有可推广经验时保留缺口，不虚构结论。简单查阅无需凑层，显式策略覆盖仍有效。

保存使用公共 memory validate-draft/commit，再 inspect/document 回读。默认策略只指导记录，不启动后台总结，也不自动接受结论。

变更时更新实际影响的引用和状态，复核/纠错遵循 context/MEMORY.md，结构性变更后刷新索引与 validate。
