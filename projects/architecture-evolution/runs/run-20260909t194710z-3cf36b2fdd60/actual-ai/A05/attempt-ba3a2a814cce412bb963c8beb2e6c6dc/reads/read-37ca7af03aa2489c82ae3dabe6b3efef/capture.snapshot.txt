# A05 对 A09 既有证据的只读交叉复审

复审者：Codex `/root/frontier_review/acceptance_c01_c14`（ai）；日期：2026-09-10。这里只读已经保存的 JSON 与实际交付正文，并比较对应字段；没有调用产品、重演场景、运行测试或修改原回执。本文件供父任务实际阅读，不单独决定 A05 最终状态。

原要求来自 `automation/testing/templates/ai-scenarios.json`：A05-E1「影响原因与路径明确，未变内容不无故重写」；A05-E2「旧固定版本保留，双文档一致或明示待更新」；A05-E3「无变化不重复堆积，缺失来源不被掩盖」。以下路径均相对本 Run；证据基目录为 `actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/`，下表缩写 `A09/` 表示该完整目录。

## 可交叉引用的实际执行

| A05 条目 | 已执行证据与本次观察 | 精确证据路径（加上述 A09 前缀） |
|---|---|---|
| E1：原因及影响路径 | AI 实际阅读新饱和约束、旧模型和定义，决定 retain 新输入/定义、revise 模型。影响查询返回 `NEW_REVISION`、`requires_review=true`，同时给出「文稿→模型」与「文稿→相关章节→模型」两条路径，两份文稿各有一个受影响章节。查询 `writes=0`。 | `AI-ANALYSIS.md`；`outcomes/impact-before-process.json`；`outcomes/impact-before-report.json` |
| E1：未变内容保持 | `retained-tank_definitions.json` 的整个 record 与 `initial-tank.json` 对应对象相等；`retained-saturation.json` 与 `initial-saturation.json` 对应对象相等；二者仍 r1。模型 r1 与初始 record 完整相等；r2 保留原 `model` 块中 `## 边界` 之前的全部正文，只改末尾边界提示并新增 `saturation_boundary`。不能说 r2 的整个旧块字节不变。 | `outcomes/initial-tank.json`；`outcomes/initial-saturation.json`；`outcomes/retained-tank_definitions.json`；`outcomes/retained-saturation.json`；`outcomes/model-r1-after.json`；`outcomes/model-r2-after.json` |
| E1：局部文稿更新 | 实际分别提交两个受影响章节 r2，再提交两份独立文稿 r2。原公式、变量定义和未饱和适用条件保留，新可达性分析补入完整稿，关键数值和限制进入简稿。 | `outcomes/updated-full-section-commit.json`；`outcomes/updated-brief-section-commit.json`；`outcomes/updated-process-commit.json`；`outcomes/updated-report-commit.json`；`delivered/updated-process.md`；`delivered/updated-report.md` |
| E2：旧固定版仍可读 | 本次比较 `baseline-*-read.json` 与 `historical-*-read.json`：各自 `document` 和完整 `report` 结构相等；历史读回 `report.complete=true`、`writes=0`。历史模型保持 r1，另有 `report_version_hints` 指明 current_revision=2，未替换正文。 | `outcomes/baseline-process-read.json`；`outcomes/baseline-report-read.json`；`outcomes/historical-process-read.json`；`outcomes/historical-report-read.json`；`delivered/historical-process.md`；`delivered/historical-report.md` |
| E2：双文稿当前一致 | 更新稿均 `report.complete=true`、`missing=[]`；两份 `common_refs` 相同，固定定义 r1、模型 r2、饱和输入 r1；最新 impact 均 `changes=[]`、`affected_section_ids=[]`、`writes=0`，`scientific_review=not_evaluated`。 | `document-update-receipt.json`；`outcomes/updated-process-read.json`；`outcomes/updated-report-read.json`；`outcomes/impact-after-process.json`；`outcomes/impact-after-report.json` |

影响路径中的固定身份：完整稿 `MEM-0e18d836-4370-5e10-88de-5a3c1da976ce` → 完整章节 `MEM-59e96850-644f-5a1a-9817-000499466692` → 模型 `MEM-2810407a-91e3-5114-b909-9a737b5e7885`；简稿 `MEM-35305be1-6956-5547-8457-b07b06b3b29d` → 简要章节 `MEM-fdc54497-ca64-52d2-a9a2-48b3e188f6bb` → 同一模型。两个 impact 回执还保存了跳过章节的直接依据路径。

## 固定修订与标识

下列 SHA 为 record SHA（不是 commit 回执中的 content_hash）。

