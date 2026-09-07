# Windows 迁移与运行环境复用

## 分发方式选择

公开分发给其他用户，使用 `setup.cmd --pack-dependencies --apply` 生成独立依赖包，与同版源码一起安装，见 [依赖包与 Release](DEPENDENCY_RELEASE.md)。该方式不包含业务记录。

下文的 `portable.cmd pack` 是完整工作区快照，包含已有材料、Run 和检索历史，适合获批的私人备份或整机迁移，不能当作公共 Release 依赖附件。

**GitHub 源码安装/旧工作区升级现在优先使用 `setup.cmd`**，无需按下文手工复制。首次安装：`setup.cmd --register --open`；升级：在新版解压目录执行 `setup.cmd --target "D:\研发\旧工作区" --register --open`。默认完整部署，旧业务数据和现有配置保留，框架变更先备份。详见 [一键部署手册](SETUP_WORKBENCH.md)。下文保留完整离线包及人工排查方法。


完整迁移包包含 Windows x64 Python 3.12、依赖、CPU 模型和 OCR，GitHub 源码版不包含这些运行环境。迁移完整包无需安装 Python、Docker 或重新下载模型。目标为 Windows 10/11 x64；其他 Windows 版本、ARM64 和不同 CPU 需以目标机自检结果为准。Codex 应用及账号、聊天、用户级插件和授权不在包中，需在目标机单独准备；仓库内 `.agents/skills` 随包保留。

## 手工排查：用旧完整副本补齐 GitHub 新版

适用于另一台电脑已经保存旧的完整工作区，同时又下载或克隆了 GitHub 新版的情况。以 GitHub 新版文件夹为主，只从旧副本复制运行环境到相同的相对位置，不用旧文件夹整体覆盖新版脚本、规则和配置。

1. 关闭两个目录中正在运行的检索、索引或其他写入程序。保留旧完整副本作为恢复来源。
2. 按下表复制。runtime 和 models 必须整目录复制；如果目标已有不完整目录，先移到单独备份位置，再放入完整目录，避免新旧依赖混合。

| 旧副本中的相对位置 | 是否需要 | 内容 |
|---|---|---|
| `services/qdrant/runtime/` | 必须 | Python、Qdrant client、OCR 和全部 Python 依赖 |
| `services/qdrant/models/` | 必须 | 本地嵌入模型及相关文件 |
| `services/qdrant/model-manifest.json` | 必须，与模型一起复制 | 与实际模型文件配套的校验清单 |
| `services/qdrant/wheelhouse/` | 可选 | 离线重装依赖的安装包 |
| `services/qdrant/downloads/` | 可选 | Python 安装缓存 |
| `services/qdrant/checksums.json`、`services/qdrant/requirements.lock.txt` | 复制离线缓存时一起带上 | 对应缓存校验与依赖版本 |

这些环境文件继续留在本机，不需要提交到 GitHub。不要复制旧的 `services/qdrant/storage/` 或 `retrieval/generated/`：它们是可重建索引，可能包含旧路径。若新版已经使用过，先把这两个目录移到单独备份位置，再重建；不要在程序运行时移动数据库。算法材料、Run 和外部来源登记属于业务内容，不随本次环境复制自动合并。

3. 确认新版中至少存在以下文件；这里只列定位点，不能只复制这三个文件：

```text
services/qdrant/runtime/python.exe
services/qdrant/models/multilingual-minilm/model_optimized.onnx
services/qdrant/model-manifest.json
```

4. 在新版根目录打开 PowerShell，先自检：

```powershell
.\portable.cmd check
```

只有显示 `"status": "passed"` 后，才继续执行以下命令，重建导航和检索索引。直接调用自带 Python，无需修改 PowerShell 执行策略：

```powershell
.\services\qdrant\runtime\python.exe -X utf8 automation\scripts\workspace_cli.py refresh-index
.\services\qdrant\runtime\python.exe -X utf8 automation\scripts\workspace_cli.py index-knowledge
```

当前使用 Qdrant 本地模式，不需要额外安装 Qdrant 服务、Docker，也不用启动服务器。环境复制与自检不需要下载模型；首次重建索引需要一些时间。旧环境能否兼容新版，以目标电脑自检为准：缺少 Python 表示 runtime 未完整复制；模型校验失败需恢复配套的 models 和 model-manifest.json；依赖导入或 DLL 错误应保留具体报错检查兼容性，不能视为迁移成功。

## 发出前

停止当前工作区的索引、查询及其他写入，再运行：

```powershell
.\portable.cmd pack
.\portable.cmd pack --apply
```

第一条预览大小与排除项，第二条检查运行时并生成 `dist/workspace-windows.zip`，同时输出 SHA-256。已有包不覆盖；可用 `--output dist/另一个名字.zip`。打包无需联网，不自动发送文件。包含运行时、模型、离线安装缓存、文档及查询/反馈历史，因此包不是脱敏模板，请只发送到获准环境。

不会打包 `.local`（合成测试数据、升级备份与最小引导）、未完成的 runtime-stage 目录、`.git`、虚拟环境、`__pycache__`、`scratch`、`tmp`、`dist`、检索派生缓存与 Qdrant 数据库。后两者含旧路径且可重建。其余历史保留，目录链接/联接会报错，避免把外部资料悄悄装入压缩包。打包过程中不要修改文件，打包失败产生的不完整包不要发送。

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
