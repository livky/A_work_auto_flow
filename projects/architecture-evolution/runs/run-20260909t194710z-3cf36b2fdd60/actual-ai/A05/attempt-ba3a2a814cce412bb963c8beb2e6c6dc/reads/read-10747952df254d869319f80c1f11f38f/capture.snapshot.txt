# A05新计划实际完整交付

plan_id=MP-bb08320e-9c81-4014-90d1-edee9bc3d07d

warnings=["尚未执行语义判断；初始动作全部为defer", "未调用语义向量、模型或未登记旧Run来源；不能据此声称覆盖全部影响"]

## SYNTHETIC F3 执行器饱和的新约束

# SYNTHETIC F3 新材料：执行器饱和约束

这是新收到的独立合成约束输入，没有旧材料 ID、引用或关联边，不是现实实验结果。

## 变量与可达性

水箱模型的面积 $A=2\,\mathrm{m^2}$，出流系数 $c=0.1\,\mathrm{m^2/s}$，液位 $h$ 与目标 $h_r$ 单位为米。新给定泵上限 $q_{max}=0.15\,\mathrm{m^3/s}$，目标 $h_r=2\,\mathrm{m}$。非负泵流量必须满足 $0\leq q\leq q_{max}$，状态方程为 $A\dot h=q-ch$。

在目标液位维持平衡需要 $q=c h_r=0.2\,\mathrm{m^3/s}$，超出给定泵上限。持续饱和时，平衡液位为 $h_{sat}=q_{max}/c=1.5\,\mathrm{m}$，低于目标。仅增大比例增益不能提高泵的物理上限。

## 阅读边界

本材料给出特定合成参数下的代数约束，足以要求重新检查“未饱和”的前提。它不是线性段指数推导错误的证明，也不含真实泵、传感器或延迟数据。对其他目标与流量上限必须重新判断可达性。


```json
{
  "owner_id": "RES-F3-SATURATION",
  "kind": "detail",
  "level": "L1",
  "title": "SYNTHETIC F3 执行器饱和的新约束",
  "keywords": [
    "SYNTHETIC",
    "F3",
    "执行器饱和的新约束"
  ],
  "payload": {
    "blocks": [
      {
        "block_id": "body",
        "markdown": "# SYNTHETIC F3 新材料：执行器饱和约束\n\n这是新收到的独立合成约束输入，没有旧材料 ID、引用或关联边，不是现实实验结果。\n\n## 变量与可达性\n\n水箱模型的面积 $A=2\\,\\mathrm{m^2}$，出流系数 $c=0.1\\,\\mathrm{m^2/s}$，液位 $h$ 与目标 $h_r$ 单位为米。新给定泵上限 $q_{max}=0.15\\,\\mathrm{m^3/s}$，目标 $h_r=2\\,\\mathrm{m}$。非负泵流量必须满足 $0\\leq q\\leq q_{max}$，状态方程为 $A\\dot h=q-ch$。\n\n在目标液位维持平衡需要 $q=c h_r=0.2\\,\\mathrm{m^3/s}$，超出给定泵上限。持续饱和时，平衡液位为 $h_{sat}=q_{max}/c=1.5\\,\\mathrm{m}$，低于目标。仅增大比例增益不能提高泵的物理上限。\n\n## 阅读边界\n\n本材料给出特定合成参数下的代数约束，足以要求重新检查“未饱和”的前提。它不是线性段指数推导错误的证明，也不含真实泵、传感器或延迟数据。对其他目标与流量上限必须重新判断可达性。\n",
        "requires_block_ids": [],
        "role": "methods"
      }
    ],
    "evidence_refs": [
      {
        "locator": "完整合成输入",
        "relation": "input",
        "revision": null,
        "sha256": "7bcb1b5e9e7791021701252d87d96473784146c883c648248fde7a86b40ff28f",
        "target_id": "SRC-F3-SATURATION",
        "target_kind": "file"
      }
    ],
    "figures": [],
    "missing_refs": [],
    "retrieval_description": {
      "applicable": [
        "本文明确的合成条件"
      ],
      "key_findings": [
        "此输入没有真实执行结果"
      ],
      "limitations": [
        "缺少实测与科学复核"
      ],
      "method": "读取独立合成前提并保留变量、公式和限制",
      "not_applicable": [
        "现实系统的稳定或性能结论"
      ],
      "question": "执行器饱和的新约束的机制与约束"
    },
    "run_ref": null,
    "unit_type": "analysis"
  },
  "sources": [
    {
      "locator": "完整合成输入",
      "relation": "input",
      "revision": null,
      "sha256": "7bcb1b5e9e7791021701252d87d96473784146c883c648248fde7a86b40ff28f",
      "target_id": "SRC-F3-SATURATION",
      "target_kind": "file"
    }
  ],
  "provenance_gap": null,
  "discovery": "workspace_summary",
  "sensitivity": "internal"
}
```

