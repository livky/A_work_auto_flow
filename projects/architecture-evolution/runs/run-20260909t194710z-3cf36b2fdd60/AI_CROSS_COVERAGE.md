# A05 / A06 与既有 A09 / A08 的实际 AI 证据交叉核对

**补充后的阅读入口：** [A06 新问题发现与条件采用已实际完成](actual-ai/A06/attempt-ea028f7f2e4240568a002129064461fb/AI-ANALYSIS.md)，A06-E1/E2/E3 的补充自查为 meets；[A05 无变化整理、缺失来源及恢复的独立补充报告](actual-ai/A05/attempt-ba3a2a814cce412bb963c8beb2e6c6dc/AI-ANALYSIS.md)和 [A05 汇总回执](a05-supplement-receipt.json)分别记录 A05-E1/E2 的明确 A09 复用以及 E3 的新执行。人工与科学验收仍待完成。

**以下“只读核对”“没有新增调用”“两项部分覆盖”及未覆盖清单均为补测前时点。** 保留当时映射以说明补测原因；文末追加 A06 新执行回执。它们不是补充完成后的最终状态，原 A08/A09 的状态与证据没有被改写。

核对者：Codex `/root/memory_review`（AI）；记录日期：2026-09-10（Asia/Shanghai）。核对范围仅为本 Run 已保存的调用请求、实际返回、阅读声明、分析与 assessment；本次没有新增产品调用、测试或场景 attempt，没有修改原 assessment 或验收状态。

**结论：六项预期中，四项在既有合成执行范围内有实质覆盖，另两项只有部分覆盖。不能因此把 A05、A06 的独立执行记为通过。** A05-E3 缺少“无新变化重新整理”完整过程和缺失来源分支；A06-E1 使用预知固定 ID 取文，未检查新问题发现候选的过程。下表的“覆盖”是证据映射判断，均不是新增测试通过、人工认可或科学复核。

## 固定依据与继承边界

预期来自 [ai-scenarios.json](../../../../automation/testing/templates/ai-scenarios.json)，本次读取 SHA256：`08e4f243c5ff6c4a4889967323e1e62af2c55c8ebc5879d78f4fcb6ddb71cb77`，与两个 attempt 的模板指纹一致。

| 既有执行 | 固定入口 | 原 assessment |
|---|---|---|
| A08 `attempt-827ddd756ca34e78825e4e48c7d98aa4` | [manifest](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/manifest.json)、[实际 AI 分析](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/AI-ANALYSIS.md) | [assessment-6ad5dd19f48641d7860d39b97d5267b7](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/assessments/assessment-6ad5dd19f48641d7860d39b97d5267b7.json)，SHA256 `2592714227b246fd45e30cb87c0d11e39fafd615e89184e2dc1e99e0349f0d62` |
| A09 `attempt-6a3c96e965c1408e998f7cfc8de720e7` | [manifest](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/manifest.json)、[实际 AI 分析](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/AI-ANALYSIS.md) | [assessment-e5b36d2cf0d34558bdff303687f91f38](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/assessments/assessment-e5b36d2cf0d34558bdff303687f91f38.json)，SHA256 `adbd6f2cade1d6897e367267843abb75929d2a63ba34258426cce9428b1b8359` |

原执行者为 Codex `/root/retrieval_review actual AI`。输入是同一执行 AI 编写的 SYNTHETIC F3 水箱、API 重试与饱和约束，连续上下文，非盲测、新上下文续接或现实实验。两个 assessment 的 `meets` 分别只评价 A08、A09 原预期，不能自动改写为 A05/A06 的 assessment。原 manifest 的初始 `not-run` 状态是不可变初始事件，应结合其后 calls、reads、assessment 阅读。

本报告仅核对上述既有执行当时的结果，不证明后续源码修改已经重新通过实际 AI 使用。人工审查仍 pending，科学复核仍 not-reviewed / not_evaluated。可读汇总入口为 [最终实际 AI 报告](actual-ai/reports/report-ff44c20b371046cab453c7b91b19b660/REVIEW.md)。

## A05：增量更新与历史保持

