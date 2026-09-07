# 核心算法

只收录公司算法/模块文档定义的关键模型算法，具体准入与排除条件见 [目录规则](AGENTS.md)。每项保存于 core-algorithms/<slug>/，可被多个研究、Run 和工作任务引用。运行 `new-core-algorithm <slug> --title "名称" --source-document "公司文档名称或编号"` 创建；ID 不携带项目归属。来源只登记，不自动读取或标记已验证。

new-module 保留为兼容命令，执行相同的文档来源检查。module.json、MOD-ID、--module 和 module_ids 等机器字段继续使用，但含义仅限核心算法。旧 modules 目录已迁移；外部旧路径引用需改为 core-algorithms 后重建索引，历史快照不重写。

核心算法代码可在核心算法内 code/，也可保留在原仓库。文档和代码通过 retrieval/sources.json 的 module_ids/related 关联；核心算法之间也可用 related_module_ids 表达关系。

创建只生成 module.json 与 README 两个入口。需要深入设计时参考 [详细核心算法卡](../docs/templates/CORE_ALGORITHM_CARD_TEMPLATE.md) 和 [接口契约](../docs/templates/INTERFACE_CONTRACT_TEMPLATE.md)，按需合并到核心算法，不重复维护摘要。
