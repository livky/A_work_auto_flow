# RUN-20260909T151004Z-A68FBA9F176D：按实现核对文档演进并建立模块影响图

## 问题、范围与依据

底层记忆与研究文稿已经合入 main，部分说明仍混用首版 L0–L3、旧 L1 实验说明、v2 map.report 和当前 v3 技术单元。本轮按代码校正文档，并建立后续开发必须检查的模块影响入口。成功标准是 docs 全量盘点、现行职责与代码一致、历史原文保留、Project 影响图与执行依据可回读。

代码基线为 `647d7862331e283439d06d42ec01d3882a32d163`，记忆实现集中引入于 `5e97aee8a03093124b95d294abaecfa36b1a2df8`。工作树包含本轮及进入任务前的未提交文档修改，不能视为该提交的纯净重放。登记的代码/schema 指纹及测试执行时的程序指纹固定实际输入。

核对范围包括全部 `docs/` 文件、根 README/AGENTS/ARCHITECTURE/context、33 个子目录介绍与规则、现行记忆/检索/证据/部署手册和五个工作流 Skill 源。原始数据、规范记忆、历史 Run、合成 fixture、可执行产品代码、依赖锁及前端资源不在本轮写入范围。`baseline/` 保留根入口和原 NOW 的修改前快照；文档盘点的初始指纹则是子任务开始读取的时点，两者不可混同。

## 方法与得到的修正

先读取 schema、contracts、Run/L0、技术单元、文稿、检索及入口实现，再分别核对文档中的能力、默认行为、日期和使用示例。时间线区分正文声明、Git 合入与本次读取时点，不根据文件修改时间推断开发顺序。

- 当前 L1 是实验、方法、推导或分析技术单元，检索说明与完整技术块分离；只有实验必须绑定固定 Run。
- 独立章节和文稿的 `level=null`；完整研究过程为 `research_process`，精简研究报告为 `research_report`。L4 仍是知识地图，v1/v2 保持兼容而不改旧字节。
- Run 优先存入实际归属对象，L0 汇总已登记输入/产物和固定来源。材料 Q/CTX 与记忆 QMEM/PKT 分开；知识、文稿、原始追溯模式各自说明默认边界。
- 更新 README、规则、现行手册、导航与 Skill；26 份历史文件只加时点提示。按初次盘点指纹验证历史正文仍保持原字节，20 个 fixture 文件未变。
- 建立八个功能分组的[现行模块影响图](../../context/MODULE_IMPACT.md)和[本轮影响处置](IMPACT_REVIEW.md)。后续按“需修改 / 已检查无需修改 / 延期及理由”记录影响；职责或接口变化时更新图，并在新 Run 固定快照。

本次统计：`docs/` 共 74 个文件，其中 58 份 Markdown；分类为当前手册 18、历史设计 21、验收记录 6、合成 fixture 20、模板 9。子目录入口和检索相关手册共核对 39 个，修改 23 个，16 个有依据地保持不变。详细范围见下面的检查回执。

## 产物与检查入口

| 产物 | 用途 |
|---|---|
| [文档时间线](../../docs/DOCUMENT_HISTORY.md)、[盘点数据](../../docs/document-inventory.json) | 当前 Project 的历史导航与本次读取指纹 |
| `artifacts/MODULE_IMPACT-v1.md.snapshot` | 本轮影响图固定快照；现行图以后可以继续演进 |
| `artifacts/DOCUMENT_HISTORY.md.snapshot`、`artifacts/document-inventory.json` | 本轮时间线与完整盘点的固定证据 |
| [记忆与部署检查](review-memory-docs.md) | 14 份文件，32 段 JSON、5 段 Python、三类 v3 草案和提交封套校验，107 个本地链接及发行边界核对 |
| [导航与检索检查](review-navigation-docs.md) | 39 个文件覆盖，72 个本地链接、3 个锚点及实际实现核对 |
| `review-document-history.md` | 时间线、原文保护与既有 fixture 缺口检查 |
| [quick 实际回执](testing/attempt-01/README.md) | 软件测试实际执行、未执行及程序指纹 |
| `doc-checks-final.json`、`workspace-validation.txt`、`git-diff-check.txt` | 最终本地链接、docs 覆盖/指纹、代码边界、结构与格式检查 |
| [审查入口](REVIEW.md) | 文档自查结论和人工待审项；不冒充实际 AI 行为验收 |

最终检查脚本为 [verify_documents.py](verify_documents.py)，只读源文件并写指定结果回执；不是新增产品功能。复跑命令：

```powershell
.\automation\python.ps1 projects/architecture-evolution/runs/run-20260909t151004z-a68fba9f176d/verify_documents.py --out .local/document-review-recheck.json
.\automation\workspace.ps1 refresh-index
.\automation\workspace.ps1 validate
```

脚本针对本次工作树与最终盘点，后续开发修改文档后会如实报告指纹变化；应在新 Run 建立新盘点，不覆盖本轮证据。第一次文档检查在并行修改期间运行，发现 9 份尚未刷新指纹及新派生 run-index；原回执保留，最终回执在盘点更新和明确派生索引例外后重新生成。

## 验证结果与限制

开发前 testing audit 和冻结选择校验通过。quick 中 12/12 个 Python 检查通过，包含真实 Windows `setup.cmd` 扩展旧工作区升级与恢复；另 12 个前端检查因缺 `frontend-dev` 未执行，quick 整体为 **incomplete**。未缩减选择制造通过，未为文档修改安装额外开发依赖。

当前文件可定位、代码入口及登记回读由本 Run 的最终回执说明。历史 fixture 清单中 `acceptance.json`、`records.json`、`work-packages.json` 存在三个既有指纹差异，文件与本轮开始读取及 Git HEAD 同字节，成因未确认；没有重写清单或将它们算作通过。

本 Run 的执行完成只表示文档整理和记录完成，不表示全部软件测试、真实 AI 行为、人工审查、检索质量、业务有效性、离线发行或第二台物理机验收通过。人工复核状态保持 `not-reviewed`。

下一轮优先围绕接口依赖、状态所有权和检索效能固定问题与负例；图联想、统一查询契约、有界召回和重排仍是待比较方案。本轮没有实现这些性能或架构改造。
