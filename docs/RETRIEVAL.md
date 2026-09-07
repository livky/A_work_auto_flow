# 检索、上下文选择与反馈手册

正式结论导出新增 `retrieve-context --purpose formal --scope "适用范围"`，只装载通过版本/复核/依赖检查的结论，purpose/scope 在扩展链保持。默认 exploration 继续读取原材料并显示跨文档风险。详细格式、复核与封存入口见 [证据准入手册](EVIDENCE_CONTROLS.md)。

检索找候选，上下文策略决定实际读多少。原理和概念见 [README 附录](../README.md#附录检索和向量化到底怎样工作)；本页集中说明命令、配置与恢复。

## 常用操作

```powershell
# 预览范围，不读取正文或创建索引。
.\automation\workspace.ps1 index-knowledge --dry-run
# 更新获准来源的正文/向量，原文件不改动。
.\automation\workspace.ps1 index-knowledge
# 只查看候选。
.\automation\workspace.ps1 search-knowledge "时间对齐 低采样率" --module MOD-ALIGNMENT
# 创建第一阶段证据包，返回 CTX-ID、Q-ID、context_path、manifest_path。
.\automation\workspace.ps1 retrieve-context "时间对齐为什么失败" --module MOD-ALIGNMENT
```

ID 和文件名是示例，不代表已存在业务对象。不确定核心算法时省略 --module，由候选关联推断有限数量的目标核心算法，再由 AI 核对。核心算法不要求属于项目；--project 仅在确需限制可选项目时使用。

读取返回的 Markdown 和 manifest。算法问答可用 `$workspace-context`；普通创建操作不必每次调用技能。`search-runs` 是 Run 元数据 AND 检索，`build-context` 是规则/导航快照，两者不替代材料检索。

## 分阶段装载

| 设置 | focus | investigate | wide |
|---|---:|---:|---:|
| 直接检索候选上限 | 6 | 14 | 24 |
| 关联扩展跳数 | 1 | 1 | 2 |
| 非必读/非用户指定材料数 | 5 | 12 | 22 |
| 单个片段字符上限 | 1800 | 3600 | 6000 |

默认总证据预算 60000 字符，三个阶段使用同一预算。可用 --budget-chars 调整；它不是客户端剩余 token，也不知道何时触发聊天压缩。--limit 可覆盖当前查询的直接候选数；下一阶段按其配置扩大。

- 目标核心算法中的算法文档，或明确 context_role=algorithm 且关联该核心算法的来源，先请求全文。核心算法 ID 已指定但没有算法文档时，manifest.module_algorithm_missing 报告缺失。
- 其他来源按角色和长度决定全文或片段。首轮全文阈值：核心代码 3500 字符、应用代码 1600、Run 4500、Research 3500、Knowledge 4500、Project 1600、普通文档 3500。后两阶段分别乘 2、3。阈值可配置，仍受总预算限制。
- 长 Python 代码能够定位命中函数时，能容纳就读整个函数；否则片段且标记 code_unit_complete=false。其他语言暂不保证函数边界。
- 长 run.json 首轮用 brief 选择原始字段，不生成新的摘要结论；字段可能截断，原件和风险提示始终可追溯。后续可用 --full 定向展开参数/日志。
- 应用代码和项目安排首轮要有正文命中或用户指定才加入；仅路径含核心算法名不够。相关核心实现优先保留用于核对文档，不把文档视为绝对正确。
- 多格式材料默认片段，format_context 可覆盖；页/幻灯片/表格行范围与图像资产在 manifest。无文字图表需打开原件。

候选预览最多 40 项，完整清单在 candidate_inventory_path；先读预览，避免大核心算法的文件清单占满上下文。manifest.candidates 给出候选角色、原文长度、选入/延后/排除原因；sources 给出实际 full/brief/excerpt/omitted、指纹、位置与 Run 风险。required_not_full 非空表示有算法基线未全文装载，包括用户排除和预算不足，必须明确说明。候选清单不代表全部已读。

## 用户选择与自动扩展

```powershell
# 路径可以换成已检索的 SRC-ID。include 保证参与选择，full 请求全文。
.\automation\workspace.ps1 retrieve-context "问题" --module MOD-ALIGNMENT --include "core-algorithms/alignment/code/core.py" --full "runs/RUN目录/run.json" --exclude "core-algorithms/alignment/apps/ui.py"
# 记录真实缺口后，自动进入下一阶段，并继承预算与选择。
.\automation\workspace.ps1 context-feedback CTX-ID --outcome unresolved --actor assistant-observation --note "缺少调用方的时间戳定义"
# 冲突时可细化问题或指定来源；本次明确选择可推翻前次选择。
.\automation\workspace.ps1 context-feedback CTX-ID --outcome conflict --actor assistant-observation --note "文档与实现采样假设不同" --query "align_signal 时间戳与调用参数"
# 只有用户明确作出评价时才用 actor=user。
.\automation\workspace.ps1 context-feedback CTX-ID --outcome solved --actor user --note "已找到需要核对的版本差异"
```

“未解决/冲突”由 AI 或用户根据实际证据判断，程序不运行回答模型或判定答案质量。根规则和常用 Skill 要求 AI 在任务中主动触发扩展，而非重复索要是否继续检索的确认。

两次自动扩展后停止。wide 阶段解除核心算法/项目过滤，仍只访问已获准索引，不自动增加预算或解除排除项。达到上限应报告缺口或给出更具体的输入要求；用户明确选择新范围时可新建 retrieve-context --stage wide 调查。旧包无法从聊天中自动移除，后续优先补新增/变化证据。

优先级：当前明确选择覆盖持久偏好；排除项不装载；算法基线与 --full 请求全文；其余依次应用显式 --context-mode、来源 context_mode、角色/长度和格式策略。同一命令同时加入并排除同一来源会报错。任何全文请求都受预算限制。

选择仅接受已经登记并成功索引的来源，不能用 --include 绕过来源登记。未知的持久偏好在 missing_preferences 中报告。正文变化后新阶段读当前版本，旧 CTX/Q 仍保留原指纹。

## 持久偏好与来源角色

retrieval/context-policy.json 管理阶段和阅读偏好。例如只在该核心算法下默认排除应用代码：

```json
{"preferences": {"global": {"include": [], "full": [], "exclude": []},
  "modules": {"MOD-ALIGNMENT": {"exclude_roles": ["application-code"]}}}}
```

这是配置片段，合并到已有文件，不要覆盖其他配置。长期偏好应来自用户明确要求，AI 在 retrieval/strategies 保存修改前后内容和原因；不能把一次相关性反馈自动升级为全局排除规则。

retrieval/sources.json 逐文件登记原位外部来源或补充元数据：

```json
{"schema_version": 1, "sources": [
  {"path": "core-algorithms/alignment/code/core.py", "title": "时间对齐核心实现",
   "module_ids": ["MOD-ALIGNMENT"], "context_role": "core-code",
   "keywords": ["对时", "alignment", "时间戳"], "version": "commit-or-file-version",
   "consistency": "mismatch", "related": ["core-algorithms/alignment/README.md"]}
]}
```

path/related 以工作区根为基准，也接受绝对文件路径。related 只连接已索引来源，不授权读取新文件。可用 enabled=false 停止召回，原件和历史保留。context_mode 可设 full/excerpt；角色为 algorithm、core-code、application-code、run、research、knowledge、project、media、document。角色不确定时不伪装成确定判断；路径推断只是默认值。

核心算法仅指公司文档定义的关键模型算法/测校项。普通代码默认 application-code；已关联算法的 core-algorithms/<slug>/code 内实现默认 core-code，apps、ui、tests、utils 等辅助目录仍按应用代码处理。算法卡 README 和 docs/algorithm 下的说明可作为算法基线，目录规则及辅助 README 不自动充当算法说明。原位文档/代码通过显式 context_role 指定角色，必须有文档—实现映射依据；module_ids 只表达关联，不将工具变成算法对象。preferences.modules、--module 和 MOD-ID 保留兼容名称，语义均为核心算法。

核心算法 aliases、Run keywords、来源 keywords 用于词项索引和限长嵌入前缀。AI 在整理任务中补业务关键词；CLI 自动分词不等于自动理解。文档/实现一致性由 AI/验证流程核对，consistency=mismatch 只提示候选优先复查，不自动撤回结论。

## 格式、范围与版本

| 格式 | 提取内容和位置 | 限制 |
|---|---|---|
| 文本/代码/JSON/LaTeX | 正文和字符范围 | 默认 UTF-8 |
| DOCX | 正文 | 复杂公式、布局、图片可能缺失 |
| PPTX | 按播放顺序的页文字、备注、图表缓存文字、图片 OCR/替代文字 | 不解释图形关系、不执行宏 |
| PDF | 页文字、可提取图片 OCR | 矢量图/特殊字体/公式可能缺失，需核对原页 |
| PNG/JPG/JPEG/BMP/WebP | 本地 OCR 与资产路径 | 无文字图形缺少语义召回，需补说明或视觉核对 |
| CSV/XLSX | 每 40 行一段；XLSX 表名/行号/单元格及缓存公式值 | 不执行公式、解释日期或图表，旧 PPT/XLS 需转换 |

默认 10000 个来源、每文件 50 MiB；每份最多 40 个视觉资产，图片缩至 2000×2000 内用于 OCR。超限/失败留原因；默认跳过的格式需对照导入清单检查。默认扫描配置内业务目录；inbox、archive、generated、模板和运行时不自动进入检索。

来源 ID 由规范化绝对路径派生，内容用 SHA-256 标识。查询前刷新，装载前再检查；缺失/禁用/损坏来源停止旧内容召回。保留历史指纹和查询，不保留完整旧原文快照，也不会自动决定并存版本哪个正确。旧 Run 复用前检查输入、适用域和复核状态，正常升级不意味着旧结论错误。

## 反馈与评估

context-feedback 保存一次调查是否解决及缺口；retrieval-feedback 保存单份来源是否相关、漏检或版本错误。两者互不替代，不改变 Run 复核状态，也不自动训练模型。

```powershell
.\automation\workspace.ps1 retrieval-feedback Q-ID SRC-ID --label relevant --actor assistant-observation --note "提供了实现入口"
.\automation\workspace.ps1 retrieval-feedback Q-ID "待登记路径" --label missing --actor assistant-observation --note "应查但未索引"
.\automation\workspace.ps1 retrieval-feedback-report
.\automation\workspace.ps1 retrieval-alias "对时" --alias "时间对齐" --alias "alignment" --dry-run
.\automation\workspace.ps1 evaluate-retrieval
```

单份反馈标签：relevant、irrelevant、missing、wrong-version、useful、correction。汇总同时显示上下文 solved/unresolved/conflict 事件；actor 保留实际贡献者，AI 不能伪造人工确认。

在 retrieval/eval.json 填真实问题与预期来源：

```json
{"schema_version": 1, "cases": [
  {"query": "低采样率下如何对齐？", "module": "MOD-ALIGNMENT", "expected": ["core-algorithms/alignment/README.md"]}
]}
```

评估输出文件级 Recall@K 和 MRR，空集返回 unavailable，不伪报满分。评估不写真实查询日志。它尚不衡量答案正确率、版本正确率或上下文是否充分；需结合调查反馈和人工/适用验证，保留未用于调参的问题。

## 文件维护与离线恢复

| 位置 | 内容 | 是否可当缓存清理 |
|---|---|---|
| config.json、context-policy.json、sources.json、eval.json | 检索/上下文策略、来源、真实评估集 | 否 |
| generated/ | SQLite、提取资产、证据包 | 可重建，但旧包精确复现需保留原版本 |
| queries/、feedback/、sessions/、context-feedback/、strategies/ | Q 查询、单源反馈、CTX 调查、扩展反馈、策略历史 | 否，按获批方式备份 |
| services/qdrant/storage/ | Qdrant local 向量库 | 可重建，先关闭检索进程 |
| services/qdrant/runtime/、models/、wheelhouse/、downloads/ | 便携解释器、模型与离线恢复包 | 离线搬迁需要完整复制 |

已装 Python 3.12.10 Windows x64、Qdrant client 1.19.0、FastEmbed 0.8.0、多语言 MiniLM 384 维、pypdf 6.17.0、RapidOCR 1.4.4。模型文件加载时校验 SHA-256，集合身份包含模型清单及编码库版本；升级产生新集合，旧集合不自动删除。

```powershell
.\automation\python.ps1 services/qdrant/install.py
.\automation\python.ps1 services/qdrant/install.py --apply --offline
.\automation\python.ps1 -m unittest discover -s automation/tests -v
```

正常推理强制离线；缺模型会报错，不自动下载。install.py 默认预览，--apply 才写入；离线恢复按 requirements.lock.txt 和缓存安装，先验证 checksums.json。download_model.py --apply 只在安装阶段下载公开模型。

本实现使用官方 Python Qdrant local，无 Docker/HTTP 服务、单库串行访问；未验收大型语料性能。复制工作区时需包含 Git 忽略的运行时/模型，迁移源路径后重建索引。首次安装需要 Python+pip 引导；若便携 python.exe 缺失，可从保存的 Python 安装包恢复再运行安装器。

config.json 的 vector_store.provider=null 可只用 FTS；ocr_enabled 控制 OCR，format_context 控制多格式默认阅读，context_chars 是证据预算。分阶段阅读设置集中在 context-policy.json，旧 vector_context_mode 已从当前 CLI 配置移除，避免与角色策略冲突。
