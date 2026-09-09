# 实际AI使用记录工具

本目录只提供任务与留存格式，不生成技术正文、自评或人工意见。实际AI先读取输入、生成请求，再通过公开CLI/API保存、回读和自查。

使用工作区Python执行 `automation/testing/ai_review.py --help`。`init --output <固定Run/ai-review> --scenario A01 --actor <实际角色>` 冻结新尝试，可用 `--task-file` 绑定本轮任务；未知模型不填。A02须由真正新上下文完成，`--context-mode fresh` 只是声明，不创建上下文。

`call --attempt <目录> --request <AI请求JSON> -- <公开CLI参数>` 原样保存请求、命令、输出、错误、失败和超时；退出非零仍留下证据。每次均唯一命名，不覆盖重试。此入口只留存命令，不证明命令属于公开产品或获得额外授权。

`read --attempt <目录> --input <阅读事件JSON>` 保存实际呈现给AI的文本/截图及读取范围；`assess --attempt <目录> --input <自查JSON>` 保存实际AI对每条预期的观察，状态只选 meets、does-not-meet、cannot-assess，必须附证据。模板里的空字段须由真实使用补齐；保存文件不等于已经阅读。

`render --output <固定Run/ai-review>` 生成新的人工审查首页和逐项页面，不改旧报告。程序执行、自查、人工审查及科学复核分别记录。人工状态始终待审，用户意见在正式审查记录中另存并固定版本。脚本机械自检归程序测试，不计作A01–A06已执行。
