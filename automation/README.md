# 工作区自动化

核心 CLI 创建全局核心算法、Run 与可选项目；检索使用 SQLite FTS5 + 已安装的本地 Qdrant/FastEmbed，多格式解析与 OCR 只读取配置范围和显式登记文件。上下文新增 focus/investigate/wide 选择与 context-feedback 扩展；检索命令、反馈闭环和来源登记详见 [检索手册](../docs/RETRIEVAL.md)。

`workflows/` 保存方法正文，常用 workspace-context 和 context-maintenance 已在 .agents/skills 安装轻量入口；其他流程按需读源。安装器默认预览，--apply 新建入口，不覆盖不同的已有技能。

## 命令

```powershell
# 检查目录、JSON、链接、疑似秘密和大文件。
.\automation\workspace.ps1 validate

# 从模板创建对象；默认拒绝覆盖。
.\automation\workspace.ps1 new-project <slug> --title "项目名"
.\automation\workspace.ps1 new-research <slug> --title "研究问题"
.\automation\workspace.ps1 new-run --title "分析目的"
.\automation\workspace.ps1 new-run --title "中文标题" --keyword "温漂"
.\automation\workspace.ps1 search-runs "温漂" --project <slug> --limit 10
.\automation\workspace.ps1 review-run RUN-ID --status disputed --reviewer "用户" --reason "发现新反证"

# 派生索引与任务上下文。
.\automation\workspace.ps1 refresh-index
.\automation\workspace.ps1 build-context --project <slug> --task "任务描述"

# 先预览会发生什么。
.\automation\workspace.ps1 new-project <slug> --title "项目名" --dry-run
```

需要直接运行 Python 核心算法或测试时，使用解释器发现包装：

```powershell
.\automation\python.ps1 -m unittest discover -s automation/tests -v
```

## 自动化边界

- `search-runs` 即时读取 Run 源元数据并计算已登记依赖影响；关键词由 AI/用户填写，不自动调用模型提词。
- `review-run` 原子保存复核前后历史；accepted 要求 evidence/scope，superseded 要求 replacement。命令不认证证据与身份；同一 Run 的复核应串行执行。
- `refresh-index` 另生成 `run-index.json`，主导航只放最近 20 项。修改复核后先刷新再共享快照；旧上下文不会自动更新。
- `context/generated/` 是派生视图，可随时重建，不能覆盖人工事实源。
- 创建命令不会覆盖现有对象。
- `build-context` 只加载配置允许的导航层和显式核心算法/项目/研究入口，不扫描共享盘或大产物。
- `validate` 的警告不代表公司级合规审计通过；它只是尽早发现结构性错误。

## 推荐节奏

- 每次结构性变更：`refresh-index` + `validate`。
- 复杂任务：维护计划；产生独立分析证据时建 Run，结束时保存必要记录，满足复核条件才晋升知识。
- 每周：整理 `inbox/`、检查 open Run 和未决行动。
- 每月：填写 `knowledge/reviews/REVIEW_TEMPLATE.md` 的实例，评估文档漂移和自动化机会。

当前已启用 SQLite FTS5 与本地 Qdrant 混合召回，依赖和模型位于 services/qdrant/。其他平台按真实案例需求选择，保留现有业务对象 ID 与开放文件格式。

核心算法导航使用 `build-context --module <slug>`，这里接收目录短名；语义材料问答用 `retrieve-context --module MOD-ID`，这里接收稳定 ID。