原任务：根据新边界局部修订技术单元，检查影响并更新受影响章节及双文档，回读新旧版，无新变化再整理一次。

| 预期 | 交叉覆盖判断 | 已有实际证据与限制 |
|---|---|---|
| A05-E1 正文：“影响原因与路径明确，未变内容不无故重写” | **有实质覆盖，限 F3 个案** | A09 阅读新约束、模型、定义和两份原件后，retain 定义与新输入，仅 revise 模型；旧模型公式保留，新增饱和边界块并修正“未检查可达性”的旧描述。两份 document-impact 返回模型 r1→r2 的 `NEW_REVISION`、直接依据路径和经章节路径。定义回读仍为原 r1；两个相关章节与两份文稿才更新。见证据 A05-1。不能外推为任意规模文稿都不会被无故改写。 |
| A05-E2 正文：“旧固定版本保留，双文档一致或明示待更新” | **有实质覆盖，限本次新建的合成基线** | A09 对模型 r1/r2、两份文稿 r1/r2 分别实际回读；新版两稿共同依据均为定义 r1、模型 r2、新饱和输入 r1；历史稿保持旧引用和旧正文，并提示模型有新版本。科学状态未提升。见证据 A05-2。两份旧依据基线是本次公开新建的合成文稿，并非长期历史业务记录。 |
| A05-E3 正文：“无变化不重复堆积，缺失来源不被掩盖” | **部分覆盖，不能整项记通过** | 两次相同 request_id 的 apply 返回相同 COM；最终两份 impact 均 `changes=[]`、`writes=0`。这证明该固定请求重试幂等及更新后的只读影响检查为空。没有证据显示在更新完成后重新生成维护计划并完整整理一次，也没有缺失/失联来源实际触发：本例来源齐全，文稿 `missing=[]`。不能用这些正常返回替代“缺失来源不被掩盖”的分支检查。见证据 A05-3。 |

### A05-1：影响与局部修订证据

- [实际维护包阅读声明](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/reads/read-5e1b7f142b494a998f99ffa930012051/event.json)及其 [capture](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/reads/read-5e1b7f142b494a998f99ffa930012051/capture.snapshot.txt)：明确读完五部分，根据正文作出 retain / retain / revise；声明是执行者实际阅读声明，存盘本身不等于已读。
- 模型 [r1 inspect 原始返回](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-23dbf3b48dea496f985c55a16aaa2120/stdout.txt)与 [r2 inspect 原始返回](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-795faa5cfd1b4097a27d46febc307f01/stdout.txt)：同一 `MEM-2810407a-91e3-5114-b909-9a737b5e7885`；r2 保留 `model` 块的条件推导，新增 `saturation_boundary` 块。修改原因、追加固定来源与 `run_ref=null` 均可回读。
- [定义原 r1 回读](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-ed6af3a75de84c3aafacbc5a5841dc51/stdout.txt)：`MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a`、SHA256 `9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d`，未被重新修订。
- [完整过程 impact 原始返回](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-e3b18fdc03794d558de521f9f1cf3848/stdout.txt)与 [简报 impact 原始返回](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-a3be712dea444c8bbcd25b8a2c860885/stdout.txt)：两稿分别给出受影响章节、模型 r1/r2 固定哈希和 `requires_review=true`。

修改所依据的是明确的合成边界计算：目标所需流量为

\[
q_{req}=c h_r=0.20\,\mathrm{m^3/s}>q_{max}=0.15\,\mathrm{m^3/s}.
\]

其中，\(c=0.1\,\mathrm{m^2/s}\) 为线性出流系数，\(h_r=2\,\mathrm m\) 为目标液位，\(q_{max}\) 为泵上限。原分析由此限定该目标不可维持，未将其写成原条件推导被整体推翻，也未声称执行了现实试验。

### A05-2：双文稿新旧回读证据

