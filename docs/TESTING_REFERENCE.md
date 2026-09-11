# 测试执行参考（按需）

测试选择标准见 [TESTING](TESTING.md)。本页提供现有工具和实际 AI 场景，不要求每次开发按顺序执行所有命令。

## 轻量定向检查

可直接执行对应的 unittest 模块/方法、组件用例或浏览器场景。任务计划/摘要记录目标、实际测试入口、输入与源码版本、结果和限制。文档调整检查链接、现行定义、历史保护和需要保留的命令即可，不为改措辞新增匹配文字的单元测试。

```powershell
# 示例：替换成实际受影响模块；不是每次开发固定必跑项
.\automation\python.ps1 -m unittest discover -s automation/tests -p test_material_scope.py -v
.\workbench.cmd testing audit
```

新增行为测试或真实故障场景应登记到 [catalog](../automation/testing/catalog.json)。`audit` 只盘点未分类/失效测试，`coverage` 只说明定义或选择覆盖；二者都不是执行通过。

## 维护基线依据

准入、复审与退出标准见 [TESTING](TESTING.md)。`testing register` 只为新发现用例登记能力，默认 `quick=false、full=true`；它没有晋升基线的参数。需进入基线时受控编辑 catalog 的 `quick` 与 `baseline`，同步 revision/history，保留旧版本；`baseline` 的字段是审查依据，选择器仍只读取原有选择字段。

按本次影响核对 `risk`、`reason`、`review_triggers` 和复审来源，变更前后比较 quick/full 选出的 ID。`testing audit` 不能替代这个判断，也不校验这些说明字段。只补依据时成员应保持一致；变更成员时记录覆盖理由、替代关系及实际验证。历史冻结计划可能因清单指纹变化失效，需要新建选择版本，不能手改旧指纹。

## 使用 quick / full 执行器

当前工具只支持 `quick`、`full`：quick 包含 catalog 的固定门槛，再加入影响能力；其中已有跨栈和真实 setup 场景，**不能把它说成仅运行本次几个测试**。直接定向执行才是当前可用的更小检查方式。本轮规则精简没有修改选择器。

```powershell
.\workbench.cmd testing prepare --tier quick --goal "本次目标" --capability research --acceptance "N01:本次行为标准" --out .local/testing/task/selection-v1.json
.\workbench.cmd testing validate --plan .local/testing/task/selection-v1.json
.\workbench.cmd testing run --plan .local/testing/task/selection-v1.json --out .local/testing/task/attempt-01
```

上述能力为示例，实际参数可用 `--help` 或 `testing catalog` 查看。复杂任务可把路径放到既有 Run 的 `testing/`。选择文件及执行目录必须是新路径；重试用下一目录，范围变化用 `testing update` 保留前版。

`--capability` 可重复；`--add-test` 添加已登记项；`--actual-ai` 只声明所需 AI 场景；`--reuse-evidence` 保存复用依据。`--exclude TEST_ID=原因` 不能消除固定门槛；已选未运行仍为 incomplete。新增测试可用 `testing register --module 实际模块 --capability 实际能力 --reason "原因"` 分类，再核对 catalog。

full 包含全部普通 Python/组件/浏览器功能。vector/OCR、完整依赖分发和规模检查另有依赖及授权；缺模型、跳过或没有机器回执都不是 full 通过。万条规模目前暂缓。前端构建命令见 [WORKBENCH_DEVELOPMENT](WORKBENCH_DEVELOPMENT.md)，真实 setup/离线矩阵见 [UPGRADE_TESTING](UPGRADE_TESTING.md)。

执行器输出 selection、results、README、实际命令、逐阶段结果和日志。`passed / incomplete / failed` 与超时、中断、skip 分别保留；零测试或缺结果不能被退出码 0 掩盖。Windows 原子写冲突保留 write-events/pending/失败回执，不覆盖旧结果。

## 实际 AI 场景

| ID | 实际要验证什么 |
|---|---|
| A01 | AI 编写有来源记录，公开预检/提交并固定回读 |
| A02 | 真正独立上下文只从研究入口恢复目标、缺口并继续 |
| A03 | 写出可独立理解的技术单元、完整块与章节 |
| A04 | 两份文稿共用固定依据，全文、简版和边界一致 |
| A05 | 来源局部修订后维护受影响内容，旧版仍可回读 |
| A06 | 跨研究检索分别识别适用与不适用的经验 |
| A07 | 选择表示、固定候选并判断缺口，不虚构内容 |
| A08 | 结构联想说明共同点、差异及负例，不冒充科学支持 |
| A09 | 新反证没有旧边时仍检查影响并做真实语义维护 |

按影响选择场景，不默认每轮全部重做。`automation/testing/ai_review.py --help` 给记录工具；模板在 [automation/testing/templates](../automation/testing/templates/)。程序只能记录和机械核对，不能预填 AI 的正文、阅读情况或自评。

保留实际任务/预期、输入与 Skill 版本、上下文身份（未知留空）、公开调用、退出码、固定回读、实际阅读与逐项判断。`execution`、`mechanical_checks`、`ai_assessment`、`human_review`、`scientific_review` 分开。人工页只展示本次必要结果，未获用户意见保持待审。

已有 Run 内需要追溯的真实回执用 `run-register` 登记即可，不重复手填 source/哈希。轻量任务可在摘要记录；不因使用本页而额外创建完整研究项目。登记与恢复细节见 [RUN_CAPTURE](RUN_CAPTURE.md)。
