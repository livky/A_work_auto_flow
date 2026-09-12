---
name: material-query
description: 查找和完整读取本地固定材料，维护带出处的阅读理解与必要细节；适用于所有Owner类型，不生成或认可新结论。
---

# 本地材料与阅读

已有上下文能推进就先工作。需要依据时按当前问题和授权范围检索，各Owner类型都可提供方法、经验或启发，不把归属当成可信度。

有RS先用 `material-query reading-list --owner ID` 找到，再 `material-query reading-view --session RS-ID --markdown` 读取必要理解。新问题用reading-template填写目标/条件/query和owner_id，再reading-start；未知字段/请求结构按[AI阅读接口](../../../docs/AI_READING.md)读取，勿猜参数。

reading-recall各层独立身份/词法/语义召回：短候选全文，L1命中块与必要条件，均带固定链接。coverage仍有候选可reading-page；缺模型、partial、空页都不能解释为全库无资料。

可保留直接相关或有具体连接理由的间接启发。保留后reading-read交付完整记录，AI实际阅读正文和缺口，再reading-note保存理解、连接步骤/假设、必要细节及出处。参数、变量/单位、边界、反例和决定性片段不能被不当压缩；交付回执不证明理解正确。

依据不足时，AI结合已读材料的相关性、当前缺口和下一步对本地经验的依赖判断：相关但缺细节就读深正文/固定依据；路线失败或关键经验仍缺则改写问题、扩大获准范围召回；已有可行方向可先推进，依赖低时可改用实验或其他来源。间接启发保留连接理由与待验证条件，不用固定分数或轮数决定。reading-decide保存实际结果、理由和下一步（proceed/expand/ask_user/finish），同时更新work-loop工作清单；expand填写实际outcome。需要用户取舍才ask_user，已处于ask_user须等真实意见，不能伪造human_decision。硬预算、授权和排除始终保留，不能新建会话伪装续查以清零预算。

RS绑定Owner和可选固定检查点，用reading-bind补旧会话归属；reading-archive只归档、不删除来源或历史。笔记属于当前阅读工作，复用成果另按work-loop保存。工作台“系统记忆→阅读记录”可查看最新状态；导出的Markdown是指定版本快照。

用户手动查询或使用旧MQ表示/文稿入口时，按[材料查询手册](../../../docs/MATERIAL_QUERY.md)操作；不要求先建RS。语义修订与结构关联是独立按需能力，不在每次阅读中强制执行。
