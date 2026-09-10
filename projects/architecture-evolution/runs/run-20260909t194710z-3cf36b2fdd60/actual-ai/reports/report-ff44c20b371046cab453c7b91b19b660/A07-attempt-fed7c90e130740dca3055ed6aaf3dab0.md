# 表示选择与完整性缺口

## 任务

通过材料查询选择普通摘要与对应全文，实际阅读组包内容，再排除一个必要定义，解释可用信息及缺口。保存真实请求、固定来源和阅读判断。

## AI自查

## 已保存可读结果

- [A07实际阅读分析](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/AI-ANALYSIS.md>)

## 逐项观察

- A07-E1：meets — 按相关性判断选择unit_digest，再为公式/变量核对选择full；六次公开调用均保留真实请求与组包结果，未调用自动语义生成。
  证据：delivered/definitions.md; calls/call-4a61ae9bb3cb49749cf45fdf4fca376d/result.json; calls/call-a4d7f5b72bfd41cfbef26cb843c0f5e3/result.json; AI-ANALYSIS.md
- A07-E2：meets — 摘要完整只相对摘要配方成立；正文与必要定义均在full中实际读到。章节摘要候选needs_generation且组包partial，排除定义使整个依赖章节省略，未伪称得到直接块。
  证据：delivered/tank-summary.md; delivered/tank-full.md; calls/call-0651848342b546c6ac2b7715b52ac1bd/stdout.txt; delivered/tank-excluded-definition.md; AI-ANALYSIS.md
- A07-E3：meets — 排除同时写入scope和scope_ceiling；固定r1及SHA记录。250输出预算仅交付31字符引言且省略完整块，没有扩预算。实际阅读按summary/partial/full分别声明并存快照。
  证据：authored-requests/tank-excluded-definition.json; authored-requests/tank-small-budget.json; delivered/tank-small-budget.md; reads; AI-ANALYSIS.md

## 限制

- 同一AI编写合成前提并执行，连续上下文；非盲测或独立题集。
- 排除后返回保守的零候选和概括缺口，未返回细化依赖原因。
- 预算组包stop_reason为null，须综合warnings/gaps/complete判断。
- 仅本机合成文本；未做现实实验或科学复核，人工待审。

## 实际调用与阅读

- [call-0651848342b546c6ac2b7715b52ac1bd/result.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/calls/call-0651848342b546c6ac2b7715b52ac1bd/result.json>)
- [call-3cf2ca12cc5b40b39f2d2f8a46e63243/result.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/calls/call-3cf2ca12cc5b40b39f2d2f8a46e63243/result.json>)
- [call-4a61ae9bb3cb49749cf45fdf4fca376d/result.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/calls/call-4a61ae9bb3cb49749cf45fdf4fca376d/result.json>)
- [call-969484b4d00848f2bbb04f4041d8e10c/result.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/calls/call-969484b4d00848f2bbb04f4041d8e10c/result.json>)
- [call-a4d7f5b72bfd41cfbef26cb843c0f5e3/result.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/calls/call-a4d7f5b72bfd41cfbef26cb843c0f5e3/result.json>)
- [call-dd0e19d8d7a3471788f36f7c9047d9c3/result.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/calls/call-dd0e19d8d7a3471788f36f7c9047d9c3/result.json>)
- [read-52118d3078b84fe88b1cf98b16a9588b/event.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/reads/read-52118d3078b84fe88b1cf98b16a9588b/event.json>)
- [read-61b3139ad53a41539afce048b3e6f74c/event.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/reads/read-61b3139ad53a41539afce048b3e6f74c/event.json>)
- [read-9d309f9e055b4c3faa9214791bb7678d/event.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/reads/read-9d309f9e055b4c3faa9214791bb7678d/event.json>)
- [read-a27b898c8edc4cbf9596a39450c1b6ab/event.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/reads/read-a27b898c8edc4cbf9596a39450c1b6ab/event.json>)
- [read-f0d21c865f77447aad93bb121fb9e879/event.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/reads/read-f0d21c865f77447aad93bb121fb9e879/event.json>)
- [read-f535759090ec4622830c405dc176c8ce/event.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/reads/read-f535759090ec4622830c405dc176c8ce/event.json>)
- [assessments/assessment-4867088575974f52ad4d933d84707dc5.json](<../../A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/assessments/assessment-4867088575974f52ad4d933d84707dc5.json>)

## 人工审查

待审查。请记录意见及所审固定版本；本工具不代填认可。
