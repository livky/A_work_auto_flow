# 一键安装、升级与研发工作台

适用 Windows 10/11 x64。GitHub 下载源码 ZIP 并**完整解压**后，在解压目录打开终端。配套依赖 ZIP 与 `.zip.sha256` 放在源码根目录后，安装和升级均可完全离线；没有配套包时首次完整安装联网下载。无需预装 Python、Node 或 Docker。依赖分发见 [依赖包与 Release](DEPENDENCY_RELEASE.md)。

## 最常用的三条命令

首次安装，并注册命令、打开工作台：

```powershell
.\setup.cmd --register --open
```

已有旧工作区，使用新版解压目录升级它：

```powershell
.\setup.cmd --target "D:\研发\旧工作区" --register --open
```

日常打开：

```powershell
rdwork
```

首次注册后重新打开终端。当前终端也可直接运行目标工作区的 `workbench.cmd`。升级后继续使用旧工作区路径，它包含原业务数据；新版解压目录只是升级来源。开始升级前关闭目标目录中正在运行的工作台、索引和实验进程。

## 选项

| 选项 | 作用 |
|---|---|
| 不指定选项 | 完整安装：便携 Python、锁定依赖、模型自检、结构检查及索引 |
| `--target "路径"` | 将新版框架安装到已有旧工作区，原位保留数据；新旧目录不能互相嵌套 |
| `--profile core` | 只准备基础入口、刷新导航与校验；证据/监测可用，不下载向量/OCR 模型 |
| `--offline` | 禁止安装流程下载；复用兼容旧环境或配套离线缓存，缺失则失败 |
| `--bundle "依赖.zip"` | 校验并直接复制配套环境，隐含离线；ZIP 旁需有 `.zip.sha256`，源码根目录的 `dependencies-windows-x64.zip` 自动识别 |
| `--pack-dependencies [--output 路径] [--apply]` | 预览或从当前真实环境生成可分发依赖 ZIP；不指定 `--apply` 不写包 |
| `--preview` | 不写入；普通安装列出框架变更，带依赖包时仅校验 ZIP/清单并报告依赖范围，无需为预览解压 Python |
| `--register` | 注册唯一的用户命令 `rdwork`，重复执行更新目标地址 |
| `--unregister` | 撤销本工具的命令注册，保留工作区和数据 |
| `--open` | 安装成功后打开工作台，Ctrl+C 停止 |
| `--rollback "回执所在目录"` | 按备份恢复框架文件；可与 `--preview` 组合 |
| `--rollback-dependencies "回执目录"` | 恢复运行时/模型组件，保留业务数据；从独立源码目录配合 `--bundle` 执行 |

已有环境只需增加命令入口：`setup.cmd --profile core --register`。所有原 CLI 子命令均可经 `rdwork <子命令>` 调用，如 `rdwork validate`、`rdwork evidence-monitor --dry-run`、`rdwork --help`。

## 升级如何保留旧数据

- 明确替换：automation 程序/界面/测试/工作流、框架手册与模板、根启动器、运行时安装脚本。
- 保留：算法实例、Run、研究、项目、知识、数据卡、报告、查询反馈、监测历史、已有检索配置、来源登记、工具登记、AGENTS、context 状态和自定义 Skill。缺少的默认配置/规则/技能才补齐。
- `.gitignore` 保留旧内容，只补充必需的本机输出排除项。框架升级不会把新版下载目录里的历史研究或测试实例复制成旧工作区业务记录。
- 每个替换文件先备份到目标 `.local/upgrades/<批次>/`，回执保存原始和安装后的 SHA-256。文件在安装期间变化会中止；恢复前全量核对，安装后有新编辑则拒绝覆盖。新加文件也记录在回执，可在恢复时移除。
- 兼容旧运行时按新版依赖锁检查后复用；需安装依赖时在临时目录构建、导入检查成功后再切换，旧运行时保留在 `.local/runtime-backups/`。失败明确返回非零，业务数据和框架备份保留，不能把部分安装当作完整成功。
- 配套依赖包先检查文件指纹、框架锁和模型清单，直接复制到目标盘暂存区，逐组件备份/切换。旧环境与回执保存在 `.local/dependency-backups/`；切换过程中失败自动恢复。后续自检或索引失败则保留回执并返回非零，可按回执恢复。框架锁文件随程序升级并进入框架备份；自定义检索配置不覆盖，自定义模型与标准包冲突时明确停止。
- 外部共享盘原件不复制，历史绝对路径不批量替换；在目标机核对 `retrieval/sources.json` 和数据卡的可访问路径。工作区内相对引用保持可迁移。

