# 当前状态

更新日期：2026-09-11。本页只给当前能力、限制和续接入口；开发从 [development-checks](../automation/workflows/development-checks/SKILL.md) 的六份短文档进入。技术架构与模块影响统一见 [ARCHITECTURE](../ARCHITECTURE.md)，功能定义见 [CORE](../docs/CORE.md)，细节和历史分类见 [文档索引](../docs/README.md)。

## 当前能力

- 规范记忆采用 v4 聚合兼容契约：新增研究经过 narrative、分类 experience、整体概览 overview；L1 与独立文稿仍用 v3，level=null 的文稿不占 L4。v1–v3 历史、旧 event/map 与固定字节保留。
- Run 优先属于实际 Owner，执行与登记产生 L0 追溯视图；不自动编写研究正文。
- 材料查询 v0.2 已接入工作台、CLI/HTTP 和三个专项 Skill，主入口按概览与经验/研究经过/技术内容选择来源，沿固定关联展开，保留六类表示兼容接口、范围树、组包与语义维护任务包；复用原 memory 存储。生成式模型、自动结构发现和自动维护代理未注册。
- 材料查询进一步支持标准对象类型多选、所有来源、显式历史、完整文稿去重与图示；默认当前修订、活动执行5分钟、读取16 MiB/文本8万字符。必要依据上限与直接筛选分开，可显式收紧。8个工作区 Skill 已逐项审查，3个过时未注册方法保留原文后合并退休。
- 旧材料与 memory 检索并存，共用 SQLite 文件但分表/回执；Qdrant local 有进程排他限制。工作台支持研究文稿、材料关系、证据和显式监测。
- Windows 升级使用新版 `setup.cmd --target`，保留旧业务数据及恢复回执；依赖/模型配套离线核验，自动模型迁移仍限标准名称/路径和兼容 384 维。

## 当前任务与未解决问题

Skill、文档与测试规则维护已完成，记录见[文档维护结果](../projects/architecture-evolution/plans/development-docs-refresh-20260910.md)。用户已确认后续目标：L0/L1 不变，L2 研究经过、L3 经验、L4 整体概览；“概览与经验”默认查 L4/L3，按需展开 L2/L1。按[人工验收改进计划 v3](../projects/architecture-evolution/plans/human-acceptance-improvements-20260910.md)实施；分层契约、来源查询、固定展开、反选与结束状态已实现并完成定向软件验证，任务成功进度已修正；浮点研究已实际整理为5条研究经过、1条整体概览，并补齐1条经验的固定关联；其他旧内容须逐项审查迁移。实际结果见[实施 Run](../projects/architecture-evolution/runs/run-20260910t125056z-8d1e5d9047b1/RESULTS.md)，用户复验仍待完成。

人工入口：[本地登记审计](../projects/architecture-evolution/runs/run-20260910t063103z-902da8123205/AUDIT_REPORT.md)、[操作检查表](../projects/architecture-evolution/runs/run-20260910t063103z-902da8123205/HUMAN_CHECKLIST.md)。前置问题阻塞了部分后续检查，未填项不当作通过。

后续测试规范补充：已为现有 24 项基线记录风险和保留依据，明确准入/复审/退出；该次补录成员不变，未重新执行基线。后续本轮新增10项内容链路用例，其中5项加入基线：catalog revision53，合计613项、29项固定基线；登记审计通过，不等于613项全部运行。见[维护记录](../projects/architecture-evolution/plans/testing-baseline-maintenance-20260910.md)。

## 验证边界与历史

- 表示查询的实际软件/AI整合记录：`RUN-20260909T194710Z-3CF36B2FDD60`；浮点研究读取修复：`RUN-20260910T050158Z-028371C48C3A`。文档更新不改变旧失败或验收结果。
- 本地审计已分别核对登记、固定回读与索引；历史源码指纹变化、未分发旧 Run 和 snapshot 的旧检索解析缺口仍保留，不能由索引补偿消除。
- 历史检索独立题集质量未通过；万条规模继续暂缓；人工、第二物理机和科学复核独立待审。详情从 [Project](../projects/architecture-evolution/README.md) 与 [历史状态台账](../docs/design/system-memory/STATUS.md)追溯。
- 规范来源/文稿不会自动换新，旧聊天内容不会自动撤回；没有自动远程备份、通用代码影响监听器或企业连接器。

此前层级收敛与浮点迁移见[结果](../projects/architecture-evolution/runs/run-20260910t183626z-429304f92e99/RESULTS.md)。当时 catalog revision59：618项、31项基线。

最新[七项查询优化结果](../projects/architecture-evolution/runs/run-20260910t210558z-aba265055ed3/RESULTS.md)：相关后端与契约回归、35项组件、5项真实浏览器、18项Windows升级通过；真实浮点连续正文动作完成，完整文稿1篇4图，深化保留有界反向引用覆盖partial。当前 catalog revision63：629项、33项基线，登记审计通过，并非全部执行。人工复验及第二物理机仍待审。
