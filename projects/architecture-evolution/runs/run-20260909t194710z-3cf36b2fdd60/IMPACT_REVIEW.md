# 本轮模块与文档影响检查

Run：`RUN-20260909T194710Z-3CF36B2FDD60`。范围为表示查询首期 P0–P6 实现及实际继承审计修复；历史设计原文和已有业务记录保留。

| 对象 | 处理 | 原因与入口 |
|---|---|---|
| 查询契约、Reader、协调器、账本、Writer | 已实现并补反例 | `automation/scripts/material_query/`；固定身份、局部依据、授权交集、累计预算、降级、幂等与索引补偿 |
| 规范记忆契约与来源关系 | 增量兼容修改 | 结构化知识 facets、关联差异和关系类型；旧 v1/v2 不强制补写或提高可信状态 |
| CLI、HTTP、工作台 | 已接通并构建 | 六种表示、范围树、选择/组包、加深、维护任务包；实际 partial 故障保留回归 |
| 用户指南和根 README | 已重审并同步 | `README.md`、`ARCHITECTURE.md`、`docs/MATERIAL_QUERY.md` 说明概念、入口、目录维护、已有知识接入和限制 |
| 起始上下文与后续计划 | 已同步 | `context/START_HERE.md`、`context/NOW.md`、根待开发计划及 Project 的 PLAN；区分历史设计与当前实现 |
| Skill | 新增三个入口并安装检查 | material-query、association-exploration、semantic-maintenance；工作流源与轻量发现入口配套 |
| 公共继承设计 | 已保留旧版并逐项映射 | `docs/design/representation-query-v0.2/`；不可将 43 方法映射推定为所有可选策略实现 |
| 测试目录与选择 | 登记新增功能和真实故障 | catalog revision 46；quick-v2/full-v4 及各次失败/补测回执分别保存 |
| Windows 安装和发行边界 | 已更新清单与共享旧工作区 fixture | 维护计划等工作数据加入保护清单；真实 setup 预览、升级、重复升级、恢复与坏输入拒绝 |
| Python 锁与标准模型 | 检查，无需变更 | 固定锁和模型指纹未变；前端仅新增开发类型依赖，使用端使用已构建资源 |
| 项目分层记录与双文稿 | 本轮另存实际实现章节 | 公开预检/提交/回读保留旧修订；固定验证报告和源正文，不重写旧设计为已实现 |
| 模块影响图 | 更新到版本 2 | `projects/architecture-evolution/context/MODULE_IMPACT.md` 保存实际依赖与职责 |
| 企业服务、万条规模、第二台机器 | 未执行 | 超出本次执行范围；不由合成案例或本机升级结果外推 |

根规则与安全边界经重审无需放宽。规范数据仍由原事务管理；原件只读，公共发行不携带本 Project 或本机来源登记。没有发布 Release、生成模型更新包或改写既有 Git 提交。

实际软件结论见 `FINAL_VALIDATION.md`；实际 AI、自查图片与人工入口在本 Run 的最终 README 中汇总。保存记录、执行成功与结论复核分别记载。
