# P0 设计继承与公共基线回执

本子任务完成 v0.1 到 v0.2 的逐项设计继承清点，没有修改产品运行代码。实现与验收的保留义务由本期继续落实，不能将本回执解释为 P0 全部退出条件已经满足。

## 产物与范围

- [继承说明](../../../../docs/design/representation-query-v0.2/INHERITANCE.md)：13 个功能/控制组、43 个方法、C01–C26 逐项对应，列出明确修订及最小字段/签名。
- [机器映射](../../../../docs/design/representation-query-v0.2/inheritance-map.json)：保留每个原方法的前后置条件、错误和调用要求，并标明实现落点、Q 关联与未核验义务。
- [公共基线](../../../../docs/design/representation-query-v0.2/baseline-v0.1/PUBLIC_BASELINE.md)：原 12 文件及其指纹；只在公共副本重定位导航、检查命令和未分发 Run 的说明入口。原 Project 12 文件未变。
- [基线静态检查](inheritance-baseline-check.json)、[继承覆盖检查](inheritance-coverage-check.json)：实际执行的独立结构回执。

## 实际结果

原基线静态检查通过：40 个领域方法、3 个共享执行控制方法、72 个数据结构、12 个正反结构请求。继承覆盖检查通过：G01–G12 与 X01 完整、43 个方法无缺号或重复、C01–C26 全部关联真实存在的 Q ID；12 个源文件/副本指纹及声明导航变换一致，46 条本地链接目标存在。

设计覆盖按真实文字判定：16 条 C 有直接对应，10 条需补专门断言；两者的产品测试状态均为 not_run。本子任务没有登记虚构测试 ID，没有延期或删除旧方法。

需补断言的旧用例：C06（显式回退）、C07（综合贡献来源闭包）、C11（分页事件缺口）、C14（降级贯穿最终材料包）、C15（融合/重排器替换）、C17（同名实体与错误路径）、C19（扩大语料与加深表示独立）、C23（独立阅读视图不写知识）、C24（对新内容追加适用复核）、C26（底层后端替换与硬语义拒绝）。详细输入和预期见继承说明，不把相邻 Q 的标题当成已覆盖断言。

## 本期必须关闭的字段和签名差异

INH01–INH12 分别覆盖：完整固定身份/旧 Ref 关系；来源/包含/排除/时间/确信/适用域筛选；逐通道命中、claim 评估及水位；变化和索引生命周期；独立排序；查询策略/新鲜度/扩展；历史和阅读视图；维护状态/完整提交回执/新复核；分项预算；结构化错误与读取依据；关系枚举和有序路径；表示注册与构建边界。

这些均保留为本期义务，运行层尚待逐项验证。已明确按 v0.2 替换的只有相应具体行为：类型与实例拆分、搜索后显式组包、表示别名、活动墙钟/独立 TTL、首期无同查询加额度，以及进程重启返回 EXPIRED。不得据简化 DTO 静默忽略其余旧字段。

## 执行记录与限制

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.\automation\python.ps1 docs/design/representation-query-v0.2/baseline-v0.1/check_contracts.py --out projects/architecture-evolution/runs/run-20260909t194710z-3cf36b2fdd60/inheritance-baseline-check.json
.\automation\python.ps1 docs/design/representation-query-v0.2/baseline-v0.1/check_inheritance.py --out projects/architecture-evolution/runs/run-20260909t194710z-3cf36b2fdd60/inheritance-coverage-check.json
```

两条命令均退出 0。检查器可在没有 Project 实例的公共目录布局下运行；缺原件时会明确记录仅核验公共副本。本轮未执行公共发行/真实 setup 升级、运行后端/权限/检索/维护行为、实际 AI 或人工/科学验收。旧 Run、规范记录和冻结 fixture 未修改。全工作区 refresh-index/validate 及最终发布边界由本轮集成阶段执行，避免和并行运行代码修改争用派生索引。