refs=[{"kind": "record", "id": "MEM-6f7931dc-84bc-510e-b865-60a6d530e3ef", "revision": 1, "sha256": "8780b85874388753acbc846a22c1b4d20d68234dac9040ab8b8d2c15627bdada", "locator": ""}]

omitted=[]

## SYNTHETIC F3 水箱线性段误差分析

## 水箱负反馈的线性段

质量守恒与控制律为

$$
A\frac{dh}{dt}=q-ch,\qquad q_c=c h_r+K(h_r-h),\qquad q=\operatorname{clip}(q_c,0,q_{max}).
$$

在整个讨论区间保持 $0<q_c<q_{max}$ 时，可代入 $q=q_c$；目标不变，故

$$
\frac{de}{dt}=-\frac{c+K}{A}e,\qquad e(t)=e(0)\exp\left(-\frac{c+K}{A}t\right).
$$

这是给定合成连续线性模型的代数推导，未做现实实验。若 $A>0,c>0,K\geq0$ 且不触发饱和，误差按该模型指数衰减。时间常数 $\tau=A/(c+K)$，单位为秒。

## 边界

上述指数解只属于未饱和区间；更大目标或初始误差可能使泵触顶或关闭，此时必须返回带 clip 的分段动力学。材料未提供普遍“增益越大越好”的现实结论。尚未测量延迟、噪声与出流非线性；本次新参数的目标可达性检查见后续边界块。


## 新饱和输入的目标可达性（合成代数检查）

新固定输入给出 $q_{max}=0.15\,\mathrm{m^3/s}$、$h_r=2\,\mathrm{m}$，沿用 $c=0.1\,\mathrm{m^2/s}$ 与 $A=2\,\mathrm{m^2}$。目标平衡需要

$$
q_{req}=c h_r=0.20\,\mathrm{m^3/s}>q_{max}.
$$

因此该参数下不存在维持目标的可用入流。持续饱和分支的平衡为

$$
h_{sat}=\frac{q_{max}}{c}=1.5\,\mathrm{m},\qquad h_r-h_{sat}=0.5\,\mathrm{m}.
$$

$q_{req}$ 是维持目标所需流量，$h_{sat}$ 是持续最大流量时的合成平衡液位。仅增大 $K$ 不能突破泵上限；不能在该目标下沿用未饱和指数式来保证误差归零。原线性段推导保留其条件成立的适用范围，没有被整体撤回。

这是基于新旧固定文字前提的代数分析，不是泵实测、仿真运行或科学复核。其他目标、泵能力、延迟和非线性条件仍需独立检查。


