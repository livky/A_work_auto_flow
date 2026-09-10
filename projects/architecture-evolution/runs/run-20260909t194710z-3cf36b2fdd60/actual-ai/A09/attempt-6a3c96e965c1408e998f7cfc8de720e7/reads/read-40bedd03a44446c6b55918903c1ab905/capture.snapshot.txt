# SYNTHETIC F3 水箱精简报告

公开 document 返回的完整正文投影；不是新撰写的文稿。

```json
{
  "document": {
    "record_id": "MEM-35305be1-6956-5547-8457-b07b06b3b29d",
    "revision": 2,
    "title": "SYNTHETIC F3 水箱精简报告",
    "document_type": "research_report",
    "purpose": "SYNTHETIC F3固定双文稿维护检查",
    "audience": "合成检查执行者",
    "scope": "固定模型r2、定义r1与饱和输入r1；仅合成参数下的代数分析，人工与科学验收未完成",
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
        "revision": 2,
        "sha256": "a67f152795f1faaea2adfe8d786ada6ac2db796972570e25f3833c045ad725a2",
        "target_id": "MEM-2810407a-91e3-5114-b909-9a737b5e7885",
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
    "section_refs": [
      {
        "locator": "",
        "relation": "references",
        "revision": 2,
        "sha256": "89c35f26d30d3631b2de614b63a345dc70729cc21a053fff90575a15a3efff69",
        "target_id": "MEM-fdc54497-ca64-52d2-a9a2-48b3e188f6bb",
        "target_kind": "record"
      }
    ]
  },
  "missing": [],
  "report_coverage": {
    "included_detail_ids": [
      "MEM-2810407a-91e3-5114-b909-9a737b5e7885",
      "MEM-6f7931dc-84bc-510e-b865-60a6d530e3ef",
      "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a"
    ],
    "uncovered_detail_ids": []
  },
  "report_version_hints": [],
  "basis_heads": {
    "RES-F3-TANK": "COM-7d0a2539-e2b6-4c77-b04a-d22956f47baf",
    "RES-F3-SATURATION": "COM-4a163fb0-43b8-45b1-b946-50faa4d66659"
  }
}
```

complete=True

## 水箱结论与饱和边界

固定章节：`{"locator": "", "relation": "references", "revision": 2, "sha256": "89c35f26d30d3631b2de614b63a345dc70729cc21a053fff90575a15a3efff69", "target_id": "MEM-fdc54497-ca64-52d2-a9a2-48b3e188f6bb", "target_kind": "record"}`

原未饱和、无延迟模型的误差指数衰减结论保留其适用条件。新固定输入给出目标 $h_r=2\,\mathrm{m}$、出流系数 $c=0.1\,\mathrm{m^2/s}$、泵流量上限 $q_{max}=0.15\,\mathrm{m^3/s}$。所需流量 $q_{req}=ch_r=0.20\,\mathrm{m^3/s}>q_{max}$，目标无法维持；持续饱和平衡 $h_{sat}=q_{max}/c=1.5\,\mathrm{m}$。$q_{req}$ 为目标所需流量，$h_{sat}$ 为持续最大流量的平衡液位。仅增大增益不能突破泵上限。应先检查可达性，再在相应分段模型中分析；其他目标、延迟、噪声和非线性仍需独立验证。本报告只保存合成代数分析，无实验或科学认可。

依据：`[{"locator": "", "relation": "references", "revision": 1, "sha256": "9e9ce11f064bd7d031b3533790a362fa8410d7916e2412963cfa7d54f1c6563d", "target_id": "MEM-d8f598be-5b56-539f-ab3e-c53cfbb8d17a", "target_kind": "record"}, {"locator": "", "relation": "references", "revision": 2, "sha256": "a67f152795f1faaea2adfe8d786ada6ac2db796972570e25f3833c045ad725a2", "target_id": "MEM-2810407a-91e3-5114-b909-9a737b5e7885", "target_kind": "record"}, {"locator": "", "relation": "references", "revision": 1, "sha256": "8780b85874388753acbc846a22c1b4d20d68234dac9040ab8b8d2c15627bdada", "target_id": "MEM-6f7931dc-84bc-510e-b865-60a6d530e3ef", "target_kind": "record"}]`
