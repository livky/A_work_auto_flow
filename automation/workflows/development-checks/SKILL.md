---
name: development-checks
description: 在 AI 研发工作区开发或修复功能时，更新并执行可复用分级测试清单，保存实际 AI 自查和人工审查入口。
---
# 开发验证

在含 `workspace.json` 的工作区使用。读取 [分级测试规范](../../../docs/TESTING.md)，按目标选择影响能力和 quick/full 层级；命令入口为 `workbench.cmd testing`，可用 `--help` 查看参数。

先按[文档与模块影响维护](../../../docs/DOCUMENTATION_MAINTENANCE.md)定位变化模块和本工作区的影响图，沿实际关联检查契约、索引、技术文稿、CLI/UI、Skill、README/AGENTS 和迁移。将需修改、已检查无需修改、延期及理由保存到本轮 Run 或小任务摘要；据此选择测试，职责变化时同步更新图并留固定快照。

开发前先执行 `testing audit`，盘点新功能或未分类测试。使用 `testing prepare` 将目标、能力、必要场景和排除理由保存到本次固定 Run；范围变化用 `testing update` 生成下一版，保留原版。新增测试用 `testing register` 明确归类，不能为消除失败降低验收标准。

实现后执行 `testing validate --plan <清单>`，再用 `testing run --plan <清单> --out <新执行目录>` 保存独立回执。quick 保留核心门槛并增加受影响项；full 覆盖完整功能。前端改动须构建与实际浏览器验证；升级、依赖及模型风险按规范增加对应测试。失败、跳过和未执行分别报告。

需要实际 AI 验收时，读取 `automation/testing/ai_review.py --help` 和规范中的 A01–A06。AI 必须自己读取输入、生成请求、通过公开入口保存并回读，然后写自查；程序只记录和机械核对，不能代填 AI 判断。新上下文续接使用真正独立的上下文，人工首页仅保留核心、本次新增和重要受影响功能。人工状态保持待审，科学结论不因功能验证自动获认可。

复用历史测试需核对源码、清单和输入指纹；总结固定 Run、执行结果与限制。目录和测试定义保存在 `automation/testing/`，任务清单、日志和审查报告保存在 Run，避免业务回执进入公共发行包。

测试回执完成后，由 AI 用 `run-register RUN-ID --artifact <实际回执文件>` 将需追溯材料登记到 L0，重复登记无需再写 source，也不要求用户手填哈希。独立 Python 验收计算可用 `run-execute` 自动保存输入与输出，但不能替代本 Skill 的分级测试入口。登记版本变化与失败必须保留；预览、恢复和范围见[执行与登记手册](../../../docs/RUN_CAPTURE.md)。