```json
{
  "owner_id": "RES-F3-TANK",
  "kind": "detail",
  "level": "L1",
  "title": "SYNTHETIC F3 水箱线性段误差分析",
  "keywords": [
    "SYNTHETIC",
    "F3",
    "水箱线性段误差分析"
  ],
  "payload": {
    "blocks": [
      {
        "block_id": "model",
        "markdown": "## 水箱负反馈的线性段\n\n质量守恒与控制律为\n\n$$\nA\\frac{dh}{dt}=q-ch,\\qquad q_c=c h_r+K(h_r-h),\\qquad q=\\operatorname{clip}(q_c,0,q_{max}).\n$$\n\n在整个讨论区间保持 $0<q_c<q_{max}$ 时，可代入 $q=q_c$；目标不变，故\n\n$$\n\\frac{de}{dt}=-\\frac{c+K}{A}e,\\qquad e(t)=e(0)\\exp\\left(-\\frac{c+K}{A}t\\right).\n$$\n\n这是给定合成连续线性模型的代数推导，未做现实实验。若 $A>0,c>0,K\\geq0$ 且不触发饱和，误差按该模型指数衰减。时间常数 $\\tau=A/(c+K)$，单位为秒。\n\n## 边界\n\n上述指数解只属于未饱和区间；更大目标或初始误差可能使泵触顶或关闭，此时必须返回带 clip 的分段动力学。材料未提供普遍“增益越大越好”的现实结论。尚未测量延迟、噪声与出流非线性；本次新参数的目标可达性检查见后续边界块。\n",
        "requires_block_ids": [],
        "role": "methods"
      },
      {
        "block_id": "saturation_boundary",
        "markdown": "## 新饱和输入的目标可达性（合成代数检查）\n\n新固定输入给出 $q_{max}=0.15\\,\\mathrm{m^3/s}$、$h_r=2\\,\\mathrm{m}$，沿用 $c=0.1\\,\\mathrm{m^2/s}$ 与 $A=2\\,\\mathrm{m^2}$。目标平衡需要\n\n$$\nq_{req}=c h_r=0.20\\,\\mathrm{m^3/s}>q_{max}.\n$$\n\n因此该参数下不存在维持目标的可用入流。持续饱和分支的平衡为\n\n$$\nh_{sat}=\\frac{q_{max}}{c}=1.5\\,\\mathrm{m},\\qquad h_r-h_{sat}=0.5\\,\\mathrm{m}.\n$$\n\n$q_{req}$ 是维持目标所需流量，$h_{sat}$ 是持续最大流量时的合成平衡液位。仅增大 $K$ 不能突破泵上限；不能在该目标下沿用未饱和指数式来保证误差归零。原线性段推导保留其条件成立的适用范围，没有被整体撤回。\n\n这是基于新旧固定文字前提的代数分析，不是泵实测、仿真运行或科学复核。其他目标、泵能力、延迟和非线性条件仍需独立检查。\n",
        "requires_block_ids": [
          "model"
        ],
        "role": "limitations"
      }
    ],
    "evidence_refs": [
      {
        "locator": "完整合成输入",
        "relation": "input",
        "revision": null,
        "sha256": "76ad0abf1493aa0879a8d85f48a21a62e62ab6be77ed833e7779645bad7630a7",
        "target_id": "SRC-F3-TANK",
        "target_kind": "file"
      },
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
        "sha256": "8780b85874388753acbc846a22c1b4d20d68234dac9040ab8b8d2c15627bdada",
        "target_id": "MEM-6f7931dc-84bc-510e-b865-60a6d530e3ef",
        "target_kind": "record"
      }
    ],
    "figures": [],
    "missing_refs": [],
    "retrieval_description": {
      "applicable": [
        "变量字典一致且全过程未饱和"
      ],
      "key_findings": [
        "给定无延迟合成模型中，误差在未饱和区间指数衰减",
        "新给定泵上限0.15 m³/s、目标2 m时，所需0.20 m³/s超出上限，不能保证目标误差归零"
      ],
      "limitations": [
        "仅检查给定合成参数的代数可达性；其他目标、泵能力、延迟与非线性仍未验证；没有现实实验"
      ],
      "method": "代入质量守恒并在未饱和区间求解一阶误差方程",
      "not_applicable": [
        "执行器饱和、未知延迟或直接外推现实模型",
        "不得把该线性段解用于新给定的不可达目标"
      ],
      "question": "未饱和水箱负反馈的误差怎样变化"
    },
    "run_ref": null,
    "unit_type": "analysis"
  },
  "sources": [
    {
      "locator": "完整合成输入",
      "relation": "input",
      "revision": null,
      "sha256": "76ad0abf1493aa0879a8d85f48a21a62e62ab6be77ed833e7779645bad7630a7",
      "target_id": "SRC-F3-TANK",
      "target_kind": "file"
    },
    {
      "locator": "",
      "relation": "prerequisite",
      "revision": 1,
      "sha256": "9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d",
      "target_id": "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a",
      "target_kind": "record"
    },
    {
      "locator": "",
      "relation": "references",
      "revision": 1,
      "sha256": "8780b85874388753acbc846a22c1b4d20d68234dac9040ab8b8d2c15627bdada",
      "target_id": "MEM-6f7931dc-84bc-510e-b865-60a6d530e3ef",
      "target_kind": "record"
    }
  ],
  "provenance_gap": null,
  "discovery": "workspace_summary",
  "sensitivity": "internal"
}
```

