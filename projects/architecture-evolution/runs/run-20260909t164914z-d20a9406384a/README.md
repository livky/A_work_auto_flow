# 接口契约与Project默认分层记录

Run：`RUN-20260909T164914Z-D20A9406384A`，归属`PRJ-ARCHITECTURE-EVOLUTION`。本轮完成设计、默认策略和实际分层保存；检索运行适配待实施，人工及科学复核未完成。

## 交付与入口

- [核心简版](../../design/interfaces-v0.1/CORE.md)：表示/索引和⑤–⑨的职责与调用链。
- [完整契约](../../design/interfaces-v0.1/SPEC.md)、[逐函数目录](../../design/interfaces-v0.1/FUNCTIONS.md)、[字段目录](../../design/interfaces-v0.1/DATATYPES.md)：40个领域方法、3个共享执行控制方法、72种数据结构；12项合并/预留/排除选择保留理由。
- [实施落点与验收](../../design/interfaces-v0.1/IMPLEMENTATION.md)：先复用现有身份/FTS/Qdrant和显式关系，不将预留策略声明为已实现。
- [默认策略核对](project-policy-review.md)与[影响检查](IMPACT_REVIEW.md)：Project默认与Research一致；请求/对象显式覆盖优先。规则、模板、README与相关Skill同步。

## 实际分层保存

3次公开commit保存24条规范记录：8个L1完整技术单元、2条L2事件、1条L3经验、1份L4地图、10个独立章节和2份独立文稿。原始依据通过16个固定文件来源及本Run材料保留，不重复创建MEM来源记录。原讨论以本次日期回顾，旧Run与快照原字节保留。

| 文稿 | 固定ID/版本 | 组织 |
|---|---|---|
| [完整过程导出](process-document.md) | MEM-3264fce7-c63f-504e-bdb5-3aaa1169eb7b r1 | 8章，保留讨论、契约、完整代码定义、实施与验证 |
| [核心简报导出](brief-document.md) | MEM-ef137680-afa6-59b8-a263-f2bb33d256c4 r1 | 2章，说明核心功能、验证限制和实施顺序 |

两份文稿共享同一组8个固定技术单元。全部作者字段回读相等，均无未覆盖单元和缺失引用；选取technical-body时自动补齐scope定义。最终内容HEAD为`COM-5150e9bb-4bb1-47ee-b833-534dacd24545`，FTS与向量索引代次3完成。结果见[memory-readback-checks.json](memory-readback-checks.json)。

请求/回执为`layered-v2-*`、`sections-*`、`documents-*`；第一次`layered-request.json`因事件decision_refs缺依据被拒绝，未写入，失败调用保留。随后补齐固定依据，使用新请求ID成功保存。[record_design.py](record_design.py)保留实际公开调用流程；不直接写规范记录文件，也不重复执行已有提交。

## 验证与限制

- [契约结构检查](contract-checks.json)：方法/类型目录一致，12个合成正负结构用例通过。这不证明新接口的运行行为、权限、质量或性能。
- [quick结果](testing/attempt-01/results.json)：136项Python实际执行，135通过、1失败；19项前端因缺开发依赖未运行，整体failed。既有冻结夹具3个文件的差异与HEAD一致，见[诊断](fixture-diagnostic.json)；未修改其冻结哈希。
- 真实setup.cmd已扩展旧工作区场景通过，覆盖预览、升级、重复升级和恢复及共享保护清单。本地Windows x64隔离合成环境通过，不等于第二台物理机/真实业务验收。本轮未改依赖、模型、前端或安装器。
- [实际AI审查](actual-ai/reports/report-1eec22947e094b81a24f5f47a682683e/REVIEW.md)：A01/A03及A04的正文/依据自查完成；公开CLI回读、原来源expand和定义闭包已有实际记录。同一连续任务，未冒充A02新上下文审查。
- [页面检查](ui-check.json)：现有本地工作台被内置浏览器以ERR_BLOCKED_BY_CLIENT阻止，未取得页面；公式、图、目录及链接的页面效果仍未验收。Markdown/LaTeX正文已回读，不能据此声称视觉效果通过。
- 人工意见、科学复核和第二台物理机验收待完成；用户认可功能方向不提升结论可信状态。未执行新检索性能或万条规模实验。

## 后续使用

需要快速了解时读核心简版；实施时按SPEC和类型签名核对，逐函数必要性及前后置条件在FUNCTIONS。当前设计文件允许后续形成新版本；本Run的`artifacts/interfaces-v0.1/*.snapshot`与固定源不修改。新证据修订技术单元时生成新修订，再检查受影响章节和文稿。

本Run状态描述“设计、规则和保存任务完成”，与quick失败、页面未验收、科学未复核分别记录。没有自动启动整理或扩大来源授权。
