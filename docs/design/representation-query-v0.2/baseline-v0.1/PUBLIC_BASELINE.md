# v0.1 公共继承基线说明

本目录保存抽象接口 v0.1 的公共设计依据，供 [v0.2 继承映射](../INHERITANCE.md)和实施验证使用。它包含 40 个领域方法、3 个共享执行控制方法、72 个数据结构及 12 个正反结构请求；不是已经接入产品的运行模块。

原始来源目录为 `projects/architecture-evolution/design/interfaces-v0.1/`，原契约记录于 `RUN-20260909T164914Z-D20A9406384A`，后续表示提案的原日期和状态保留在各文件中。公共复制与继承检查属于 `RUN-20260909T194710Z-3CF36B2FDD60`。原文中的“本轮”“当前”“下一轮”均属于原设计时点，不代表本次产品状态。

## 复制范围与指纹

原目录的 12 个文件全部复制。[source-manifest.json](source-manifest.json)保存每个原路径、原 SHA256、副本 SHA256 及明确导航调整。Python、JSON、两份生成目录均与来源字节相同；手写 Markdown 只调整公共目录链接、检查命令以及未分发历史回执的说明入口。原 Project 文件没有修改。

本说明、source-manifest.json 和 check_inheritance.py 是公共继承配套文件，不属于原 v0.1 的 12 文件；不可据此改写原签名版本。原 check_contracts.py 只核对设计和合成结构，不能代表真实后端符合 C01–C26。

## 未随公共包分发的研究回执

原 IMPLEMENTATION.md 引用：

- `projects/architecture-evolution/runs/run-20260909t155125z-2961bdf175a8/sources.json`：原来源台账。
- `projects/architecture-evolution/runs/run-20260909t155125z-2961bdf175a8/DISCUSSION.md`：原讨论稿。

Project 与 Run 实例不随公共源码包分发。本目录保留原 Run ID 和来源指纹，不复制研究实例，也不伪造缺失的研究/运行/人工验收材料。原文的外部公开文献链接仍保留；本次迁移没有重新验证其研究结论。

## 使用与维护

从工作区根目录执行：

```powershell
.\automation\python.ps1 docs/design/representation-query-v0.2/baseline-v0.1/check_contracts.py
.\automation\python.ps1 docs/design/representation-query-v0.2/baseline-v0.1/check_inheritance.py
```

原基线保持固定，不在本目录执行 --write 来改变历史生成目录；修改运行契约或行为时更新 v0.2 及继承映射，确需修订旧契约时新建版本。公共副本内所有必要设计材料均可本地阅读，产品运行无需 Project 实例。公共发行包的实际收录、安装升级及恢复仍须 P6 验证。

