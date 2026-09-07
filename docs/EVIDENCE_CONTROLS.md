# 结论准入、依赖失效与当前环境检查

本功能将记录完整性、逐结论复核和正式证据导出接到现有 CLI。它不代替领域验证，也不限制有写权限的外部编辑器。旧记录仍可探索检索；正式使用需要补齐证据。

如需直接查看依据、复核历史、失效观察时间及报告影响，使用 [证据工作台与只读监测](EVIDENCE_VIEW_MONITOR.md)。查看和提出维护候选不会自动改变复核状态。

## 先确认当前副本能力

```powershell
.\automation\workspace.ps1 doctor
.\automation\workspace.ps1 doctor --require fts --require vector --require ocr
.\automation\workspace.ps1 verify --profile core
.\automation\workspace.ps1 verify --profile full
```

doctor 默认只报告；组件为 ready/unavailable/unverified，未要求任何组件时退出 0 表示诊断已完成，不表示全部可用。require 会在能力未达 ready 时退出 1；vector/OCR 在依赖齐备时使用实际离线探针。FTS 使用内存数据库，向量使用临时库，不改业务索引。portable 与 business-eval 需要专门迁移/领域验收，doctor 不凭文件存在宣称通过。

verify 的 core 运行结构/FTS 检查和现有测试，允许因缺模型跳过的测试，但状态明确为 passed-with-skips；full 额外要求向量/OCR 实测，且任何 skipped 均不能算通过。测试子进程有 60 秒上限，超时显示不可用，不冒充通过。full 指本仓库集成验证，不是公司算法有效性验收。

## 在现有对象中记录结论

Run 的 run.json、研究的 research.json、算法的 module.json 支持可选 claims 和 dependencies。新模板提供空数组。每条 claim 使用 [结论模板](templates/CLAIM_TEMPLATE.json)，包含 CLM-ID、statement、kind（fact/calculation/inference/recommendation）、scope、evidence_refs、review 和 review_history。

scope 是人工确定的适用范围标识，正式使用精确匹配。程序不推断工况等价；需要多个范围时分别登记和复核，不能随意扩展。

普通知识/ADR 和报告源使用 [逐文档证据模板](templates/EVIDENCE_TEMPLATE.json)，保存为 knowledge/ 下或 reports/sources、reports/manifests 下的 `名称.evidence.json`。evidence_id 使用 EVD-ID，document_path 是工作区相对文件路径。此旁文件只声明一个文档；不复制正文。元数据中的依赖不自动把文件加入检索读取授权。

引用格式：

```json
{
  "target": "RUN-EXAMPLE",
  "relation": "supports",
  "sha256": "填写目标当前的64位内容指纹",
  "locator": "conclusion / 具体结论或产物位置"
}
```

target 可以是 RUN/CLM/RES/MOD/EVD-ID，或工作区相对文件路径。外部文件必须已在 retrieval/sources.json 逐文件启用登记；不会根据网页 URL 或 Markdown 链接自动读取外部文件。输入/产物为文件引用时使用 path 和 sha256；路径均相对工作区根，避免和历史 Run 内相对路径约定混淆。

- `supports`、`input`：固定版本和定位，传播缺失、撤回、版本变化、循环和失效。
- `background`、`contradicts`：保留背景/反证关系，不继承原结论的失效。
- 消费整个对象会检查其结论；只依赖其中一条结论时优先引用 CLM-ID，避免过宽依赖。
- 未声明关系的旧 Markdown 若链接到失效对象，显示 unclassified-reference，提醒补充关系类型；不伪称已识别科学因果。

对象的内容指纹与文件字节 SHA-256 不同。对象指纹排除复核/封存事件，因此复核状态改变不会伪造一个正文版本；正文、输入、参数或依赖变化仍会改变指纹。通过以下入口获取：

```powershell
.\automation\workspace.ps1 evidence-status RUN-ID
.\automation\workspace.ps1 hash-file <文件路径>
.\automation\workspace.ps1 evidence-status
```

第一个命令输出对象 fingerprint，第二个计算文件字节哈希，第三个列出当前影响范围。两种哈希不可互换。

## 复核与纠错

