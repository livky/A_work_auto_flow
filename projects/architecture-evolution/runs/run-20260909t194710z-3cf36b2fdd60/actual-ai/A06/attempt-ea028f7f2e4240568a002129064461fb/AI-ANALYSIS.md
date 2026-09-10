# A06 自然语言发现候选的实际 AI 补充回执

执行者：Codex `/root/memory_review actual AI`。本补充执行发生于 2026-09-10（Asia/Shanghai），任务在 [manifest](manifest.json) 中事先冻结。它补齐原 A08 固定取文未覆盖的“从新问题发现候选”过程，使用原 SYNTHETIC F3 隔离区；不是重演 A08/A09，也不是盲测。

实际完成：新自然语言问题与技术关键词 → 公共 lexical 查询 → 阅读四个候选 → 根据返回引用选择固定全文 → 实际阅读全部五个交付部分 → 编写条件参考 → 公共保存并 inspect / associations-view → 原记录和原件保持检查。

## 观察与原始证据

| 步骤 | 实际观察 | 证据 |
|---|---|---|
| 初始失败 | 请求漏了范围和联想选项的必填字段；VALIDATION、消耗 0，未读取材料。失败保留，未伪装成功。 | [原请求](calls/call-9d7b6232a86d485f8b17877802229824/request.snapshot.txt)、[原返回](calls/call-9d7b6232a86d485f8b17877802229824/stdout.txt) |
| 自然语言发现 | 只补齐字段，保留原问题与“重试、饱和、误差、边界”关键词；未预填 MEM ID/include_refs，未用 F3 标签做关键词。lexical 返回模型 r2、定义 r1、API r1、饱和 r1，均 not-assessed。 | [有效请求](calls/call-2eaaaa7e125a4b59b5cd13cab7c22294/request.snapshot.txt)、[实际候选](calls/call-2eaaaa7e125a4b59b5cd13cab7c22294/stdout.txt)、[阅读声明](reads/read-363f22c9169d4f8182ebb438a21cd3ef/event.json) |
| 选择与读取 | 依据候选摘要选择四份记录；新固定查询只使用上一步返回的 refs，组包 ok、complete=true。定义重复出现在 required_context 与 direct，四份独立证据交付为五部分，未重复计算证据数。 | [选择请求](calls/call-47b56f1236744402a0d66f61a6eabce2/request.snapshot.txt)、[原始组包](calls/call-47b56f1236744402a0d66f61a6eabce2/stdout.txt)、[可读交付](delivered-full.md)、[阅读声明](reads/read-8dd047df97a14dd0a6899fdf5b03bd3f/event.json) |
| 判断与保存 | 正例为有条件采用分段检查次序；负例拒绝增益互换和 API 稳定/吞吐/成功保证，列明服务端模型缺口与未执行验证。保存创建一份 analogous_to/candidate，committed；索引 pending，退出码 3。 | [采用说明](ADOPTION.md)、[保存请求](calls/call-e7eaed358e5c41339bc7171c9cf63ae4/request.snapshot.txt)、[提交回执](calls/call-e7eaed358e5c41339bc7171c9cf63ae4/stdout.txt) |
| 保存后回读 | 实际读完新记录正文、AI 身份、固定四条依据与候选状态。associations-view 的 stale=false、changed_endpoints=[]。 | [inspect](calls/call-0260a9e2e8d54358ad6390f0ad2ac30a/stdout.txt)、[view](calls/call-96b7d94a507b45ae9e7fb71acfb42d21/stdout.txt) |
| 索引与原材料 | 显式 vector=off reconcile 后文本 indexed，向量 disabled，canonical_writes=0。四份原记录公开 inspect 的哈希与 owner 均保持；A08 原导航哈希保持，三份原件字节哈希保持。 | [reconcile](calls/call-831fbf0fda3d454d91284dd19b888138/stdout.txt)、[逐项回读与哈希检查](readback-checks.json) |

新保存记录为 **MEM-1c372f0d-3afe-5a4b-96fb-867eff035115 r1**，SHA256 `cd92874aed47cdfb48b734d1d3569221cd4b6913d6cf685161a9f34cb10bf4e7`，归属 `RES-F3-RETRY`。该 owner 的 HEAD 从 `COM-b98936d9-17a7-4a31-9016-4c12ea27ccaa` 变为 `COM-d0ce2b58-4d09-49d5-87a2-05aa1e587187`，generation 2→3；水箱与饱和 owner 的 HEAD 未变。A05 独立副本检查已通知这次新增候选，不能将原目录有意新增的记录误认成原记录被修改。

## 逐预期自查

- **A06-E1：meets（本次功能执行范围）**。新问题确实经公共 lexical 查阅候选，先读返回候选再固定展开。初始请求没有固定路径或 ID；固定取文发生在候选阅读之后。执行者之前读过 A08/A09，所以这里不声称盲测或独立检索质量评估。
- **A06-E2：meets（已读合成前提）**。正文明确可参考的局部方法、幂等/超时/计数前提、不允许迁移的数值与稳定性保证、缺少的服务端模型，以及仍待执行的验证。分段检查建议未冒充已执行实验。
- **A06-E3：meets（新候选与固定原记录）**。参考说明保存在第二研究；双方原归属、四个固定来源和 A08 原导航保持。新记录仍为 candidate、AI 身份，未创建实验或科学复核。

## 限制

这是连续已知上下文、三个小型合成研究、词项检索通道；不证明语义模型已运行、未知领域发现质量、现实 API 稳定性或规模性能。CLI 发现与固定展开为两个独立查询，保留各自预算与 query_id，没有声称跨进程续查。只有新参考候选被写入合成 F3，产品源码、真实 Project、原件和既有结论未改动。人工审查 pending，科学复核 not-reviewed。
