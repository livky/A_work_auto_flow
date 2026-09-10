# SYNTHETIC F3 水箱完整过程（旧依据基线）

公开 document 返回的完整正文投影；不是新撰写的文稿。

```json
{
  "document": {
    "record_id": "MEM-0e18d836-4370-5e10-88de-5a3c1da976ce",
    "revision": 1,
    "title": "SYNTHETIC F3 水箱完整过程（旧依据基线）",
    "document_type": "research_process",
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
        "sha256": "d4833181c30ccefb61f91558678bd6ade4363312852a41b37b1d014e2de02b27",
        "target_id": "MEM-59e96850-644f-5a1a-9817-000499466692",
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

## SYNTHETIC F3 水箱完整模型：定义、推导与边界

固定章节：`{"locator": "", "relation": "references", "revision": 1, "sha256": "d4833181c30ccefb61f91558678bd6ade4363312852a41b37b1d014e2de02b27", "target_id": "MEM-59e96850-644f-5a1a-9817-000499466692", "target_kind": "record"}`

本章需要同时阅读变量定义与线性段推导；排除定义会留下解释缺口。

依据：`[]`

固定单元：`{"locator": "", "relation": "references", "revision": 1, "sha256": "9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d", "target_id": "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a", "target_kind": "record"}`

## 必要变量与单位

设水箱横截面积 $A=2\,\mathrm{m^2}$，液位 $h(t)$ 与常值目标 $h_r$ 的单位为 $\mathrm{m}$，时间 $t$ 单位为 $\mathrm{s}$。入流量 $q(t)$ 单位为 $\mathrm{m^3/s}$；出流量采用线性假设 $q_{out}=c h$，其中 $c=0.1\,\mathrm{m^2/s}$。误差定义为 $e=h_r-h$。比例增益 $K\geq0$ 的单位为 $\mathrm{m^2/s}$，使 $K e$ 与流量同量纲。$q_c$ 是未限幅命令，$q_{max}>0$ 是泵的流量上限，二者单位均为 $\mathrm{m^3/s}$。

操作函数 $\operatorname{clip}(x,0,q_{max})=\min(q_{max},\max(0,x))$。初值 $h(0)=h_0\geq0$。传感器、泵在此材料中假设连续、无延迟；未加入噪声、泄漏变化或积分控制。


固定单元：`{"locator": "", "relation": "references", "revision": 1, "sha256": "b959d433659b2f69f9cbd050a2f866e25c78ba655fd70aa4461d1dd8d246b4bc", "target_id": "MEM-2810407a-91e3-5114-b909-9a737b5e7885", "target_kind": "record"}`

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

