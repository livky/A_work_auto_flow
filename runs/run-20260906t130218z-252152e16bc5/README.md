# RUN-20260906T130218Z-252152E16BC5：结构审阅与缺口验证

执行状态：已完成；结论复核状态：not-reviewed。日期：2026-09-06。

本 Run 支持[研发工作区结构评审](../../research/agent-workspace-review/SYNTHESIS.md)。判断范围是代码实现和合成场景，不是公司算法现实有效性。

## 输入与环境

仓库基线 8b54b060dd8d0366baf049f4851a40a7edd522bf。评审开始时工作树干净；本轮仅新增评审/验证记录并更新导航和当前状态说明。输入版本与 SHA-256 见 [inputs.json](inputs.json)。
Python 3.12.14，Windows 11。实际采用包装脚本选中的可用解释器；当前源码副本没有完整本地检索依赖/模型，实际安装环境没有与 requirements.lock.txt 等同的证明。

## 已执行与观察

| 检查 | 结果 | 证据 |
|---|---|---|
| 工作区 validate（开始时） | 0 错误、4 历史证据链接警告 | [validate-before.txt](validate-before.txt) |
| 现有 unittest discovery | 49 项，42 通过，7 因模型缺失跳过 | [tests.txt](tests.txt) |
| 隔离行为探针 | 四组观察完成，详见下文 | [probe-results.json](probe-results.json) |
| index-knowledge | 不成功：缺少 qdrant_client | [index-attempt.txt](index-attempt.txt) |
| 最终导航/结构检查 | 见最终校验与 run.json | [validate-final.txt](validate-final.txt) |

探针通过 CLI 和检索实现构造一次性合成目录，正常结束后清理。观察到：

1. inputs/artifacts/quality_results 为空的 succeeded Run，通过结构校验。
2. 撤回 Run 自身有风险标记，跨研究综合没有继承，仍以全文装载。
3. restricted 研究卡的综合正文可索引，索引元数据无 sensitivity。
4. 同一逻辑相对位置换根路径后 SRC-ID 改变。

以上是边界观察；其中现有系统对原 Run 和同目录材料的风险提示已正确实现。没有尝试真实越权读取。

## 复跑

在当前仓库根目录执行：

```powershell
.\automation\python.ps1 runs/run-20260906t130218z-252152e16bc5/probe_gaps.py --output runs/run-20260906t130218z-252152e16bc5/probe-results-recheck.json
.\automation\python.ps1 -m unittest discover -s automation/tests -v
.\automation\workspace.ps1 validate
```

[探针脚本](probe_gaps.py)只依赖标准库和当前框架。重跑使用新结果文件，避免覆盖原始证据；合成 Run 随机 ID、时间和临时路径可以不同，比较各观察字段语义。

## 解释与限制

完整评审完成不等于索引可用；跳过 7 项不能视为本地模型/OCR 验证成功。没有真实业务问答、领域验收数据或外部框架实机比较。当前报告建议未作人工业务确认，也未通过任何将其晋升为 accepted 的授权流程。

