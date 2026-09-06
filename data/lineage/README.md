# 血缘事件

第一阶段可把事件追加到项目 Run 内的 `lineage.jsonl`；达到查询瓶颈后再汇总到 SQLite 或 OpenLineage 后端。

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
