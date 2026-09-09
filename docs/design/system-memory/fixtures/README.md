# 合成材料与验收配方

全部为 AI 构造的 SYNTHETIC ONLY 软件测试材料，不是公司数据、真实实验或已确认经验。文件留在本目录，不导入正式 research、runs、knowledge 或核心算法库。

## 已准备内容

| 文件 | 内容 |
|---|---|
| records.json | 23个业务对象（八类）、8个旧Run配方、48条记忆/辅助记录、8个合成复核配方 |
| sources/ | 8个主题原始文本和1个同条件冲突变体；均明确标注合成 |
| negative-drafts.json | 16个反例：层级、类型、属性、状态、引用、权限、原件覆盖等 |
| scenarios.json | 16个场景及记录关联，包括并发、存储故障、关系图、检索、UI和升级 |
| variants.json | 明确的图边/预期邻居、四类失败、故障点、状态序列、规模与API结果配方 |
| queries.json | 48条人工可读的AI合成检索标注：32开发、16留出，按规范ID和边界评价 |
| ai-cases.json | 12张给AI执行的固定任务卡，包含必须满足与禁止结果；每卡在独立会话重复3次 |
| acceptance.json | 115个产品测试点的前置、操作、断言、返回码和证据要求；全部not-run |
| work-packages.json | 14个任务的输入依赖、交付物、步骤、位置及测试ID |
| fixture-manifest.json | 固定输入文件SHA-256和规模；用于检测配方/留出集被修改 |
| verify_plan.py | 仅使用Python标准库的计划/素材自检，不能替代未来产品测试 |

## 配方与正式提交格式的区别

这些是可重复测试的seed recipes，不是已提交的MemoryRecord。W00实现materialize转换层，W01实现产品schema；两者不能相互冒充。

1. 在临时工作区复制sources原始文本并登记SRC ID，按实际字节计算SHA-256。
2. 用既有创建函数/测试帮助构造八类合法旧对象。legacy_runs中实际代码、环境、输入产物hash和封存字段由测试帮助填写；不把配方里的描述字符串当正式复核。
3. 通过合成授权验证流程创建旧CLM的复核与封存状态，明确只验证软件行为。review_recipes是测试前置，不是AI可直接写入的accepted字段。
4. records的record_id用于注入固定测试身份；actor变为请求actor，时间与revision/hash由服务计算。顶层occurred_at是配方排序提示，不作为全部产品记录的公共字段。
5. 配方RefSpec的target_id/revision/relation/locator转换为正式Ref：MEM目标固定revision，旧owner/CLM/文件读取并填真实指纹；source payload中的source_id转换成source_ref。缺失的依据在负例中明确制造，正例不得留下临时符号。
6. experience payload中的keywords移入公共keywords属性；consolidation的空basis_heads在构造时绑定本次对象HEAD；所有当前指针由setup场景明确设置，不靠“创建时间最近”猜测。
7. 新的MEM层内引用可作为同批client_key提交。单批只写一个owner；跨owner按依赖顺序提交，并保存每个回执。
8. SC-HISTORY给map补齐目标/路线/问题引用；SC-EVIDENCE建立文件→旧Run/CLM→经验→地图→报告的显式依赖。variants定义图节点A–F在临时目录中映射到六个不同MEM ID。

负例的replace是测试输入修改配方，点号路径表示嵌套字段。NEG-PATH送到路径解析器；NEG-CLAIM送到review入口；NEG-SENSITIVITY中的source_sensitivity修改临时授权上下文；NEG-READONLY构造非法动作，其余转换为对应草案字段。不得把这些测试辅助键带入正常生产请求。每个反例都关联验收用例。

所有故障、原件变化和损坏只作用于临时副本；本目录sources作为固定输入保持只读。未来扩展需要修改配方版本与manifest，并记录原因，尤其不能在观察留出结果后静默改标注。

## 运行自检

仓库根执行：

```powershell
.\automation\python.ps1 docs/design/system-memory/fixtures/verify_plan.py --self-test
```

输出JSON，退出0表示计划输入关联与完整性通过；1表示校验失败，2表示参数/读取错误。不会启动模型、联网、写业务目录或执行计划中的产品用例。

`--freeze`仅用于首次创建本版本manifest：正常输入检查通过后，以独占创建方式写入；已有清单不覆盖。更新版本时保留旧清单，使用新的`--manifest`文件名冻结，再更新使用说明。默认运行是只读的。

## 评价纪律与限制

- 先用32条开发查询调试，16条留出查询仅在W13最终评价使用。当前标签由AI按合成材料编写，尚无人工业务标注。
- AI任务每卡3次，共36次；每次满足所有must且forbidden均未发生才通过。保存模型/Skill/输入版本和外显调用/结果，不采集私有思维链。
- 正文正确性、类比是否合理和真实业务价值不能通过JSON格式检查证明。
- 当前只已生成配方和静态文本。临时工作区物化器、产品schema、115个产品用例及模型/浏览器/真实setup运行都属于后续实现和验收。