| 对象 | 公共调用实际返回 | 实际阅读声明 |
|---|---|---|
| 完整过程 r2 | [call-eda6825b69d24d1888715c7ed9705fbd](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-eda6825b69d24d1888715c7ed9705fbd/stdout.txt) | [read-efc768a49bf14415a869bb735d36df95](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/reads/read-efc768a49bf14415a869bb735d36df95/event.json) |
| 精简报告 r2 | [call-6deac7a226904315822b0067d1766cde](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-6deac7a226904315822b0067d1766cde/stdout.txt) | [read-40bedd03a44446c6b55918903c1ab905](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/reads/read-40bedd03a44446c6b55918903c1ab905/event.json) |
| 完整过程历史 r1 | [call-02c41d6cebe046db85a00b9199c18eec](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-02c41d6cebe046db85a00b9199c18eec/stdout.txt) | [read-267aa1533c4348b5aab7fdfbd77f2abb](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/reads/read-267aa1533c4348b5aab7fdfbd77f2abb/event.json) |
| 精简报告历史 r1 | [call-eeda96b443bd414a8a63aba74262d29e](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-eeda96b443bd414a8a63aba74262d29e/stdout.txt) | [read-2a177850b1174ef8919406677b9e17ca](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/reads/read-2a177850b1174ef8919406677b9e17ca/event.json) |

固定新版本、历史修订号、共同依据、原件哈希与导航过期状态汇总于 [document-update-receipt.json](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/document-update-receipt.json)。更新后 A08 的旧章节导航仍为 `stale=true`、章节当前 r2，明确待复核，没有删除旧导航或自动认定可继续沿用。

### A05-3：幂等与仍缺的分支

[首次 apply 原始返回](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-c6c87e43829449848eb321cafc1d6e6c/stdout.txt)与 [同请求再次 apply 原始返回](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-55abd190b5af4644ba16ed54f00c0c55/stdout.txt)使用相同 request_id `d9b6718f-ee70-4d97-a9b8-380e2689c9de`，返回相同 `COM-525a8d2a-122a-44fb-a5c0-01a3e1cfd3fe`，均如实保留 `partial` 与索引 pending。[完整过程最终 impact](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-0883a9d37d494e82a97001391cd19e1b/stdout.txt)和 [简报最终 impact](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/calls/call-9270a4dfc62a4c319c5438917e46c3fd/stdout.txt)均 `changes=[]`、`writes=0`。后两次是只读检查，不是再次运行完整整理过程；来源齐全也不能检验缺失来源分支。

## A06：跨研究适用条件

原任务：在第二研究用新问题检索和展开第一研究结果，分别判断可参考方法及超出适用范围的请求，保存带条件的采用说明。

| 预期 | 交叉覆盖判断 | 已有实际证据与限制 |
|---|---|---|
| A06-E1 正文：“通过实际检索查阅候选，不按预知路径抄答案” | **部分覆盖，关键发现过程未覆盖** | A08 真实调用公共 `material-query search --assemble` 并阅读两份 full 正文及水箱定义；但两个请求的 question 都是预先已知的 MEM ID，include_refs 指定固定 r1，channels 只有 identity。确实查阅了材料，无法证明“从第二研究的新问题发现第一研究候选”或非预知路径检索。见证据 A06-1。 |
| A06-E2 正文：“正例保留条件，负例明确不可推广与缺口” | **有实质覆盖，限所读两份合成材料** | A08 可参考项仅为区分封顶前后再检查边界的方法，限定幂等/去重、错误类别、超时与总耗时；明确拒绝数值增益互换及由水箱连续模型推导 API 稳定、吞吐或最终成功保证，说明缺少服务端状态与负载模型，并给出待执行事件序列验证。实际保存内容含正反判断及限制。见证据 A06-2。 |
| A06-E3 正文：“原归属和固定来源保持，不复制实验或提高可信状态” | **有实质覆盖，限导航候选** | 保存的候选归属第二研究 `RES-F3-RETRY`；两端仍固定第一研究水箱章节与第二研究 API 单元 r1。保存后分别 inspect 原对象确认哈希和归属保持。导航为 `analogous_to/candidate`、AI 身份，未创建实验或科学 review。见证据 A06-2。该候选是有条件参考说明，不代表完成实际技术采用验证。 |

