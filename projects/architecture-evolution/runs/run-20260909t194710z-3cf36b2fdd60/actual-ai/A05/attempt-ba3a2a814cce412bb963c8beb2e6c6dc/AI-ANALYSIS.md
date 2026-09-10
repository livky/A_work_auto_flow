# A05 无新变化与缺失来源的实际补充

执行者：Codex `/root/frontier_review`，身份为 ai。本次在 A09 最终状态的独立合成副本执行，复制前后全部文件哈希一致；没有重演 A09 的局部内容修订。A05-E1/E2 明确复用并复审 A09 已保存证据，A05-E3 是本次新增的公开调用和实际判断。人工及科学审查仍待完成。

## 重新计划后的实际阅读与决定

我向公开 `material-query maintenance-plan` 提交与 A09 相同的固定饱和输入 r1，在复制得到的最终状态生成新计划 `MP-bb08320e-9c81-4014-90d1-edee9bc3d07d`。服务交付三个 detail 与两份登记原件，初始动作仍全部为 defer；这不是自动得出了“无变化”。我完整读完五部分正文、固定引用和空 omitted，并另外读了两份文稿的当前 `document-impact`：两者 `changes=[]`、受影响章节为空、`writes=0`。

模型现为 r2，已经包含与同一输入一致的边界：

$$
q_{req}=c h_r=0.20\,\mathrm{m^3/s}>q_{max}=0.15\,\mathrm{m^3/s},\qquad
h_{sat}=q_{max}/c=1.5\,\mathrm{m}.
$$

这里 $q_{req}$ 是维持目标所需流量，$h_r=2\,\mathrm m$ 是目标，$c=0.1\,\mathrm{m^2/s}$ 是出流系数，$h_{sat}$ 是持续最大流量下的合成平衡液位。r2 已说明目标相差 $0.5\,\mathrm m$，保留原未饱和指数式的适用条件；这只是给定文字前提的代数检查，未执行仿真或现实实验。

我逐项填写了三个 retain 决定：保留相同的饱和输入 r1；模型 r2 已覆盖该输入，无需再次追加相同边界；变量定义 r1 的单位、误差与 clip 定义也没有变化。公开 review 保存不可变审查版本，digest 为 `522fb50f4cd59a9028bdf1dfb815a3ced0f2c6a12f78dbcee5b7822e34211b5f`。我保留了服务端原上下文、未检查范围和读取回执，没有冒领人工审查。

随后用新 request_id `48c67170-bdee-4f57-8a1e-a140c9f5d2b7` 公开 apply，返回 **ok、commits=[]、pending_items=[]、index_status=indexed**。55 份规范及来源文件的哈希全部与副本初始状态相同，公开 TANK owner inspect 前后完整结果也相等。此次没有重复生成知识正文或新内容修订；新的本地计划和审查/应用回执仍保留，这是审计历史，不应删除或误称不存在。

实际交付：[五部分完整正文](delivered/no-new-evidence-plan.md)。公开结果：[新计划](outcomes/no-new-evidence-plan-retry.json)、[retain 审查](outcomes/no-change-retain-review.json)、[无内容写入应用](outcomes/no-change-apply.json)、[前后机械核对](mechanical-verification.json)。

## 真实缺失来源与恢复

只在 A05 副本中，我临时移走已登记的 `SRC-F3-SATURATION` 对应文件 `research/saturation/data/合成 输入.md`，登记项和规范记录保持不变。公开同一维护计划入口实际返回 **rejected / SOURCE_MISSING**：`value=null`、警告“固定来源不可用”、`stop_reason=source_missing`，结构化 Issue 的 `retry=after_external_change`。没有把无法读取的来源当作无影响或生成完整材料；输出字符消耗为 0。该拒绝并不表示所有读取成本为零。

调用结束后，在 finally 中恢复同一原始字节，恢复前后 SHA256 均为 `7bcb1b5e9e7791021701252d87d96473784146c883c648248fde7a86b40ff28f`。恢复后的再次公开计划生成 `MP-47545906-7308-4f6c-b8ed-b62be81a1251`，重新交付五部分，固定条目引用和每一部分内容都与已完整读过的前一计划相等。55 份规范及来源文件再次核对无变化。

缺失与恢复证据：[缺失时公开拒绝](outcomes/missing-saturation-plan.json)、[字节恢复回执](outcomes/missing-saturation-plan-restoration.json)、[恢复后计划](outcomes/restored-source-plan.json)、[最终核对](mechanical-verification.json)。恢复后计划仍以 defer 开始，未再次 apply，避免把同一检查再算一次内容操作。

## A05 逐项对应

| 条目 | 本次观察与证据性质 |
| --- | --- |
| A05-E1 影响原因、路径及未变内容 | 交叉引用 A09 的两份 impact-before：文稿→章节→模型及直接依据路径，实际局部修订两个相关章节/文稿；定义和饱和输入保持 r1，原推导保留而边界新增。本次完整阅读 [A09 分析](../../A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/AI-ANALYSIS.md)和[独立交叉复审](../../../a05-cross-reference-review.md)，不是重新执行旧修订。新执行另证明同一已处理输入下三个 retain 不重复写内容。 |
| A05-E2 旧版保留、双文稿一致 | 交叉引用 A09 的历史两稿完整回读、[双文稿更新回执](../../A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/document-update-receipt.json)与共同依据。A09 的旧双文稿是当次明确建立的合成基线，不是现实历史恢复。本次公开两份当前 impact 再次显示 changes=[] 且固定定义 r1、模型 r2、饱和 r1 一致。 |
| A05-E3 无变化不堆积、来源缺失可见 | 本次新计划→完整阅读→三个 retain→review→新 request_id apply 返回空提交；55 文件与公开对象前后相等。真实原件缺失返回 SOURCE_MISSING，恢复字节后重新交付相同内容。A09 原同 request_id 幂等只作补充历史证据，没有替代本次两项实际执行。 |

## 范围、失败与限制

- 所有实际执行的本次产品调用的根目录均为 `.local/testing/a05-followup-10a1d20f283742e8947da848225d89d2/workspace`。来源缺失只在这个副本制造，未修改产品、测试、原 F3 或真实 Project，也未改已登记的继承报告或 FINAL_VALIDATION。
- 第一条维护计划误用了该材料查询入口不支持的前置 `--root` 形式，CLI 在解析阶段退出 2。原失败调用留存；后续改为以独立副本为 cwd 调用公开 material-query，形成新的成功交付回执。它没有被改写为成功。
- A09 的 revision/CAS/幂等以及双文稿 r1→r2 是先前真实调用，本次仅交叉引用与只读复审。A06 可在原 F3 另行新增获准的合成候选；因此不把整个并发时段原 F3 的 HEAD 恒定作为 A05 的断言。A05 验证的是自己独立副本的 55 文件。
- 当前 planner 对显式输入仍产生待审计划，是否保留来自此次 AI 实际阅读；没有宣称自动识别任意语义等价或全库无变化。范围为 TANK/SATURATION 的合成 detail，其他主题、未登记来源、向量模型和现实科学有效性未验证。

原 A09 同 request_id `d9b6718f-ee70-4d97-a9b8-380e2689c9de` 两次返回同一 `COM-525a8d2a-122a-44fb-a5c0-01a3e1cfd3fe`，完整固定 ID 与对照路径见[交叉复审笔记](../../../a05-cross-reference-review.md)。本尝试的不可变 manifest、独立 calls、reads 与 assessment 分开记录；manifest 的初始 not-run 不被覆盖。
