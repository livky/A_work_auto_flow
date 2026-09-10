# 可选项目视图

项目用于临时交付、产品或工作任务的聚合，不拥有独立算法副本。通过 project.json 的 module_ids、active_research_ids 等引用全局对象；不建项目也可创建算法、研究和 Run。

新算法在根 `core-algorithms/`。项目自身计算用 `new-run --owner PRJ-ID` 保存在项目 `runs/`；研究、算法等对象的运行保存在各自运行目录，无归属轻量任务才使用根 `runs/`。旧根 Run 和 `projects/*/analysis/runs` 历史记录继续可检索与复核，不需要搬动原件或修改既有 ID。

项目默认采用与 Research 相同的分层记录：每轮实质设计、分析或开发保存 L0 依据、L1 技术单元和 L2 实际事件；阶段结束维护 L3 经验、L4 地图及完整/精简文稿。没有可推广经验时说明缺口，简单查字段不凑层。HEAD/提交历史由公共记忆服务维护，已有显式对象策略仍可覆盖默认值。

完整过程与精简报告使用独立 document/document_section 引用 L1 技术单元，L4 只维护主题结构；通过 `memory inspect PRJ-ID` 查看有效策略，用 validate-draft/commit 保存并以 document 回读。文件与完整命令见 [分层记录标准](../docs/RESEARCH_RECORDING.md)。项目实例属于具体工作数据，公共源码保留本目录规则与模板，实例按发行规则排除。
