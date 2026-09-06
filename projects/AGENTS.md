# 可选项目视图规则

project.json、README 和 context/MODULE_MAP.md 组织目标、里程碑及全局核心算法/研究/Run 引用，不复制对象正文。项目局部 AGENTS 只补本目标的约束。

新核心算法在根 core-algorithms/，新分析记录在根 runs/，研究在根 research/。不为创建 Run 而创建空项目。旧项目内对象保留来源、ID 和历史，CLI 兼容旧 Run；新增工作使用全局布局。

变更时更新实际影响的引用和状态，复核/纠错遵循 context/MEMORY.md，结构性变更后刷新索引与 validate。
