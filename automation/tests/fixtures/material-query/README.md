# P0 材料查询运行契约样本

全部内容为合成输入，不引用业务库；JSON 中的 MEM、SRC、CLM、COM、QMAT 是接口示例身份，不能当成真实存储已经存在的记录。需要真实提交与版本回读时使用 `automation/tests/material_query_fixture.py` 的 F1。

| 文件 | 用途 |
|---|---|
| query-valid.json | 六种类型的完整 QueryRequest 正样本；包含正式适用范围、章节固定引用和显式回退 |
| query-invalid.json | 16 个实际拒绝样本：未知字段、bool/int、负预算、类型枚举、空问题、时间、正式范围和回退冲突 |
| result-valid.json | Result[SearchReceipt] 的 ok/partial/rejected/cancelled/failed 各一例；有值时验证嵌套 Candidate/FixedRef |
| result-invalid.json | 五种状态各一反例：未知包装字段、不符合绑定类型的 value、错误 warnings、布尔预算和缺必需字段 |
| fixed-refs.json | record/file/owner/claim/representation 五种身份的正样本；非法修订及指纹由测试做受控变换 |

文件外层 `id`、`input`、`expected_code` 是测试配方；只有 `input` 送入真正的 `material_query.validation.parse`，不把配方元数据传给产品。

运行：

```powershell
.\automation\python.ps1 -m unittest discover -s automation/tests -p test_representation_contracts.py -v
```

测试运行实际注册表、解析器、旧引用适配器、Ledger 和 JSON/TypeScript 生成器。受控产物与本次 `rendered()` 比较，不固定整个文件哈希，允许父任务继续增加合法 DTO；`--check` 漂移故障仅在新临时目录中注入，验证它返回非零且不覆盖文件。当前环境没有额外 jsonschema 包，本组不声称完成独立 Draft 2020-12 标准实现的 schema 验证。

## 覆盖边界

| Q 用例 | 本组实际覆盖 | 仍需对应集成验收 |
|---|---|---|
| Q01、Q02 | 六种注册定义可读、未知类型/版本拒绝、定义读取无文件 IO | 应用/HTTP 能力发现 |
| Q05、Q68 | 空问题、未知字段、严格包装和数值规则的运行拒绝 | 动作路由、策略注册与 UI 错误呈现 |
| Q06 | 解析后 null 与空集保留区别，排除信息不丢失 | 授权交集及所有召回通道的排除行为 |
| Q09 | RFC3339、时区与区间顺序校验 | 数据查询的左闭右开实际筛选 |
| Q20、Q66 | 五种固定身份、哈希/修订约束、旧六字段转换和错误脱敏 | 固定旧版回读、旧 API 完整结果兼容 |
| Q23、Q28、Q71 | 实际 Ledger 的零/刚好/超额、取消、累计活动和用户等待；使用假时钟，无真实 sleep | 真实读取/组包的计量、TTL、并行提供器与端到端取消 |
| Q72 | 实际解析六类型及五状态正反样本；生成器重复输出、受控 JSON/TS 一致与真实漂移检测 | 浏览器类型使用、全接口响应样本、升级后回读 |

这组是 P0 软件契约验证，不能代替检索质量、实际 AI、科学复核、浏览器或真实 setup 升级结果。预期与实际通过状态由测试运行回执分别保存。
