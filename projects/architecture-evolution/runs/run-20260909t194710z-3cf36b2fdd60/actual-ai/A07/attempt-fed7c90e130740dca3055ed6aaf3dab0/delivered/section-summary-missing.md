# section-summary-missing

这是公开调用实际输出的可读投影；AI 阅读尚未声明。

调用证据：calls\call-0651848342b546c6ac2b7715b52ac1bd

返回码：2

```json
{
  "status": "partial",
  "code": null,
  "warnings": [
    "选定材料没有可组合正文"
  ],
  "consumed": {
    "wall_ms": 172,
    "read_bytes": 28574,
    "output_chars": 272,
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

## required_context / SYNTHETIC F3 水箱必要变量定义

问题：
水箱模型采用哪些变量和单位

方法：
固定变量符号、单位与理想化前提

主要发现：
- 仅建立合成模型的变量字典

适用条件：
- 同一水箱合成前提

不适用条件：
- 不同单位或物理机制

限制：
- 没有现实参数辨识

固定来源：`[{"kind": "record", "id": "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a", "revision": 1, "sha256": "9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d", "locator": ""}]`

## required_context / SYNTHETIC F3 水箱线性段误差分析

问题：
未饱和水箱负反馈的误差怎样变化

方法：
代入质量守恒并在未饱和区间求解一阶误差方程

主要发现：
- 给定无延迟合成模型中，误差在未饱和区间指数衰减

适用条件：
- 变量字典一致且全过程未饱和

不适用条件：
- 执行器饱和、未知延迟或直接外推现实模型

限制：
- 尚未验证目标可达性；需要同组必要定义

固定来源：`[{"kind": "record", "id": "MEM-2810407a-91e3-5114-b909-9a737b5e7885", "revision": 1, "sha256": "b959d433659b2f69f9cbd050a2f866e25c78ba655fd70aa4461d1dd8d246b4bc", "locator": ""}]`

## gaps / 缺口

选定材料没有可组合正文

固定来源：`[]`
