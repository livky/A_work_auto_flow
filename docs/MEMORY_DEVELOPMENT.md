# 系统记忆：首批开发入口

> 本文保留首批开发阶段的范围与示例。当前工作台、检索、迁移及回执处理请使用 [版本记忆使用指南](MEMORY_USAGE.md)；最终验收状态见 [执行状态](design/system-memory/STATUS.md)。下文“尚未交付”等表述描述当时阶段，不代表当前功能清单。

> **历史定位，2026-09-09 核对：** 本页的 v1 契约、W06 尚未接入、首批请求与回执说明保持其当时含义，不能作为当前默认行为。现行记录默认 v3，L1 已扩展为技术单元，独立文稿使用 document/document_section，索引同步与补偿已接入；具体兼容条件和可执行请求见 [当前使用指南](MEMORY_USAGE.md)、[请求示例](MEMORY_REQUESTS.md) 与 [分层记录标准](RESEARCH_RECORDING.md)。当前模块职责见 [ARCHITECTURE.md](../ARCHITECTURE.md)，后续文档同步见 [维护约定](DOCUMENTATION_MAINTENANCE.md)。

2026-09-08 首批提供八类对象适配、草案预检、单对象版本保存、按 ID 读取和恢复检查。检索、正式复核、研究经过/续接、工作台页面和最终 AI Skill 尚未交付。这里是已实现 CLI 的开发用法；完整任务及后续顺序见[实施批次](design/system-memory/IMPLEMENTATION.md)。

## 对象、层级和版本

对象回答“记录属于哪项研究、Run、知识文档或其他业务材料”。一条记忆只有一个对象归属。已有 Run 仍保留 RUN 身份和专用字段，适配不会生成第二个等价 MEM-event。

本页原为首批开发说明；当前分层已扩展为L0原始来源、L1详细计算说明、L2事件与决策、L3有边界经验、L4主题地图。旧v1记录通过版本化投影读取，不修改历史哈希。问题、目标、路线、检查点、关联等是辅助记录，level为null。层级不是可信等级，保存成功不等于结论已复核；现行要求见[研究分层记录标准](RESEARCH_RECORDING.md)。

正文保存在每次修订的 JSON `body_markdown` 中。专属对象使用自身 `memory/`，平铺文档使用 `<完整文件名>.memory/`，工具使用 `tools/memory/<tool_id>/`。`owner.json` 保存稳定入口；`commits/` 保存不可变修订，`HEAD.json` 指向当前完整提交。调用者通过 CLI 修改，避免手工改正文和指纹。发现损坏时拒读并保留现场。

## 从已有材料开始

先查看已有对象，不创建空记忆：

```powershell
.\workbench.cmd memory --help
.\workbench.cmd memory list-owners
.\workbench.cmd memory inspect RES-实际研究ID
```

已有稳定 ID 的 Research、Run 等在首次有效提交时按需创建入口。没有稳定身份的知识文档必须先采用：用 `hash-file` 得到当前文件 SHA-256，再执行 `memory adopt-owner "knowledge/实际文档.md" --expected-hash "实际哈希" --actor "执行者ID"`。返回的 OBJ ID 此后保持稳定，原正文不变。手工移动文件会报告缺失；显式移动迁移服务属于后续 W11。

采用只登记入口，不会自动提取知识正文。AI 要将已有知识整理成经验时，先登记允许读取的来源，再提交正文、固定引用、适用与禁用条件；不知道的内容保留缺口。当前原文件引用只接受 `retrieval/sources.json` 中启用的逐文件登记 ID，不根据正文链接扩大授权。

## 保存、读取和修订

请求使用 UTF-8 JSON 文件。新操作生成新的 UUID；同一请求重试保留 UUID 和全部原参数。以下结构演示一条无实验依据的合成经验，使用前替换 request_id 和 owner_id：

