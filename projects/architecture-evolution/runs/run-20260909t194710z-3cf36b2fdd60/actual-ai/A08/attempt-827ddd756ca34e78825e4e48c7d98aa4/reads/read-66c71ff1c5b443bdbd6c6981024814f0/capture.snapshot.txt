# retry-full

这是公开调用实际输出的可读投影；AI 阅读尚未声明。

调用证据：calls\call-5dd2950b5e564b53b1cbbe12612b7d04

返回码：0

```json
{
  "status": "ok",
  "code": null,
  "warnings": [],
  "consumed": {
    "wall_ms": 61,
    "read_bytes": 10434,
    "output_chars": 602,
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
  "complete": true,
  "basis": {
    "refs": [
      {
        "kind": "record",
        "id": "MEM-1749e71c-ee06-5f04-9c40-03228706f4f4",
        "revision": 1,
        "sha256": "7a68515fb103ca5ab6d09179905763972ca1446196589561222310364c0d27da",
        "locator": null
      }
    ],
    "owner_heads": [
      [
        "RES-F3-RETRY",
        "COM-b18654cc-36f8-4cc5-9743-726c1d770d59"
      ]
    ],
    "index_watermarks": [],
    "consistency": "fixed_refs"
  }
}
```

## direct / SYNTHETIC F3 API 退避重试策略

# SYNTHETIC F3 API 退避与重试

本材料是独立的软件策略前提，没有服务端负载测量、生产日志或成功率试验。

## 变量与机制

$k\in\{0,1,\ldots,N-1\}$ 为当前连续失败后的重试序号；$N=5$ 是总重试上限。$b=0.2\,\mathrm{s}$ 是初始等待，倍率 $r=2$ 无量纲，$d_{max}=3.2\,\mathrm{s}$ 是等待上限。等待策略为

$$
d_k=\min(d_{max},b r^k).
$$

一次请求失败后等待 $d_k$ 再重试，成功后结束本次流程，达到 $N$ 次则停止并返回失败。响应仅有成功/可重试失败/不可重试失败三类，不可重试失败立即停止。本前提没有目标误差 $e$、服务端队列长度、连续流量或物理守恒方程。

## 适用边界

只有具备幂等性或明确去重语义的操作可按此策略重复；必须给超时和最大总耗时单独设限。固定倍率与上限不证明服务端稳定、请求最终成功或最优吞吐。多个客户端同步重试可能同时唤醒；本前提未定义抖动、服务端容量、到达率、成功概率与响应延迟分布。


固定来源：`[{"kind": "record", "id": "MEM-1749e71c-ee06-5f04-9c40-03228706f4f4", "revision": 1, "sha256": "7a68515fb103ca5ab6d09179905763972ca1446196589561222310364c0d27da", "locator": null}]`
