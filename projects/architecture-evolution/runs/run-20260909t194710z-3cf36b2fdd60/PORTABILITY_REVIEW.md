# Windows x64 发行与升级边界独立审查

Run：`RUN-20260909T194710Z-3CF36B2FDD60`。审查时间：2026-09-10 05:40（UTC+8）。审查者：AI `memory_review`。机器回执：[portability-review.json](portability-review.json)。

本轮只读核对通过，保留公共源码来源登记这一发布前条件。未发现新增材料查询模块、契约、技能、公共继承基线或预构建资源缺失。此次没有生成、检查或发布最终源码 ZIP，也没有代替主任务执行真实 `setup.cmd`。

## 实际结果

| 核对对象 | 观察结果 | 依据与限制 |
| --- | --- | --- |
| 框架升级清单 | 427 个可替换框架文件、37 个补缺文件；本次 50 个必要路径全部存在 | 实际调用 [deployment.py](../../../../automation/scripts/deployment.py) 的 `framework_files/seed_files`；后者在目标已存在时不覆盖 |
| 材料查询运行时 | 22 个 Python 文件全部纳入清单 | 从 `automation/scripts/material_query/*.py` 实际枚举后比对；未按预想文件数量判断 |
| 契约与前端 | JSON schema、生成 TypeScript 以及查询前端源码均纳入 | `generate_types.py --check` 实际退出 0，`changed=[]` |
| 三个技能 | `material-query`、`association-exploration`、`semantic-maintenance` 的完整 workflow 与轻量入口均纳入 | workflow 随框架更新；`.agents/skills/*/SKILL.md` 属于补缺，保留已有用户修改；安装器也在清单 |
| 公开继承基线 | 15 个配套文件完整；原 12 文件及公共副本指纹均匹配 | 独立运行 `check_inheritance.py` 退出 0：13 组、43 方法、26 项旧验收、74 个 Q 案例；仅证明结构、指纹和导航 |
| 公开运行状态 | 43 个实际方法落点；维护状态已更新为 `delegated:maintenance.status` | 初次读取的旧“未实现”说明已由负责代理修正，复读机器映射包含实际 11 项状态回归 ID；无 `unsupported:` 占位不等于所有旧语义都已完整验证 |
| 预构建资源 | 44 个源码、65 个构建文件全部 SHA-256 匹配；组合源码指纹匹配 | 实际读取 [asset-manifest.json](../../../../automation/ui/workbench-assets/asset-manifest.json) 并逐文件核验；使用端不依赖 Node 或 node_modules |
| 业务与运行目录 | 升级清单没有 Project/Research/Core/Run 实例、`.local`、查询历史、向量库、模型目录或 node_modules | README、规则和模板保留；前端 `src/generated` 下的受控 TypeScript 是源码，不能误判为业务缓存 |
| 公共源码排除规则 | Project/研究/Run 的实例目录受 `export-ignore` 排除；公开 docs 与运行源码没有被排除；`.local/material-query/plans` 被 Git 忽略 | 验证实际属性与 Git 跟踪集合；不能据此声称尚未生成的最终 Git archive 已验收 |
| 已有维护计划 | 共享升级 fixture 已通过真实公共 `maintenance-plan` 保存未审查计划；全部文件哈希和目录进入保护清单 | 审阅 [upgrade_fixture.py](../../../../automation/tests/upgrade_fixture.py) 及真实 `setup.cmd` 回归调用链；本独立审查没有执行该升级测试，实际结果由主任务记录 |

## 依赖和模型

本 Run 保存的开始时 Git 状态没有 Python lock 或模型 manifest 修改，当前 HEAD 仍为 `647d7862331e283439d06d42ec01d3882a32d163`。此次进一步比较了该提交原字节：

- `services/qdrant/requirements.lock.txt` 完全相同，SHA-256 为 `5bc0ebab661be8031755b4852953ae9dc054f451ab18def291f5eed078d3d1e4`。
- `services/qdrant/model-manifest.json` 完全相同，SHA-256 为 `8bd7a882766c881dd29766c89e7bacfba32deb98308b5d69cee4b3e453c5476f`。标准 multilingual MiniLM 模型的 8 个登记文件已按该清单逐个校验，没有不一致。
- 前端 `package-lock.json` 有实际变化：新增开发类型依赖 `@types/node 22.10.2` 和 `undici-types 6.20.0`，生产运行依赖未变。这两项不是 Python/模型依赖包变更，也不要求使用端安装 Node。

开始时的 [baseline-fingerprints.json](baseline-fingerprints.json) 没有专门保存依赖指纹，因此这里明确使用“开始时 Git 状态 + 相同 HEAD 的字节比较”，不虚构预先冻结的依赖快照。所有本次核对文件及实际指纹保存在机器回执。

## 发布前条件

当前本机 `retrieval/sources.json` 保存 22 个登记，而 HEAD 中的公共模板为 0 个；该文件在开始时已经有修改。这些是现有业务登记，必须保留，不能为了发行清空。本次没有修改或删除这些登记，也不扩展安装逻辑。安装器的 `seed_files` 会把源码目录的这份文件用作新工作区补缺输入，因此未来公共发行须从受控空模板或干净源码准备；不能把当前 seed 枚举当成脱敏发布工具，不能把本机登记提交或复制进公开包。旧目标工作区的已有登记继续原样保留。

主任务的真实 `setup.cmd` 测试使用已有登记的隔离目标，以完整保护清单逐文件核对哈希。本审查记录测试结构和职责，不替主任务声明该次执行已经通过。

最终发布还应针对已推送的配套源码提交核对实际 ZIP 文件内容和哈希。这个条件已告知主任务，本轮未开展对外发布。

## 验证边界

实际执行的是清单枚举、文件指纹、Git 属性/跟踪集合、契约生成一致性和继承结构检查；审阅了计划保护 fixture 的真实调用和逐文件保护逻辑。真实旧工作区升级、重复升级、恢复及完整回归由主集成任务单独给出运行证据。第二台物理机、完整离线依赖包安装、实际 AI 语义审查、模型业务有效性和人工验收均不因本审查通过。

本次没有修改生产代码、依赖、来源登记或原始材料，仅写本报告和机器回执。
