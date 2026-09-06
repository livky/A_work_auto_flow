# 分析 Runbook

本清单用于正式分析；零碎探索可在同一个任务级 Run 追加步骤，不必每个 shell 命令单独建 Run。详见工作区 `context/MEMORY.md`。

## 新建 Run

```powershell
.\automation\workspace.ps1 new-run --title "本次分析目的" --module MOD-ID --research RES-ID
```

## 运行前

- [ ] 问题、假设、成功标准和非目标明确
- [ ] 数据资产与契约已确认，原始数据只读
- [ ] 路径、时间窗、字段和采样范围受控
- [ ] 环境、依赖、代码版本、参数和随机种子可记录
- [ ] 输出写入新位置，不覆盖原始数据或历史 Run

## 运行中

- 保存结构化日志和质量检查结果。
- 每个过滤、聚合、对齐、标定和单位变换都可解释。
- 候选根因同时保存支持证据与反证。
- 大数据先用可复现采样验证逻辑，再扩展到全量。

## 运行后

- [ ] `run.json` 状态和产物已更新
- [ ] 补充 keywords、question、conclusion、适用范围；执行状态与 review.status 分开记录
- [ ] 实际消费的上游 Run 填入 parent_run_ids；复核变更使用 review-run 保留历史
- [ ] 关键指标含单位、分母、时间窗和不确定度
- [ ] 结论写明适用范围和未决问题
- [ ] 图表可追溯到脚本、参数与数据引用
- [ ] 需要时创建 ADR、复盘、模式或报告 brief
