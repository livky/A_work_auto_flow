# 记忆与部署文档：代码对照检查回执

记录时间：2026-09-09T15:27:12Z。归属 Run：`RUN-20260909T151004Z-A68FBA9F176D`。检查者：Codex 文档核对代理（AI）。本回执保存本轮已实际完成的静态检查和只读核对；没有重复运行历史实验，也不是实际 AI 行为测试或人工验收。

## 范围与结果

检查限定为下列 14 个已修改文件。按当前 main 代码和工作区未提交文档核对默认记录版本、L1 技术单元、独立章节/双文稿、检索模式、Run/L0 归属、安装/迁移和公共发行边界。最终未发现该范围内新增的现行定义冲突；此结论不覆盖其他文件或未登记关系。

`RESEARCH_RECORDING.md` 原先有一句将所有 L1 都描述成 Run 说明。根代理已将第 29 行限定为“实验类 L1”，并说明方法、推导和分析按实际依据保存；本次只读回看确认已落盘，未再次编辑该文件。`MEMORY_DEVELOPMENT.md` 保留首批 v1/W06 历史原文，通过明显的历史定位和当前入口区分，不将其旧状态作为现行行为。

## 实际执行的检查

| 检查 | 实际方式 | 结果与限制 |
|---|---|---|
| 文档与实现对照 | 阅读 v3 schema、contracts、technical_units、documents、search、policy/service，以及部署/portable、共享升级 fixture、工作台调用入口 | 已核对；默认 v3 与旧形状 v2 兼容、固定文稿与块依赖、字符预算、策略入口均按代码描述 |
| JSON 示例语法 | 用工作区 Python 3.12.10、`-B`，从六份记忆/Run 文档提取 JSON 代码块并运行 `json.loads` | 32 段通过；只证明示例语法，不证明占位身份或业务依据真实 |
| Python 示例语法 | 同一只读检查用 `ast.parse` 解析 Python 代码块 | 5 段通过 |
| 新草案契约 | 以隔离内存中的合成固定引用，校验文档新增的 detail、document_section、document 草案，并校验首个 CommitRequest | 三类草案和提交封套通过当前纯契约校验；没有提交规范记录或执行实验 |
| 相对文件链接 | 排除代码围栏和外部 URL，检查相对链接目标文件存在 | 记忆/Skill 88 个、部署 19 个，共 107 个目标存在；未检查外网内容及所有 Markdown 锚点 |
| 框架升级清单 | 只读调用 `deployment.framework_files` | 四份部署手册及 `docs/DOCUMENTATION_MAINTENANCE.md` 在清单中；项目实例不在升级清单中 |
| 发行排除属性 | `git check-attr export-ignore` 检查目录和通用手册 | `projects/architecture-evolution` 为 set；项目模板和 README 为 unset；通用维护手册无排除属性。检查的是目录规则，没有生成或上传发行 ZIP |
| 差异格式 | 对所负责文件运行 `git diff --check` | 通过；Git 提示未来检出可能按 autocrlf 转换换行，无空白错误 |
| 最终只读回看 | 对 14 文件定向检索旧默认/旧编排/归属/发行边界表述，并回读根代理修订的 L1 定义 | 未发现其他现行定义冲突；最后记录各文件实际 SHA-256 |

以上示例、链接、清单和差异检查在本轮前序阶段已执行，本回执复用其真实结果。最后阶段只做定向回看与输入指纹记录，没有将重复执行次数当作独立证据。

代码核对入口：`automation/scripts/memory/contracts.py:336`、`technical_units.py:76`、`documents.py:46`、`documents.py:226`、`documents.py:291`、`documents.py:424`、`search.py:119`、`service.py:50`、`automation/scripts/deployment.py:34`、`portable.py:20`、`automation/tests/upgrade_fixture.py:186` 和 `:297`。这些行号对应下述代码提交；工作区文档另以固定哈希识别。

## 未执行与未确认

- 未开展实际 AI 按 Skill 完成任务的行为测试、用户人工阅读验收或 GUI 视觉检查。
- 本代理未运行新的完整单元测试、真实 setup 安装/升级/恢复、离线模型链路或接收端再次打包；如主 Run 另有执行，应引用其独立回执。
- 未验证第二台物理机、不同硬件、企业环境、真实业务材料、检索质量或万条规模性能。
- 未重跑历史研究实验、恢复未分发的历史 Run 或重新确认业务结论。
- 未生成最终发行 ZIP、创建 Release、上传或外发材料；发行属性/清单检查不代替实际包内容核验。

