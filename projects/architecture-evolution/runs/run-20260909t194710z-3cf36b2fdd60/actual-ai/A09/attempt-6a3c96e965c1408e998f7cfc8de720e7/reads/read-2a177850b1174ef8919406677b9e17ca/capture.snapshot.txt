# SYNTHETIC F3 水箱精简报告（旧依据基线）

公开 document 返回的完整正文投影；不是新撰写的文稿。

```json
{
  "document": {
    "record_id": "MEM-35305be1-6956-5547-8457-b07b06b3b29d",
    "revision": 1,
    "title": "SYNTHETIC F3 水箱精简报告（旧依据基线）",
    "document_type": "research_report",
    "purpose": "SYNTHETIC F3固定双文稿维护检查",
    "audience": "合成检查执行者",
    "scope": "旧r1依据基线；新饱和输入尚未融合，不据此认可新参数下的结论",
    "common_refs": [
      {
        "locator": "",
        "relation": "references",
        "revision": 1,
        "sha256": "9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d",
        "target_id": "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a",
        "target_kind": "record"
      },
      {
        "locator": "",
        "relation": "references",
        "revision": 1,
        "sha256": "b959d433659b2f69f9cbd050a2f866e25c78ba655fd70aa4461d1dd8d246b4bc",
        "target_id": "MEM-2810407a-91e3-5114-b909-9a737b5e7885",
        "target_kind": "record"
      }
    ],
    "section_refs": [
      {
        "locator": "",
        "relation": "references",
        "revision": 1,
        "sha256": "a8a611af0cbe69d15adcdcd816cc2a70309817ae205abc2cb474d7bab0a9e1c6",
        "target_id": "MEM-fdc54497-ca64-52d2-a9a2-48b3e188f6bb",
        "target_kind": "record"
      }
    ]
  },
  "missing": [],
  "report_coverage": {
    "included_detail_ids": [
      "MEM-2810407a-91e3-5114-b909-9a737b5e7885",
      "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a"
    ],
    "uncovered_detail_ids": []
  },
  "report_version_hints": [
    {
      "record_id": "MEM-2810407a-91e3-5114-b909-9a737b5e7885",
      "revision": 1,
      "current_revision": 2
    }
  ],
  "basis_heads": {
    "RES-F3-TANK": "COM-7d0a2539-e2b6-4c77-b04a-d22956f47baf"
  }
}
```

complete=True

## 水箱结论与边界（旧依据基线）

固定章节：`{"locator": "", "relation": "references", "revision": 1, "sha256": "a8a611af0cbe69d15adcdcd816cc2a70309817ae205abc2cb474d7bab0a9e1c6", "target_id": "MEM-fdc54497-ca64-52d2-a9a2-48b3e188f6bb", "target_kind": "record"}`

旧r1依据仅说明：在给定连续、无延迟且全过程未饱和的合成模型中，液位误差指数衰减。该结论不能推广到饱和泵或现实系统；尚需检查目标所需流量与泵容量。新输入尚未融合到这份显式基线，本文不确认新参数下可达。

依据：`[{"locator": "", "relation": "references", "revision": 1, "sha256": "9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d", "target_id": "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a", "target_kind": "record"}, {"locator": "", "relation": "references", "revision": 1, "sha256": "b959d433659b2f69f9cbd050a2f866e25c78ba655fd70aa4461d1dd8d246b4bc", "target_id": "MEM-2810407a-91e3-5114-b909-9a737b5e7885", "target_kind": "record"}]`
