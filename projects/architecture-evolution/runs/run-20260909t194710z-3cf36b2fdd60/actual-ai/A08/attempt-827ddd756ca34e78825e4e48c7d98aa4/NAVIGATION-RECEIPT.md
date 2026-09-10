# 导航草案实际保存与回读

公开 `memory associations-decide` 已提交导航记录 **MEM-bab0426e-0012-5106-9124-4b5fba49a65f r1**，SHA256 为 `2f319ec12299920fc1c24c3310dda7aded06a448c439ff96db79f78ced50b6b1`，归属 `RES-F3-RETRY`。`created_by.kind=ai`，身份为 `Codex /root/retrieval_review actual AI`。

我实际回读了公开 inspect 返回的正文、两个端点、四条固定依据与四条迁移限制：`relation=analogous_to`，`status=candidate`。公开 `associations-view` 返回 `stale=false`、无变化端点。记录没有变成 supports，未创建科学 review，也没有冒领人工身份。

保存返回 `save_status=committed`，同时 `index_status=pending`、`INDEX_PENDING`、进程退出码 3。这是已保存但向量索引待处理的状态，不是保存失败。随后公开 `memory reconcile` 显式指定 `vector=off`，实际返回 `index_status=indexed`，向量保持 disabled；未配置本地模型的事实保留。

保存后又通过公开 inspect 读取双方原始 r1：水箱章节仍为 SHA256 `d4833181c30ccefb61f91558678bd6ade4363312852a41b37b1d014e2de02b27`，API 单元仍为 `7a68515fb103ca5ab6d09179905763972ca1446196589561222310364c0d27da`，两者归属也保持。导航记录只增加了一份候选判断，没有复制实验或修订原正文。

完整调用和结果见 [navigation-result.json](navigation-result.json)，关键原始证据如下。

- [公开保存回执](calls/call-4e81fbade77f45439ed142abb2d21ef4/stdout.txt)
- [公开固定记录回读](calls/call-a6adce6c15db429ea62b7665b263fef0/stdout.txt)
- [公开关系状态回读](calls/call-f018f26162764358b03f025c6a44328c/stdout.txt)
- [公开文本索引回执](calls/call-74d730a5320a40b8b672ee8af09158dd/stdout.txt)

“已保存导航草案”“索引可读”“人工认可”“科学结论有效”仍是四种不同状态；后两项未获得。