## 机器可读摘要与输入指纹

路径相对于工作区根目录。指纹固定本次只读核对时的文档字节；后续任何编辑需作为新时点登记，不改写本回执表示其也已核对。

```json
{
  "schema_version": 1,
  "run_id": "RUN-20260909T151004Z-A68FBA9F176D",
  "recorded_at": "2026-09-09T15:27:12Z",
  "reviewer": {"kind": "ai", "id": "codex-memory-docs-review"},
  "review_type": "source_and_document_inspection",
  "code_commit": "647d7862331e283439d06d42ec01d3882a32d163",
  "working_tree_dirty": true,
  "documentation_result": "no_additional_conflict_found_in_scope",
  "scope_file_count": 14,
  "json_examples_parsed": 32,
  "python_examples_parsed": 5,
  "v3_draft_contracts_passed": ["detail", "document_section", "document"],
  "commit_request_contract_passed": true,
  "relative_file_links_checked": 107,
  "missing_relative_file_links": 0,
  "maintenance_doc_in_upgrade_files": true,
  "project_instance_excluded_from_upgrade_files": true,
  "diff_check_passed": true,
  "prior_checks_reused": true,
  "actual_ai_behavior_test": "not_performed",
  "human_review": "pending",
  "second_physical_machine_validation": "not_performed",
  "release_archive_generated": false,
  "open_findings": [],
  "files": [
    {"path":"docs/MEMORY_USAGE.md","sha256":"926698a1f7f08fdbaa0cdf4f71e60d1aec324871a19ff0c98be991003a60b0f2"},
    {"path":"docs/MEMORY_REQUESTS.md","sha256":"991a7785ffa7053616337ce132de6ca8a19c50b2c9aad5043722b4e59b0c9356"},
    {"path":"docs/RESEARCH_RECORDING.md","sha256":"80c879388179277aad4e9d2f111f439c5961df5185d3f3e3ef11957fe5d1038f"},
    {"path":"docs/MEMORY_DEVELOPMENT.md","sha256":"eba2723fca10fc57e870ba09dec5778e0326e386fe5e70e15157dd9547e20f6d"},
    {"path":"docs/OBJECT_RUN_STORAGE.md","sha256":"ee8560c8447efb47204beee15d72658b7274214626c030215e02ac4ea201cfc0"},
    {"path":"docs/RUN_CAPTURE.md","sha256":"c78fa6538e8f5e1c8b3b547a5a6701d931ef7a68dfb0570f8b705fbb2bf39e43"},
    {"path":"docs/SETUP_WORKBENCH.md","sha256":"8407e4edae092a081b2dd680ec08f0d05483c575830d95479f3628c21c468ac8"},
    {"path":"docs/WINDOWS_PORTABILITY.md","sha256":"6e05924cc601d84d280c9425b3bc767cbce86bcb7fdb5d0ed7caaf127b0fd953"},
    {"path":"docs/DEPENDENCY_RELEASE.md","sha256":"5420648bc3b36f1ceff8de555b807c23dc13625bdd87c7b0a2084e9d0129234f"},
    {"path":"docs/UPGRADE_TESTING.md","sha256":"cfd47dd0a0a32bc143488f4ed3b4378085756cfe6fa1696f0a2c4c2f7b602008"},
    {"path":"automation/workflows/workspace-context/SKILL.md","sha256":"6d47a30225fb598706563a372216285683655efa2a40dcfc32a58b708c7b65f5"},
    {"path":"automation/workflows/context-maintenance/SKILL.md","sha256":"480676c1114422ebaa6029ca16d86f49e40d300eb23157ffaf74f994a7dd694b"},
    {"path":"automation/workflows/research-loop/SKILL.md","sha256":"9b9bb0b8a571f48d46554dfc013f5cb15c67b41105a3c9f1fe8d019294cf9ab3"},
    {"path":"automation/workflows/evidence-inspection/SKILL.md","sha256":"aceeb3333ac168a2d23768c554fb864e2689f83ecff4932d6ab1e01c93d6e43a"}
  ]
}
```