恢复示例：

```powershell
.\setup.cmd --rollback "D:\研发\旧工作区\.local\upgrades\实际批次目录" --preview
.\setup.cmd --rollback "D:\研发\旧工作区\.local\upgrades\实际批次目录"
```

恢复范围是该回执中的框架文件，业务编辑不回滚。运行时旧目录单独保留，必要时在关闭 Python 进程后恢复；模型和重建索引不伪装成业务记录备份。

依赖包提供独立的一键恢复入口，见 [依赖恢复](DEPENDENCY_RELEASE.md#升级与恢复)。使用端不需要 wheelhouse；直接导入包内已经安装并验证过的文件。旧 `install.py --offline` 从 wheelhouse 重装的方式仍可使用。

## 命令注册如何避免累积

注册文件位于 `%LOCALAPPDATA%\AI-RD-Workspace\bin`。只添加**一个固定用户 PATH 项**，不改变系统 PATH、PowerShell profile 或永久执行策略。工作区地址写在 JSON 中，升级/换路径只更新地址；重复注册不追加路径。已有其他软件的同名命令或不属于本安装的目录会阻止覆盖。

卸载只删除本工具的启动器，以及由本安装添加的 PATH 项，保留其他软件路径。注册信息属于当前 Windows 用户，不随 Git 或离线包迁移；其他机台需重新注册。Windows 的进程环境由父进程继承，因此已开的终端不会自动更新，见 [Microsoft 环境变量说明](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables?view=powershell-7.5)。

## 工作台中的操作

工作台已采用预构建界面，源码包包含完整 JS、CSS 和计算 Worker，使用机台无需 Node。材料关系页支持辐射、聚合、证据链和按需分析，操作见 [材料关系手册](MATERIAL_RELATIONS.md)。首次构建和分析在后台执行，任务页可查看进度或取消。前端开发方式见 [开发手册](WORKBENCH_DEVELOPMENT.md)。

首页聚合证据入口、模块文件清单、手动监测、持续监测和能力检查。证据页可搜索结论、查看来源与复核、定位受影响报告。能力检查区分不可用、尚未验证和所选检查通过，不自动安装。

持续监测由按钮手动开启，每 60 秒执行一次，只保存本机观察基线、事件与候选。首次建立基线；错误显示在页面，保留上次有效基线。关闭服务终端或 Ctrl+C 时停止；关闭浏览器标签页不会结束服务。不会安装开机服务、系统定时任务或跨会话自动化。

工作台只绑定 127.0.0.1，以随机访问地址隔离会话；HTTP 操作只有固定动作，拒绝跨站请求、任意命令与任意文件路径。复核、导入和实验仍使用现有 CLI/Skill，网页不会自动执行它们。

## 本机测试数据

```powershell
.\workbench.cmd test-data
.\workbench.cmd workbench --demo
```

生成器在 `.local/test-workspace/` 建立独立合成工作区，覆盖算法、数据/契约、Run、研究、知识、报告、项目、工具、检索、导航和治理目录。包含“输入→结论→研究/报告”链和未完成实验，全部标记合成、未复核。生成器与测试代码进入源码版本；**生成的数据实例、缓存、观察日志和备份不进入 Git，也从 portable 离线包排除**。

重复生成保留样本编辑。可以在沙盒中修改 CSV 或把 Run 的 status 从 running 改成 succeeded，再点击“立即检查一次”，查看版本风险与完成事件。正式工作区不会读取沙盒结论。测试中的关键词检索配置只作用于沙盒，不能用来证明真实向量模型可用。

首次无 Python 引导使用官方嵌入式 Python，本机保存；嵌入包不自带 pip，安装器使用公开 pip 引导并为目标 CPython 3.12 x64 下载锁定 wheel，见 [Python 官方说明](https://docs.python.org/3.12/using/windows.html#the-embeddable-package) 和 [pip 安装文档](https://pip.pypa.io/en/stable/installation/)。
