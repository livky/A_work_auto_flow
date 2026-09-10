# tank-small-budget

这是公开调用实际输出的可读投影；AI 阅读尚未声明。

调用证据：calls\call-3cf2ca12cc5b40b39f2d2f8a46e63243

返回码：2

```json
{
  "status": "partial",
  "code": null,
  "warnings": [
    "输出预算不足，已省略完整块：SYNTHETIC F3 水箱必要变量定义",
    "输出预算不足，已省略完整块：SYNTHETIC F3 水箱线性段误差分析"
  ],
  "consumed": {
    "wall_ms": 171,
    "read_bytes": 28574,
    "output_chars": 31,
    "candidates": 1,
    "graph_nodes": 0,
    "graph_edges": 0,
    "graph_hops": 0,
    "model_tokens": 0,
    "model_calls": 0,
    "model_input_tokens": 0,
    "model_output_tokens": 0,
    "rerank_items": 0
  },
  "stop_reason": null,
  "complete": false,
  "basis": {
    "refs": [
      {
        "kind": "record",
        "id": "MEM-59e96850-644f-5a1a-9817-000499466692",
        "revision": 1,
        "sha256": "d4833181c30ccefb61f91558678bd6ade4363312852a41b37b1d014e2de02b27",
        "locator": null
      },
      {
        "kind": "record",
        "id": "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a",
        "revision": 1,
        "sha256": "9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d",
        "locator": ""
      },
      {
        "kind": "record",
        "id": "MEM-2810407a-91e3-5114-b909-9a737b5e7885",
        "revision": 1,
        "sha256": "b959d433659b2f69f9cbd050a2f866e25c78ba655fd70aa4461d1dd8d246b4bc",
        "locator": ""
      }
    ],
    "owner_heads": [
      [
        "RES-F3-TANK",
        "COM-667f328f-45bf-4ab3-af97-937e78ed45c0"
      ]
    ],
    "index_watermarks": [],
    "consistency": "fixed_refs"
  }
}
```

## direct / SYNTHETIC F3 水箱完整模型：定义、推导与边界

本章需要同时阅读变量定义与线性段推导；排除定义会留下解释缺口。

固定来源：`[{"kind": "record", "id": "MEM-59e96850-644f-5a1a-9817-000499466692", "revision": 1, "sha256": "d4833181c30ccefb61f91558678bd6ade4363312852a41b37b1d014e2de02b27", "locator": null}]`

## gaps / 缺口

输出预算不足，已省略完整块：SYNTHETIC F3 水箱必要变量定义
输出预算不足，已省略完整块：SYNTHETIC F3 水箱线性段误差分析

固定来源：`[]`