### A06-1：公共固定查阅与未覆盖的发现过程

- 水箱调用 [request snapshot](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/calls/call-b7513a3df54049bf9675ac508d3a19b4/request.snapshot.txt)、[result](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/calls/call-b7513a3df54049bf9675ac508d3a19b4/result.json)、[实际交付正文](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/delivered/tank-full.md)、[阅读声明](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/reads/read-2d6f56d83dde49aca7fb4ae7a49a2bc1/event.json)。
- API 调用 [request snapshot](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/calls/call-5dd2950b5e564b53b1cbbe12612b7d04/request.snapshot.txt)、[result](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/calls/call-5dd2950b5e564b53b1cbbe12612b7d04/result.json)、[实际交付正文](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/delivered/retry-full.md)、[阅读声明](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/reads/read-66c71ff1c5b443bdbd6c6981024814f0/event.json)。

这两个 request snapshot 直接显示 `question=MEM-…`、`scope.include_refs` / `scope_ceiling.include_refs` 固定 r1、`freshness=fixed`、`channels=[identity]`。A08 的原任务允许选定两份材料后做结构比较，因此这个发现过程缺口不否定 A08 原自查；它只限制本次对 A06-E1 的继承。

### A06-2：有条件参考的保存及回读

[导航保存 request snapshot](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/calls/call-4e81fbade77f45439ed142abb2d21ef4/request.snapshot.txt)包含比较正文、共同局部结构、四项迁移限制、固定两端与四条依据；[公开保存原始返回](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/calls/call-4e81fbade77f45439ed142abb2d21ef4/stdout.txt)与 [导航 inspect 原始返回](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/calls/call-a6adce6c15db429ea62b7665b263fef0/stdout.txt)记录 `MEM-bab0426e-0012-5106-9124-4b5fba49a65f` r1、SHA256 `2f319ec12299920fc1c24c3310dda7aded06a448c439ff96db79f78ced50b6b1`、`owner_id=RES-F3-RETRY`、`created_by.kind=ai` 和候选状态。[实际阅读声明](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/reads/read-b7fbaafe9b704c92b0eef75ce3949ea8/event.json)明确核对了这些字段。

保存后 [水箱原 r1 inspect](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/calls/call-d2ac28929a2e46b4875fca765567c969/stdout.txt)和 [API 原 r1 inspect](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/calls/call-07ccebc3e4524418b3af05c746724290/stdout.txt)可核对原归属及哈希；[保存与回读分析](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/NAVIGATION-RECEIPT.md)分别记录保存 committed、索引 pending 和随后文本 indexed。

结构自动探索实际返回 [UNSUPPORTED](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/delivered/unconfigured-structural.md)。候选内容来自当次对话 AI 的实际阅读和撰写，不能将其记成产品自动结构模型已经执行成功。

## 保留的未覆盖项

1. A05：更新完成后，在无新增依据条件下重新执行一次整理/维护规划，核对未重复产生业务修订；既有同 request_id 重试只能覆盖该请求幂等。
2. A05：实际遇到缺失或不可访问来源时的维护与文稿表现；当前两次执行没有触发此分支。
3. A06：从第二研究的新自然语言问题开始，在未预先指定第一研究候选 ID 的条件下检索、选择、展开并说明采用边界。
4. A05、A06 均未因此新增独立 attempt；新上下文、独立执行者、现实业务有效性、人工验收以及最终源码的重新实际 AI 使用不在本次交叉核对证明范围内。

## 后续补充：A06 的新问题发现候选已实际执行

上述只读核对发现的 A06-E1 缺口，随后按明确任务补做，保存在 **A06 / attempt-ea028f7f2e4240568a002129064461fb**。本段是新的实际执行证据，不把原 A08 改成曾经做过自然语言发现；A05 的追加执行由另一执行者独立记录。

