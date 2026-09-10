# 血缘事件

可把事件保存到实际 Run 内的 `lineage.jsonl`；Run 可以归属研究、算法、项目等对象，也可以是无归属的根 Run。当前格式是人工/脚本维护的文件约定，不代表已部署 OpenLineage 服务。需要后端汇总时先证明查询收益，再增加实现。

最小事件示例：

```json
{
  "event_id": "EVT-<uuid>",
  "event_time": "2026-09-04T08:00:00Z",
  "event_type": "COMPLETE",
  "activity": {"type": "analysis", "run_id": "RUN-..."},
  "agent": {"type": "software", "id": "TOOL-...", "version": "..."},
  "inputs": [{"entity_id": "DATA-...", "version": "...", "digest": "..."}],
  "outputs": [{"entity_id": "ART-...", "uri_alias": "...", "digest": "..."}],
  "code": {"repository": "private", "commit": "..."},
  "status": "succeeded"
}
```

失败事件也应记录，并与 `run.json` 状态一致。若同一作业产生多个不相关输出，显式记录真实边，避免笛卡尔积式假血缘。
