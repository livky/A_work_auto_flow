# Windows 迁移与运行环境复用

## 分发方式选择

公开分发给其他用户，使用 `setup.cmd --pack-dependencies --apply` 生成独立依赖包，与同版源码一起安装，见 [依赖包与 Release](DEPENDENCY_RELEASE.md)。该方式不包含业务记录。

下文的 `portable.cmd pack` 是完整工作区快照，包含已有材料、Run 和检索历史，适合获批的私人备份或整机迁移，不能当作公共 Release 依赖附件。

公共源码按 `.gitattributes` 的 export-ignore 通过 git archive 打包，排除 Project 等开发实例；项目内的计划/影响图仅在完整 checkout 或获批私人副本中保留。`portable.cmd pack` 按自己的排除表保存当前工作区，不使用 export-ignore，因此可能包含这些项目。通用 [文档维护约定](DOCUMENTATION_MAINTENANCE.md) 位于 docs，随公共源码交付；发布前仍需核对实际文件清单。

**GitHub 源码安装/旧工作区升级现在优先使用 `setup.cmd`**，无需按下文手工复制。首次安装：`setup.cmd --register --open`；升级：在新版解压目录执行 `setup.cmd --target "D:\研发\旧工作区" --register --open`。默认完整部署，旧业务数据和现有配置保留，框架变更先备份。详见 [一键部署手册](SETUP_WORKBENCH.md)。下文保留完整离线包及人工排查方法。


完整迁移包包含 Windows x64 Python 3.12、依赖、CPU 模型和 OCR，GitHub 源码版不包含这些运行环境。迁移完整包无需安装 Python、Docker 或重新下载模型。目标为 Windows 10/11 x64；其他 Windows 版本、ARM64 和不同 CPU 需以目标机自检结果为准。Codex 应用及账号、聊天、用户级插件和授权不在包中，需在目标机单独准备；仓库内 `.agents/skills` 随包保留。

## 排查：核对旧完整副本的运行环境

适用于另一台电脑已有旧完整工作区，又取得独立新版源码的情况。升级仍从新版目录使用 `setup.cmd --target "旧工作区路径"`，完成后继续使用旧目录。下表帮助定位缺失组件；运行时或模型需要更新时使用匹配依赖包，由安装器核验、暂存、备份和切换，避免手工复制组件后绕过恢复回执。

1. 关闭相关目录中正在运行的工作台、检索、索引和实验进程，保留旧工作区及可用备份。
2. 对照表中位置检查旧完整副本。已有经过验证的环境可按 [依赖分发手册](DEPENDENCY_RELEASE.md) 打包；缺失或不匹配时使用配套发布包，不用旧锁文件覆盖新版源码约束。

| 旧副本中的相对位置 | 核对重点 | 内容 |
|---|---|---|
| `services/qdrant/runtime/` | 是否完整、依赖是否匹配新版锁 | Python、Qdrant client、OCR 和全部 Python 依赖 |
| `services/qdrant/models/` | 是否为当前支持的标准模型 | 本地嵌入模型及相关文件 |
| `services/qdrant/model-manifest.json` | 是否与实际模型文件配套 | 模型校验清单 |
| `services/qdrant/wheelhouse/` | 可选 | 离线重装依赖的安装包 |
| `services/qdrant/downloads/` | 可选 | Python 安装缓存 |
| `services/qdrant/checksums.json`、`services/qdrant/requirements.lock.txt` | 仅按配套版本比对，不拼接新旧锁 | 对应缓存校验与依赖版本 |

运行环境不提交到 GitHub。`services/qdrant/storage/` 和 `retrieval/generated/` 是可重建索引，可能包含旧路径；它们不属于公共依赖包。算法材料、对象内 Run、规范记忆和外部来源登记属于业务内容，继续留在目标旧工作区。需要完整私人迁移时使用下文快照流程，重建索引不能代替找回业务原件。

3. 核对待验证完整环境中的以下定位点；存在这些文件不等于依赖和模型已通过完整检查：

```text
services/qdrant/runtime/python.exe
services/qdrant/models/multilingual-minilm/model_optimized.onnx
services/qdrant/model-manifest.json
```

4. 在待验证完整工作区根目录打开 PowerShell，自检：

```powershell
.\portable.cmd check
```

`"status":"passed"` 只证明本次自检所用版本和环境通过，不代表新版源码已完成安装。随后从独立新版目录按标准 setup 命令升级；安装器会执行对应检查和材料索引。当前使用 Qdrant local，无需额外服务端或 Docker。现行标准模型契约限定已验证名称、相对路径和 384 维；模型或 DLL 校验失败时保留报错并使用匹配依赖包，不宣称任意模型可直接复用。

## 发出前

停止当前工作区的索引、查询及其他写入，再运行：

```powershell
.\portable.cmd pack
.\portable.cmd pack --apply
```

第一条预览大小与排除项，第二条检查运行时并生成 `dist/workspace-windows.zip`，同时输出 SHA-256。已有包不覆盖；可用 `--output dist/另一个名字.zip`。打包无需联网，不自动发送文件。包含运行时、模型、离线安装缓存、文档及查询/反馈历史，因此包不是脱敏模板，请只发送到获准环境。

不会打包 `.local`（合成测试数据、升级备份与最小引导）、未完成的 runtime-stage 目录、`.git`、虚拟环境、`__pycache__`、`scratch`、`tmp`、`dist`、检索派生缓存与 Qdrant 数据库。后两者含旧路径且可重建。其余历史保留，目录链接/联接会报错，避免把外部资料悄悄装入压缩包。打包过程中不要修改文件，打包失败产生的不完整包不要发送。

私人快照会保留实际存在的对象 memory_home、HEAD/不可变提交/回执、对象内 runs、单文件对象的 `.memory.runtime/runs/`、工具 runtime/runs 和 `.run-captures/`。v1/v2 历史、v3 技术单元、独立章节与双文稿按原字节保存。`.local/upgrades`、`.local/dependency-backups` 和其他 `.local` 回执不在此快照中，不能把快照当成这些排除项的备份；需要保留时另按获批范围备份。

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

已有版本记忆还需核对派生索引状态；`index-knowledge` 不代替记忆索引补偿。按 [记忆使用指南](MEMORY_USAGE.md) 准备 UTF-8 请求 `{"vector":"auto"}`，调用 `workbench.cmd memory reconcile --request 请求文件` 从规范 HEAD 重建记忆索引。先检查当前模型能力和回执，pending 不表示历史记录丢失；不要修改旧记录哈希来消除提示。

外部材料不随框架搬迁。检查 `retrieval/sources.json`、数据卡和授权中的路径，在目标机确认可访问范围并重新登记变化的来源。历史查询和报告中的绝对路径保留为历史证据，不批量替换；新查询应重新生成。若手动直接压缩整个目录，也必须包含隐藏的 `.agents` 与 Git 忽略的 `services` 内容，停止写入并在迁移后重新索引。

自检通过证明本机所测运行链可用；真正不同电脑上的 DLL、CPU 和企业执行限制仍需接收端运行自检确认。