```json
{
  "schema_version": 1,
  "request_id": "00000000-0000-4000-8000-000000000001",
  "actor": {"kind": "ai", "id": "开发验证"},
  "owner_id": "RES-实际研究ID",
  "expected_head": null,
  "operations": [{
    "op": "put_record",
    "client_key": "example",
    "draft": {
      "owner_id": "RES-实际研究ID",
      "kind": "experience",
      "title": "SYNTHETIC ONLY：前置条件经验",
      "body_markdown": "先核对条件，再决定是否复用。",
      "record_reason": "开发验证",
      "sources": [],
      "provenance_gap": "合成测试，无现实实验依据",
      "discovery": "owner_only",
      "sensitivity": "internal",
      "payload": {
        "problem_structure": "前置条件不同",
        "recommendation": "先核对条件",
        "applicable": ["此合成场景"],
        "prohibited": ["直接用于真实业务"],
        "failure_modes": [],
        "retry_conditions": ["取得实际输入"],
        "claim_refs": [],
        "claims": []
      }
    }
  }],
  "dry_run": false
}
```

```powershell
.\workbench.cmd memory validate-draft --request "request.json"
.\workbench.cmd memory commit --request "request.json"
.\workbench.cmd memory inspect RES-实际研究ID --record-id MEM-返回的ID
.\workbench.cmd memory inspect RES-实际研究ID --record-id MEM-返回的ID --revision 1
```

预检不创建目录、业务记录、回执或索引。新对象的 expected_head 为 null；后续请求必须提供 inspect 返回的 `head.commit_id`。修订操作用 `record_id`、`expected_revision` 替代 client_key，draft 提供完整新正文和 change_reason，不把 inspect 的服务端 ID、hash、时间字段复制进 draft。未改变内容的修订返回 no_change，旧提交不改写。

批次内引用新记录时可使用 `{"client_key":"example","relation":"derived_from","locator":"完整经验"}`，服务先解析整批再保存。正式引用固定记录 revision，旧对象/claim/文件固定 sha256。临时键不能跨批次使用；supports/input 自证环拒绝。

## 回执和故障处理

| 返回 | 意义与处理 |
|---|---|
| `save_status=committed`、`INDEX_PENDING`、退出码 3 | 内容已保存，W06 索引未接入；现在用 ID 读取。不能说尚未保存，也不能说已经可搜索 |
| `save_status=no_change` | 不创建正文修订，幂等轻量回执保留。当前索引仍 pending，退出码仍 3 |
| `VERSION_CONFLICT`、退出码 5 | 读取当前版本与草案比较，决定修订后以新请求提交 |
| `IDEMPOTENCY_CONFLICT`、退出码 5 | 同一 request_id 被用于不同内容；先查看原回执 |
| `LOCKED`、退出码 6 | 写入者活跃或身份不可判定，不能强删锁 |
| `INTEGRITY_ERROR`、退出码 7 | 指纹/结构损坏，保留现场，不重新计算 hash 掩盖损坏 |
| `STORAGE_ERROR`、退出码 8 | 检查 save_status、receipt 和 recovery_ref；HEAD 前失败未提交，HEAD 后失败可能已提交 |

```powershell
.\workbench.cmd memory recover RES-实际研究ID
.\workbench.cmd memory recover RES-实际研究ID --apply
```

默认仅检查。`--apply` 只在操作系统证明原进程退出时归档旧写锁并保存回执；不自动把孤立 commit 接到 HEAD，不递归删除 staging，也不覆盖新修改。随后用原请求重试，已提交的请求返回原身份。文件占用需先由持有者释放。进程中断回归不等于任意断电保证。

## 开发维护与升级

契约真源是 `automation/schemas/memory-v1.schema.json`，后端仅实现文档声明的标准库子集，未知关键字拒绝。类型用 `automation/scripts/memory/generate_types.py` 生成到 `automation/schemas/memory-v1.d.ts`；后续工作台再接入，不维护第二套领域规则。策略采用工作区→类型→对象→当前请求优先级；inspect 返回有效值及来源，保留显式 false。

源码发行清单包含新包、schema、类型和嵌套设计素材。共享扩展旧工作区 fixture 包含真实生成的记忆历史、旁目录、请求回执及故障现场。升级仍从独立新版目录执行 `setup.cmd --target "旧工作区" --register --open`，完成后继续使用旧目录。本批未改 Python 包锁或模型；现有匹配依赖包可沿用，无需新增逐包安装。

本批实际验证和剩余项以[执行状态](design/system-memory/STATUS.md)及其固定 Run 为准。完整离线模型链路、第二台物理机和 H01–H18 用户使用验收分别记录，不能以本批文件事务回归替代。
