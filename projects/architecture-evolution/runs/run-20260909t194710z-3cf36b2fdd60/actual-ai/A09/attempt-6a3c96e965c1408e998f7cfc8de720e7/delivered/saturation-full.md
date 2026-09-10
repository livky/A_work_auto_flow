# saturation-full

这是公开调用实际输出的可读投影；AI 阅读尚未声明。

调用证据：calls\call-18f4d64b713a4159b40a7a7c91487162

返回码：0

```json
{
  "status": "ok",
  "code": null,
  "warnings": [],
  "consumed": {
    "wall_ms": 61,
    "read_bytes": 10496,
    "output_chars": 620,
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
        "id": "MEM-6f7931dc-84bc-510e-b865-60a6d530e3ef",
        "revision": 1,
        "sha256": "8780b85874388753acbc846a22c1b4d20d68234dac9040ab8b8d2c15627bdada",
        "locator": null
      }
    ],
    "owner_heads": [
      [
        "RES-F3-SATURATION",
        "COM-4a163fb0-43b8-45b1-b946-50faa4d66659"
      ]
    ],
    "index_watermarks": [],
    "consistency": "fixed_refs"
  }
}
```

## direct / SYNTHETIC F3 执行器饱和的新约束

# SYNTHETIC F3 新材料：执行器饱和约束

这是新收到的独立合成约束输入，没有旧材料 ID、引用或关联边，不是现实实验结果。

## 变量与可达性

水箱模型的面积 $A=2\,\mathrm{m^2}$，出流系数 $c=0.1\,\mathrm{m^2/s}$，液位 $h$ 与目标 $h_r$ 单位为米。新给定泵上限 $q_{max}=0.15\,\mathrm{m^3/s}$，目标 $h_r=2\,\mathrm{m}$。非负泵流量必须满足 $0\leq q\leq q_{max}$，状态方程为 $A\dot h=q-ch$。

在目标液位维持平衡需要 $q=c h_r=0.2\,\mathrm{m^3/s}$，超出给定泵上限。持续饱和时，平衡液位为 $h_{sat}=q_{max}/c=1.5\,\mathrm{m}$，低于目标。仅增大比例增益不能提高泵的物理上限。

## 阅读边界

本材料给出特定合成参数下的代数约束，足以要求重新检查“未饱和”的前提。它不是线性段指数推导错误的证明，也不含真实泵、传感器或延迟数据。对其他目标与流量上限必须重新判断可达性。


固定来源：`[{"kind": "record", "id": "MEM-6f7931dc-84bc-510e-b865-60a6d530e3ef", "revision": 1, "sha256": "8780b85874388753acbc846a22c1b4d20d68234dac9040ab8b8d2c15627bdada", "locator": null}]`
