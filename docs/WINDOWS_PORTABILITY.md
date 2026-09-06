# Windows 压缩迁移

框架自带 Windows x64 Python 3.12、依赖、CPU 模型和 OCR。迁移完整包无需安装 Python、Docker 或重新下载模型。目标为 Windows 10/11 x64；其他 Windows 版本、ARM64 和不同 CPU 需以目标机自检结果为准。Codex 应用及账号、聊天、用户级插件和授权不在包中，需在目标机单独准备；仓库内 `.agents/skills` 随包保留。

## 发出前

停止当前工作区的索引、查询及其他写入，再运行：

```powershell
.\portable.cmd pack
.\portable.cmd pack --apply
```

第一条预览大小与排除项，第二条检查运行时并生成 `dist/workspace-windows.zip`，同时输出 SHA-256。已有包不覆盖；可用 `--output dist/另一个名字.zip`。打包无需联网，不自动发送文件。包含运行时、模型、离线安装缓存、文档及查询/反馈历史，因此包不是脱敏模板，请只发送到获准环境。

不会打包 `.git`、虚拟环境、`__pycache__`、`scratch`、`tmp`、`dist`、检索派生缓存与 Qdrant 数据库。后两者含旧路径且可重建。其余历史保留，目录链接/联接会报错，避免把外部资料悄悄装入压缩包。打包过程中不要修改文件，打包失败产生的不完整包不要发送。

## 收到后

1. 完整解压到有写权限的短路径，例如 `D:\研发框架\workspace`。不要在压缩包内直接运行。
2. 双击 `portable.cmd`，或终端执行 `.\portable.cmd check`。自检实际运行本地嵌入、OCR、临时 Qdrant 和结构校验，失败返回非零退出码。
3. 在新目录运行以下命令，重建导航与检索缓存：

```powershell
.\automation\workspace.ps1 refresh-index
.\automation\workspace.ps1 index-knowledge
```

若本机 PowerShell 策略不允许运行脚本，可直接使用自带 Python，无需修改系统策略：

```powershell
.\services\qdrant\runtime\python.exe -X utf8 automation\scripts\workspace_cli.py refresh-index
.\services\qdrant\runtime\python.exe -X utf8 automation\scripts\workspace_cli.py index-knowledge
```

外部材料不随框架搬迁。检查 `retrieval/sources.json`、数据卡和授权中的路径，在目标机确认可访问范围并重新登记变化的来源。历史查询和报告中的绝对路径保留为历史证据，不批量替换；新查询应重新生成。若手动直接压缩整个目录，也必须包含隐藏的 `.agents` 与 Git 忽略的 `services` 内容，停止写入并在迁移后重新索引。

自检通过证明本机所测运行链可用；真正不同电脑上的 DLL、CPU 和企业执行限制仍需接收端运行自检确认。