refs=[{"kind": "record", "id": "MEM-2810407a-91e3-5114-b909-9a737b5e7885", "revision": 2, "sha256": "a67f152795f1faaea2adfe8d786ada6ac2db796972570e25f3833c045ad725a2", "locator": null}]

omitted=[]

## SYNTHETIC F3 水箱必要变量定义

## 必要变量与单位

设水箱横截面积 $A=2\,\mathrm{m^2}$，液位 $h(t)$ 与常值目标 $h_r$ 的单位为 $\mathrm{m}$，时间 $t$ 单位为 $\mathrm{s}$。入流量 $q(t)$ 单位为 $\mathrm{m^3/s}$；出流量采用线性假设 $q_{out}=c h$，其中 $c=0.1\,\mathrm{m^2/s}$。误差定义为 $e=h_r-h$。比例增益 $K\geq0$ 的单位为 $\mathrm{m^2/s}$，使 $K e$ 与流量同量纲。$q_c$ 是未限幅命令，$q_{max}>0$ 是泵的流量上限，二者单位均为 $\mathrm{m^3/s}$。

操作函数 $\operatorname{clip}(x,0,q_{max})=\min(q_{max},\max(0,x))$。初值 $h(0)=h_0\geq0$。传感器、泵在此材料中假设连续、无延迟；未加入噪声、泄漏变化或积分控制。


```json
{
  "owner_id": "RES-F3-TANK",
  "kind": "detail",
  "level": "L1",
  "title": "SYNTHETIC F3 水箱必要变量定义",
  "keywords": [
    "SYNTHETIC",
    "F3",
    "水箱必要变量定义"
  ],
  "payload": {
    "blocks": [
      {
        "block_id": "definitions",
        "markdown": "## 必要变量与单位\n\n设水箱横截面积 $A=2\\,\\mathrm{m^2}$，液位 $h(t)$ 与常值目标 $h_r$ 的单位为 $\\mathrm{m}$，时间 $t$ 单位为 $\\mathrm{s}$。入流量 $q(t)$ 单位为 $\\mathrm{m^3/s}$；出流量采用线性假设 $q_{out}=c h$，其中 $c=0.1\\,\\mathrm{m^2/s}$。误差定义为 $e=h_r-h$。比例增益 $K\\geq0$ 的单位为 $\\mathrm{m^2/s}$，使 $K e$ 与流量同量纲。$q_c$ 是未限幅命令，$q_{max}>0$ 是泵的流量上限，二者单位均为 $\\mathrm{m^3/s}$。\n\n操作函数 $\\operatorname{clip}(x,0,q_{max})=\\min(q_{max},\\max(0,x))$。初值 $h(0)=h_0\\geq0$。传感器、泵在此材料中假设连续、无延迟；未加入噪声、泄漏变化或积分控制。\n",
        "requires_block_ids": [],
        "role": "definitions"
      }
    ],
    "evidence_refs": [
      {
        "locator": "完整合成输入",
        "relation": "input",
        "revision": null,
        "sha256": "76ad0abf1493aa0879a8d85f48a21a62e62ab6be77ed833e7779645bad7630a7",
        "target_id": "SRC-F3-TANK",
        "target_kind": "file"
      }
    ],
    "figures": [],
    "missing_refs": [],
    "retrieval_description": {
      "applicable": [
        "同一水箱合成前提"
      ],
      "key_findings": [
        "仅建立合成模型的变量字典"
      ],
      "limitations": [
        "没有现实参数辨识"
      ],
      "method": "固定变量符号、单位与理想化前提",
      "not_applicable": [
        "不同单位或物理机制"
      ],
      "question": "水箱模型采用哪些变量和单位"
    },
    "run_ref": null,
    "unit_type": "analysis"
  },
  "sources": [
    {
      "locator": "完整合成输入",
      "relation": "input",
      "revision": null,
      "sha256": "76ad0abf1493aa0879a8d85f48a21a62e62ab6be77ed833e7779645bad7630a7",
      "target_id": "SRC-F3-TANK",
      "target_kind": "file"
    }
  ],
  "provenance_gap": null,
  "discovery": "workspace_summary",
  "sensitivity": "internal"
}
```

