# 材料关系图调研与结构核对

Run：`RUN-20260907T063633Z-159B86592CDD`。执行：succeeded；结论复核：not-reviewed。

结果见 [综合建议](../../research/material-relationship-view/SYNTHESIS.md) 与 [来源台账](../../research/material-relationship-view/EVIDENCE_LEDGER.md)。本次为工具调研和适用性分析，未实施工作台图功能。

[只读盘点](relationship-audit.json) 保存既有索引和证据关系数量、输入代码指纹。正式图包含本次新建的研究和 Run，索引快照尚未包含本次研究；合成数据与正式记录分开。盘点不刷新索引、不加载模型。

复现盘点（输出会反映复现时的材料状态）：

```powershell
.\automation\python.ps1 runs/run-20260907t063633z-159b86592cdd/inspect_relations.py
```

没有真实业务材料、外部产品安装对比或图交互性能测试。研究完成不表示建议已获复核。
