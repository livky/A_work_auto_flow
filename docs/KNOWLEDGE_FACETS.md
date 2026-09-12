# 知识分类、尝试结果与置信评估

知识分类回答材料属于哪些角色、哪些实际尝试得到什么结果，以及谁基于什么证据评估了具体目标的置信程度。它与 claim 的复核状态、当前有效性分别保存和筛选；高置信度、成功尝试或分类依据不会创建 accepted review。

v4 narrative/overview及分类experience也沿用可选knowledge_facets；experience还需要knowledge_type（observation/conclusion/hypothesis/recommendation）。knowledge_type描述认识性质，roles可含method等用途，二者不是同一枚举。步骤性方法通常保存为L1，外来主张应在正文明确，分类不会自动授予复核。

## 保存位置与兼容性

v3 的 `event`、`experience`、`detail`、`map`、`document`、`document_section` 可在 `payload.knowledge_facets` 保存下列可选对象。使用原 `memory validate-draft` / `memory commit` / `memory inspect` 流程，修订遵守原 CAS 和幂等要求。

整个 `knowledge_facets` 可省略；一旦提供，内部字段须完整，不用省略字段冒充已经评估。字段属于已有 payload，参与原内容指纹。旧 v1/v2 定义保持原样，既有记录不会补填或重算哈希；要补分类，应先按正常内容修订流程生成受支持的 v3 记录。

| 字段 | 内容与约束 |
| --- | --- |
| `roles` | 多选 `fact_claim / insight / hypothesis / experience / method / principle / definition / constraint`；空数组表示尚无分类。非空必须提供 `classification_basis`。 |
| `principle_kind` | principle 的具体类型：`definition / mathematical_axiom / derived_invariant / physical_law_model / engineering_assumption`；与 principle 角色同时填写，其他情况为 null。 |
| `attempts` | 多次实际尝试，每项保存 `attempt_ref`、`outcome`、`conditions`。outcome 为 `success / failure / mixed / unknown`，不同尝试可以有不同结果。 |
| `applicability` | `description`、精确条件标签 `conditions`、禁止条件 `exclusions`、UTC 时间 `valid_from / valid_until`、固定 `subject_versions`。两个时间边界可为 null；非空区间左闭右开且开始早于结束。 |
| `counterexamples` | 固定反例引用数组；没有已知反例用空数组，不表示不存在反例。 |
| `confidence` | 每项绑定固定 `target`、`level`、`assessed_by`、含 name/version 的 `method`、固定 `basis`、独立 `applicability`、`calibrated_probability` 与 `calibration_ref`。 |
| `classification_basis` | 支撑角色分类的固定依据引用数组。 |

这里的引用统一使用既有六字段 Ref：`target_kind / target_id / revision / sha256 / locator / relation`。记录引用须有实际正修订号，所有分类引用须已有 SHA；通过公开读取取得固定引用后再提交，不能填写临时草案身份。新增字段中的全部引用仍经过原保存校验以及材料读取时的来源权限闭包。

置信度 level 为 `high / medium / low / unknown`，不使用检索排名分数。已知 level 要有固定 basis；概率非空时必须在 `[0, 1]` 内并提供固定 calibration_ref。评估保存并不代表概率已通过现实校准验收，适用范围和评估者必须保留。

## 查询与未知值

材料查询继续使用 `Scope.roles / outcomes / confidence_levels / review_states / validities`。不同字段取 AND，同一字段取 OR；null 不限制，空数组无结果。`outcomes` 对所有已保存的实际尝试取匹配，不能把失败与成功合并成一个“已验证”状态。

未保存分类时，未知值默认不满足明确筛选；`include_unknown=true` 才允许未知维度参与匹配，返回候选的 `unknown_facets` 标明这次匹配依赖的 `roles / outcomes / confidence`。已知失败、低置信度或被撤回的结论不会因开启 include_unknown 变成未知。

置信筛选检查实际固定 target：精确 claim 请求只能使用该 claim 的评估；record 请求可匹配它自己或它自身当前 claim 的评估。引用了高置信度外部来源，不会让当前记录继承高置信度。复核与有效性再与同一个 claim 交叉筛选。

没有 knowledge_facets 的旧内容只做有限、可追溯的映射：experience 类型可识别为 experience 角色，method 技术单元可识别为 method，event 非空结构化 failure 可识别为失败尝试。正文里的“成功”、程序退出码以及可能的 failure_modes 不用于猜测实际尝试结果。

## 适用条件的当前边界

当前请求的 `applicability_conditions` 必须逐个精确匹配已声明的 conditions，且不能出现在材料自己的 exclusions 中；`applicability_exclusions` 排除声明了这些条件的材料。描述正文和标签子串都不构成匹配依据。旧 experience 的 applicable/prohibited、技术单元检索说明的 applicable/not_applicable 使用同样的精确标签规则。

规范对象完整保存适用时间与 subject_versions，并检查固定引用和时间一致性；当前条件数组请求并不等同于旧完整 Applicability DTO。请求端的完整业务时间/目标版本条件仍需独立适配，不能把成功保存这些字段说成已经执行相应查询。

结构字段与约束以 `automation/schemas/memory-v3.schema.json`、`memory/facets.py` 为准；查询投影位于 `material_query/facets.py`，不新增第二套分类数据库或后台分类器。使用真实合成材料的回归为 `automation/tests/test_material_facets.py`。
