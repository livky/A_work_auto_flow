# A09 无旧边新约束的实际维护

执行者：Codex `/root/retrieval_review`，身份类型 ai。所有产品调用只访问 SYNTHETIC F3 隔离区；未修改主工作区业务对象。输入与本次分析由同一 AI 在连续上下文完成，不是盲测或科学验收。

## 实际阅读与判断

我先通过公开 full 查询读到饱和单元 r1，再读完维护任务包实际交付的五部分：新约束、旧模型、必要定义、两份已登记原件。初始 saturation 的 sources 与 evidence_refs 仅指向自身原件，没有旧材料记录引用。计划中的旧模型与定义由共享词项形成候选；它们共享的 SYNTHETIC/F3 标记也会造成命中，所以不能把这次候选命中当成语义检索质量证明。判断来自实际公式阅读。

给定目标液位 $h_r=2\,\mathrm{m}$、出流系数 $c=0.1\,\mathrm{m^2/s}$、泵上限 $q_{max}=0.15\,\mathrm{m^3/s}$，目标所需流量为

$$
q_{req}=ch_r=0.20\,\mathrm{m^3/s}>q_{max}.
$$

因此这个合成目标无法维持。持续最大流量分支的平衡液位 $h_{sat}=q_{max}/c=1.5\,\mathrm{m}$，与目标相差 $0.5\,\mathrm{m}$。这里 $q_{req}$ 为目标所需流量，$h_{sat}$ 为持续饱和分支的平衡液位。我核对了计算与单位，没有执行仿真或现实试验。

新证据限制的是把未饱和线性解用于该新参数的推论，不证明原条件推导错误。因此逐项决定如下。

| 项目 | 动作 | 实际原因 |
|---|---|---|
| 饱和新输入 r1 | retain | 保留原始合成约束与固定来源，不把输入改成实验结果 |
| 必要变量定义 r1 | retain | 单位、误差与 clip 含义仍适用，不必无故修订 |
| 水箱线性段模型 r1 | revise | 保留未饱和推导，追加给定参数不可达的计算、限制与新固定依据 |

没有采用 retract：本例没有应撤回的已复核 claim，也没有证明条件成立时的线性式错误。无旧边不等于无影响，但共享词也不等于已经证明影响。

## 维护事务的实际结果

初始计划 `MP-1c92d2ce-1cb4-44ea-b4ec-c3f882bec6c7`，digest `932af988848a21af6cb852f17d1a08a4af6907cb7d0338fd27dd07cbea911610`，所有动作最初 defer，reviewed_refs 为空。我实际读完五部分后填入原交付 refs，保留服务器 read_receipt、上下文和未检查范围，填写自己的 ai 身份与具体理由。

公开 maintenance-review 保存 digest `b6d4c57663a683e445963ebb0b1941d2a77aed240b0b63e8550c8e6773ddf9df`，返回 partial 及“保存审查不等于科学有效”的说明。公开 apply 使用固定 request_id `d9b6718f-ee70-4d97-a9b8-380e2689c9de`，真实产生 `RES-F3-TANK / COM-525a8d2a-122a-44fb-a5c0-01a3e1cfd3fe`；pending_items 为空，但索引 pending，不能称全部完成。随后以同一 request_id 再次 apply，回读同一个 COM，没有增加新修订；再提交旧 review 请求，实际返回 CONFLICT，提示 HEAD 已改变。

模型已公开回读为 **MEM-2810407a-91e3-5114-b909-9a737b5e7885 r2**，SHA256 `a67f152795f1faaea2adfe8d786ada6ac2db796972570e25f3833c045ad725a2`。r1 保持 `b959d433659b2f69f9cbd050a2f866e25c78ba655fd70aa4461d1dd8d246b4bc`。公开 reconcile 显式 vector=off 后文本 indexed；模型仍未配置。

## 双文稿和下游回读

F3 起初没有两份独立文稿。为了实际检查双文稿维护，我明确通过公开事务新建了“旧 r1 依据基线”的完整过程与简报；它们当时就注明新输入尚未融合。它们不是恢复出来的真实历史记录。

模型更新后，我实际读了公开 document-impact：两份文稿各有指向模型 r1→r2 的 NEW_REVISION 和受影响章节。随后只修订两个相关章节，再更新两份独立文稿的固定引用与共同依据。全文保留定义、原推导和新增可达性块；简版保留关键数值、适用限制与未验证事项。两份文稿的共同依据一致，为定义 r1、模型 r2、新约束 r1。

| 文稿 | r2 固定记录 | SHA256 |
|---|---|---|
| 完整过程 | MEM-0e18d836-4370-5e10-88de-5a3c1da976ce | c7ccfc356fa372121b304b49adf19d4beca480301ae55ece68be3eea39074997 |
| 精简报告 | MEM-35305be1-6956-5547-8457-b07b06b3b29d | 8d8b83d87e24d72068fa89a4d41dd27a59615b6faad6b96eae998bf18f7caa34 |

我实际读完两份更新稿和两份历史 r1 投影。当前两稿 complete=true，最新 impact changes=[]；历史稿仍是旧正文和旧引用，额外提示模型已有 r2，没有静默替换。`scientific_review=not_evaluated` 保持。三份原件的 SHA256 与 F3 manifest 一致。

A08 候选导航仍固定旧章节 r1，公开 associations-view 现在真实返回 stale=true、章节 current_revision=2。这项保留为下游待重新检查，不自动提升为可沿用关系，也没有删除历史候选。

## 范围与证据入口

- [饱和全文](delivered/saturation-full.md)、[维护包完整实际交付](delivered/maintenance-plan.md)。
- [更新完整稿](delivered/updated-process.md)、[更新简稿](delivered/updated-report.md)、[历史完整稿](delivered/historical-process.md)、[历史简稿](delivered/historical-report.md)。
- [公开 apply](outcomes/maintenance-apply.json)、[幂等回读](outcomes/maintenance-apply-same-id.json)、[旧依据拒绝](outcomes/maintenance-stale-review.json)、[文稿更新回执](document-update-receipt.json)。
- 维护计划只选择 TANK/SATURATION 的 detail；文稿使用单独公开规范事务维护。API 材料、其他主题、未登记来源和真实系统未纳入本次语义维护。
- 本例检验一次成功应用、同身份重试和过期依据拒绝，没有执行故障注入或跨 owner 部分失败恢复；这些需要独立机械测试。
- 没有进行科学 review 或人工验收。AI 自查、保存、索引和科学有效性分别记录。

实际调用同时暴露了界面问题：有效 review 返回 partial 时，界面此前只接受 ok，导致无法进入应用。该真实集成缺口已报告父任务，随后修复与浏览器回归另存，不混入本节的 CLI 成功结论。
