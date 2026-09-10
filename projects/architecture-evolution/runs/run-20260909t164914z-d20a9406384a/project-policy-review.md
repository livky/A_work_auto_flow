# Project 默认记录规则：实现与验证

本记录整理于 2026-09-10（北京时间）。事实来自本轮源码修改、公共 inspect 和实际测试回执，不把接口设计当作已运行的检索能力。

## 问题、依据与修改

Project 的规范记忆后端原本已支持 L1–L4 和独立文稿；该项目本轮开始时 HEAD=null，只有此前 Run/L0 记录。`memory/policy.py` 原类型默认将 Project 设为 basic，项目 README 还使用“按需采用对象记忆”。这使默认记录要求弱于 Research。

依据本轮用户要求，Research 与 Project 现共用同样的类型默认：explore、fine、retain=[L0,L1,L2,L3,L4]、auto_summary=true。公共 inspect 已返回这些值，来源均为 type；owner_only、auto_deepen=false、checkpoint=true 保持基础默认。

根规则、projects 规则和模板、研究记录标准、MEMORY、README、对象保存指南及相关 Skill 已同步。每轮实质工作保存 L0/L1/L2，阶段维护 L3/L4 与完整/精简文稿；无经验时说明缺口，不凑层数。程序只提供有效策略，不后台生成正文。已有显式对象策略和请求覆盖仍优先；原始记录、固定引用和历史复核保持原样。

## 已执行的验证

| 检查 | 实际结果 | 限制 |
|---|---|---|
| 策略与对象专用回归 | test_memory_owners 12 项通过 | 使用隔离合成对象，不是检索质量评测 |
| 冻结 quick 选择 v2 | 136 项 Python 执行：135 通过、1 失败；19 项前端未执行 | quick 整体 failed，不能写为全部通过 |
| 真实 setup 扩展旧工作区 | test_windows_zip_upgrade_entry_and_rollback_preserve_data 通过，约 92.6 秒 | 本机 Windows 隔离目录，非第二台物理机验收 |
| 新 Project 默认公共回读 | inspect 返回 explore/fine/L0–L4/auto_summary=true，来源为 type | 分层正文仍须由 AI 实际撰写和保存 |
| 抽象契约结构检查 | 40 个领域方法、3 个控制方法、72 个数据结构、12 个正反请求均通过 | 不证明后端行为、鉴权或性能已实现 |

quick 的唯一 Python 失败为既有冻结 fixture 自检：acceptance.json、records.json、work-packages.json 与冻结 manifest 不一致。三文件当前 SHA 与 HEAD 一致，也与前一轮 Run 已报告的差异相同。本轮未修改 fixture 或通过重算清单掩盖问题。19 项前端缺 frontend-dev，未执行原因已保存。

相关证据：testing/attempt-01/results.json、01-python.json/log、fixture-diagnostic.json、policy-inspect-before-save.json、contract-checks.json。完整机器回执与源文件由本 Run 固定登记。

## 不可推出的结论与后续

不能从上述结果推出新召回、图检索、渐进预算或自动整理执行器已经接入，也不能推出业务知识已经获得科学复核。下一步应从固定读取/范围/回执适配开始，按接口验收矩阵逐步实施；既有 fixture 指纹差异另行追溯。当前依赖和模型未变，沿用 Windows x64 源码加原配套依赖包的升级方式。

本轮将接口正文与实际事件保存为 Project 规范记忆及双文稿，保存成功、AI 自查和人工审查分别记录。