| 对象 | record_id | r1 SHA256 | r2 SHA256 |
|---|---|---|---|
| 模型 | `MEM-2810407a-91e3-5114-b909-9a737b5e7885` | `b959d433659b2f69f9cbd050a2f866e25c78ba655fd70aa4461d1dd8d246b4bc` | `a67f152795f1faaea2adfe8d786ada6ac2db796972570e25f3833c045ad725a2` |
| 完整章节 | `MEM-59e96850-644f-5a1a-9817-000499466692` | `d4833181c30ccefb61f91558678bd6ade4363312852a41b37b1d014e2de02b27` | `34ecafeff6026b5a5784518f154c5558f135a1b93128ff42aa7731596f650399` |
| 简要章节 | `MEM-fdc54497-ca64-52d2-a9a2-48b3e188f6bb` | `a8a611af0cbe69d15adcdcd816cc2a70309817ae205abc2cb474d7bab0a9e1c6` | `89c35f26d30d3631b2de614b63a345dc70729cc21a053fff90575a15a3efff69` |
| 完整稿 | `MEM-0e18d836-4370-5e10-88de-5a3c1da976ce` | `8cef3944102f4255ad62750a31ecd15f92230009a595b055909cbd7f8ab78d3e` | `c7ccfc356fa372121b304b49adf19d4beca480301ae55ece68be3eea39074997` |
| 简稿 | `MEM-35305be1-6956-5547-8457-b07b06b3b29d` | `5a7f8e1870d9b3aed6fedd07697a717fcac9d896818447235792a0b7f48227d6` | `8d8b83d87e24d72068fa89a4d41dd27a59615b6faad6b96eae998bf18f7caa34` |

定义 `MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a` 保持 r1 / `9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d`；新输入 `MEM-6f7931dc-84bc-510e-b865-60a6d530e3ef` 保持 r1 / `8780b85874388753acbc846a22c1b4d20d68234dac9040ab8b8d2c15627bdada`。

模型事务的计划为 `MP-1c92d2ce-1cb4-44ea-b4ec-c3f882bec6c7`，审查后 digest 为 `b6d4c57663a683e445963ebb0b1941d2a77aed240b0b63e8550c8e6773ddf9df`；`A09/ready-apply-request.json` 固定 request_id `d9b6718f-ee70-4d97-a9b8-380e2689c9de`。`A09/outcomes/maintenance-apply.json` 与 `A09/outcomes/maintenance-apply-same-id.json` 均回读 `RES-F3-TANK / COM-525a8d2a-122a-44fb-a5c0-01a3e1cfd3fe`；两者 `pending_items=[]`、`index_status=pending`、状态 partial / exit_code=2，不能把初次结果写成全部完成。`A09/outcomes/maintenance-index-reconcile.json` 后续明确 vector=off、index_status=indexed、canonical_writes=0。`A09/outcomes/maintenance-stale-review.json` 为旧 HEAD 审查返回 rejected / CONFLICT。

| 文稿阶段 | request_id | commit_id |
|---|---|---|
| 完整章节 r2 | `ca16a058-7bed-4eb0-9415-b4dad964d685` | `COM-ff817f4c-f903-431b-961b-3af9faf07f4b` |
| 简要章节 r2 | `8d93d740-9113-4245-b0df-970d0b569924` | `COM-983b6bd1-a703-4ef7-98ef-76c774695329` |
| 完整稿 r2 | `093a3290-25e0-4f6b-9b73-c957434315a4` | `COM-818cb25e-c314-4d44-a9b5-973e355a3b65` |
| 简稿 r2 | `5e2e6900-10ce-409c-a00c-defd98a93434` | `COM-7d0a2539-e2b6-4c77-b04a-d22956f47baf` |

## 不能由交叉引用替代的部分

- E1/E2 可登记为「复用 A09 已执行证据，并由本次 AI 只读交叉复审」。本次不是 A05 新的产品执行，也不是另一位 AI 独立重演 A09；原 A09 的输入与分析由同一 AI 连续完成，非盲测。
- A09 的同 request_id 重试证明该事务幂等；它不等于新建一次“无新变化再整理”的完整计划，也不能单独关闭 A05-E3。两份 impact 的 `changes=[]` 是只读观察，无新规范写入；不是实际无变化计划的应用回执。
- A09 没有执行真实缺失来源用例；`missing=[]`、原件哈希保持与已明确限制不能代替“缺失来源不被掩盖”的新检查。
- 双文稿 r1 是 A09 当次通过公开事务创建的显式旧依据基线，并非恢复出来的真实历史文稿；该事实必须随 E2 交叉引用保留。
- 原 A09 仅修订 TANK/SATURATION 的合成 detail，并用单独公开事务维护文稿；没有证明任意材料自动生成、故障注入、跨 owner 部分失败恢复、现实模型有效性或人工验收。本次也未重新读取原始文件、重新核验当前产品指纹或重跑其公开调用。