- [补充任务与执行环境](actual-ai/A06/attempt-ea028f7f2e4240568a002129064461fb/manifest.json)事先冻结任务、源码/Skill 指纹、合成输入原件哈希与初始 HEAD，明确连续已知上下文。
- [发现请求](actual-ai/A06/attempt-ea028f7f2e4240568a002129064461fb/calls/call-2eaaaa7e125a4b59b5cd13cab7c22294/request.snapshot.txt)使用新的自然语言问题及“重试、饱和、误差、边界”关键词，channels=lexical；没有 MEM ID/include_refs。实际返回四个候选，先阅读后才按返回 refs 发起固定全文查询。
- [固定组包返回](actual-ai/A06/attempt-ea028f7f2e4240568a002129064461fb/calls/call-47b56f1236744402a0d66f61a6eabce2/stdout.txt)为 ok / complete=true，实际阅读模型 r2、定义 r1、API r1、新饱和输入 r1。定义作为必要上下文与直接选择重复呈现，未当成额外独立证据。CLI 两次查询身份独立，未冒充续查。
- [条件采用说明](actual-ai/A06/attempt-ea028f7f2e4240568a002129064461fb/ADOPTION.md)保留正例条件、负例与模型缺口；经公共保存并 inspect 回读为 `MEM-1c372f0d-3afe-5a4b-96fb-867eff035115` r1、SHA256 `cd92874aed47cdfb48b734d1d3569221cd4b6913d6cf685161a9f34cb10bf4e7`，归属 RES-F3-RETRY，状态仍 analogous_to / candidate，AI 身份。
- [原记录和原件检查](actual-ai/A06/attempt-ea028f7f2e4240568a002129064461fb/readback-checks.json)显示四份原记录的公共 inspect 哈希与 owner 保持，A08 旧导航哈希保持，三份原件哈希保持。只新增一个合成参考候选；RETRY HEAD 从 COM-b98936d9-17a7-4a31-9016-4c12ea27ccaa 变为 COM-d0ce2b58-4d09-49d5-87a2-05aa1e587187。该新增已通知 A05 副本执行者。
- [逐项自查 assessment-ca63ed7be8c7442a8ebfd9fe3a4394b9](actual-ai/A06/attempt-ea028f7f2e4240568a002129064461fb/assessments/assessment-ca63ed7be8c7442a8ebfd9fe3a4394b9.json)对本补充范围的 A06-E1/E2/E3 均记录 meets；[可读实际执行回执](actual-ai/A06/attempt-ea028f7f2e4240568a002129064461fb/AI-ANALYSIS.md)链接全部调用、实际阅读与限制。

原首个 A06 请求漏必填字段，VALIDATION / 消耗 0 的失败仍保留；补齐字段后问题和关键词不变。保存返回 committed + INDEX_PENDING / 退出码 3，后续显式 vector=off 的 reconcile 返回文本 indexed、向量 disabled、canonical_writes=0。新问题经词项通道发现候选的功能过程已补齐；盲测、语义模型质量、现实系统验证、人工与科学验收仍未完成。

## 后续补充：A05 的无变化整理与缺失来源由独立执行者完成

Codex `/root/frontier_review` 在 A09 最终状态的独立合成副本完成 **A05 / attempt-ba3a2a814cce412bb963c8beb2e6c6dc**。本核对者已读其 [实际分析](actual-ai/A05/attempt-ba3a2a814cce412bb963c8beb2e6c6dc/AI-ANALYSIS.md)与 [固定汇总回执](a05-supplement-receipt.json)，此处引用其执行结果，不冒领自己执行了 A05。

新计划先真实交付五部分，执行者完整阅读后逐项填写 retain，经 review 后以新 request_id apply 返回 `ok / commits=[] / pending_items=[]`；55 份规范与来源文件保持。独立副本临时缺失已登记来源时，公共入口返回 `SOURCE_MISSING`，恢复原字节后重新交付相同内容，55 文件再次一致。原 A09 的局部修订、双文稿及旧版回读仍作为 A05-E1/E2 的明确复用证据；本次新执行补齐 A05-E3，未声称重新执行整条 A09 旅程。

因此，本报告最初识别的两个具体功能证据缺口已有各自的补充回执。两项补充均保留原失败调用、实际阅读声明和逐预期自查；“AI 自查 meets”仍不等于人工认可或科学有效。
