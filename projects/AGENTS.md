# 可选项目视图规则

project.json、README 和 context/MODULE_MAP.md 组织目标、里程碑及全局核心算法/研究/Run 引用，不复制对象正文。项目局部 AGENTS 只补本目标的约束。

Project用于系统级或大型工作；通用核心算法与独立研究可继续在根目录管理并由项目引用。项目直接开展的计算用 `new-run --owner PRJ-ID` 保存到项目内 runs/；研究、算法等对象的计算保存在各自 runs/，根 runs/作为无归属轻量任务的默认目录。不为创建 Run 建空项目，不复制跨对象共用的 Run。旧项目布局和旧根Run保持兼容、保留原ID及历史。

各类Owner默认使用work-loop，按有用内容保存L0依据、L1方法/分析、L2有依据的经过、L3可复用认识及L4概览。允许缺层，文稿按阅读和交付需要编排；不为每轮凑记录或强制双文稿。固定引用复用原件，来源主张、AI推断与本次验证明确区分。已有显式对象策略保留。

保存使用公共 memory validate-draft/commit，再 inspect/document 回读。默认策略只指导记录，不启动后台总结，也不自动接受结论。

变更时更新实际影响的引用和状态，复核/纠错遵循 context/MEMORY.md，结构性变更后刷新索引与 validate。