先保存候选，然后依据人的明确确认或已有授权验证流程操作：

```powershell
.\automation\workspace.ps1 review-claim CLM-ID --status accepted --reviewer "复核主体" --reason "复核原因" --evidence "验证记录或确认依据" --scope "已声明范围" --dry-run
.\automation\workspace.ps1 review-claim CLM-ID --status accepted --reviewer "复核主体" --reason "复核原因" --evidence "验证记录或确认依据" --scope "已声明范围"
.\automation\workspace.ps1 review-claim CLM-ID --status retracted --reviewer "复核主体" --reason "新的反证"
```

accepted 要求引用有效、scope 一致和完整复核记录，并自动绑定结论内容及所属对象版本；改正文、参数或输入后旧复核不能沿用。修改其他独立 claim 不改变这一绑定。superseded 还需 --replacement CLM-ID。dry-run 不写；实际修改追加复核历史，锁定单个 manifest 并比较读取版本。命令不认证 reviewer 身份，不自动判定证据真假。

review-run 保留旧行为，并额外返回 affected_evidence_ids；一条 Run 被撤回时，研究、算法卡、ADR 和报告通过已登记依赖传播风险。历史文件不会自动被覆盖、更正或删除。已打开的聊天/旧证据包也不会被后台改写。

## 正式 Run 检查与封存

```powershell
.\automation\workspace.ps1 check-run RUN-ID --scope "已声明范围"
.\automation\workspace.ps1 finalize-run RUN-ID --scope "已声明范围" --dry-run
.\automation\workspace.ps1 finalize-run RUN-ID --scope "已声明范围"
```

要求执行状态 succeeded、非空输入与产物清单且文件指纹匹配、固定代码 commit 且 dirty=false、Python 与环境锁/镜像 SHA-256、具名必要验证全部 passed，以及本 Run 的结论全部完成相同 scope 的复核。输入/产物条目格式为 `{"path":"工作区相对路径","sha256":"64位哈希"}`。这些字段仍由任务执行者负责真实登记，代码版本和镜像身份不在此命令中远程认证。

封存仅保存本次内容指纹和检查范围，不修改 Run 或 claim 的科学复核状态。正式读取会重新检查输入/产物文件的当前字节，不能只凭旧封存沿用被替换的文件。内容改变后检查失败；重新复核变动的结论，再执行 finalize 可创建新封存，旧封存事件保留于 finalization_history。上游 Run 必须先完成正式检查与封存；本 Run 可先 review-claim，再 finalize，避免相互等待。

## 从证据中提取正式结论

```powershell
.\automation\workspace.ps1 evidence-status CLM-ID --scope "已声明范围" --formal
.\automation\workspace.ps1 retrieve-context "本次问题" --purpose formal --scope "已声明范围"
```

正式上下文只导出已复核、版本仍有效、依赖未失效且 scope 匹配的结论和证据引用；不会夹带所在文件的其余正文。Run 中的结论还要求有效封存。同一结论去重，条目预算不足时整条省略，避免截掉限定条件。完全没有有效结论时保留 manifest 并退出 1。混合文档可只导出其中有效的条目；evidence-status 对整份文档的 formal 检查更严格，要求其所有声明都符合该范围。

purpose/scope 在 context-feedback 扩展链保留，旧会话默认 exploration。正式包是受约束的结论摘录，不能冒充完整算法原文；算法全文缺失标记仍保留。日常推理先使用默认探索模式读取算法与反证，交付前再检查正式依据。报告生成方必须调用该门；任意 shell 直接写报告不在此机制约束之内。

## 首批真实试点

选一个已有获准算法：一份算法说明、一个固定实现、一个历史结果。保留原件，登记版本/适用范围和一个可重跑 Run；依照现有检索流程分批接入。初期约 30–50 个实际问题作为起点，分开调参与独立验收，覆盖版本冲突、单位/公式错误、失效结论、范围外问题和无法回答。

现有 retrieval/eval.json 仍只衡量来源召回，不能代替答案验收。真实问题的标准答案、来源版本、定位、单位、允许误差、必须揭示的冲突和停止条件应由领域复核者核对。当前没有公司材料，不能用本仓库合成测试填充真实评估集。