refs=[{"kind": "record", "id": "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a", "revision": 1, "sha256": "9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d", "locator": null}]

omitted=[]

## 已登记原始材料

# SYNTHETIC F3 新材料：执行器饱和约束

这是新收到的独立合成约束输入，没有旧材料 ID、引用或关联边，不是现实实验结果。

## 变量与可达性

水箱模型的面积 $A=2\,\mathrm{m^2}$，出流系数 $c=0.1\,\mathrm{m^2/s}$，液位 $h$ 与目标 $h_r$ 单位为米。新给定泵上限 $q_{max}=0.15\,\mathrm{m^3/s}$，目标 $h_r=2\,\mathrm{m}$。非负泵流量必须满足 $0\leq q\leq q_{max}$，状态方程为 $A\dot h=q-ch$。

在目标液位维持平衡需要 $q=c h_r=0.2\,\mathrm{m^3/s}$，超出给定泵上限。持续饱和时，平衡液位为 $h_{sat}=q_{max}/c=1.5\,\mathrm{m}$，低于目标。仅增大比例增益不能提高泵的物理上限。

## 阅读边界

本材料给出特定合成参数下的代数约束，足以要求重新检查“未饱和”的前提。它不是线性段指数推导错误的证明，也不含真实泵、传感器或延迟数据。对其他目标与流量上限必须重新判断可达性。


refs=[{"kind": "file", "id": "SRC-F3-SATURATION", "revision": null, "sha256": "7bcb1b5e9e7791021701252d87d96473784146c883c648248fde7a86b40ff28f", "locator": "完整合成输入"}]

omitted=[]

## 已登记原始材料

# SYNTHETIC F3 水箱负反馈线性模型

独立合成前提，不是公司算法或现实试验。

## 必要变量与单位

设水箱横截面积 $A=2\,\mathrm{m^2}$，液位 $h(t)$ 与常值目标 $h_r$ 的单位为 $\mathrm{m}$，时间 $t$ 单位为 $\mathrm{s}$。入流量 $q(t)$ 单位为 $\mathrm{m^3/s}$；出流量采用线性假设 $q_{out}=c h$，其中 $c=0.1\,\mathrm{m^2/s}$。误差定义为 $e=h_r-h$。比例增益 $K\geq0$ 的单位为 $\mathrm{m^2/s}$，使 $K e$ 与流量同量纲。$q_c$ 是未限幅命令，$q_{max}>0$ 是泵的流量上限，二者单位均为 $\mathrm{m^3/s}$。

操作函数 $\operatorname{clip}(x,0,q_{max})=\min(q_{max},\max(0,x))$。初值 $h(0)=h_0\geq0$。传感器、泵在此材料中假设连续、无延迟；未加入噪声、泄漏变化或积分控制。

## 水箱负反馈的线性段

质量守恒与控制律为

$$
A\frac{dh}{dt}=q-ch,\qquad q_c=c h_r+K(h_r-h),\qquad q=\operatorname{clip}(q_c,0,q_{max}).
$$

在整个讨论区间保持 $0<q_c<q_{max}$ 时，可代入 $q=q_c$；目标不变，故

$$
\frac{de}{dt}=-\frac{c+K}{A}e,\qquad e(t)=e(0)\exp\left(-\frac{c+K}{A}t\right).
$$

这是给定合成连续线性模型的代数推导，未做现实实验。若 $A>0,c>0,K\geq0$ 且不触发饱和，误差按该模型指数衰减。时间常数 $\tau=A/(c+K)$，单位为秒。

## 边界

上述指数解只属于未饱和区间；更大目标或初始误差可能使泵触顶或关闭，此时必须返回带 clip 的分段动力学。材料未提供普遍“增益越大越好”的现实结论。尚未测量延迟、噪声与出流非线性，也未验证目标流量是否可达。


refs=[{"kind": "file", "id": "SRC-F3-TANK", "revision": null, "sha256": "76ad0abf1493aa0879a8d85f48a21a62e62ab6be77ed833e7779645bad7630a7", "locator": "完整合成输入"}]

omitted=[]
