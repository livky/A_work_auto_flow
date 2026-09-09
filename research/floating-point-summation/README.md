# 浮点求和：长期开发测试例子

本目录是 main 中保留的合成研究样例，用于回归测试数值复现、原始材料、不可变记忆和两种研究文稿。所有数值输入均为构造数据，没有公司业务材料。正式发布包不包含本目录或其他业务实例。

## 目录与证据边界

- `research.json`、`PLAN.md`、`details/`、`rounds/`、`memory/` 和本研究 `runs/` 保留原研究及其历史，不将开发测试通过等同于科学结论通过。
- 本研究 `runs/` 收纳原三轮根目录 Run 的固定字节，并保留既有两次复核 Run；它们仍是同一次历史运行，不是新执行。旧元数据中的路径在隔离工作区按原布局还原。
- `fixtures/restore-manifest.json` 逐文件记录原路径和 SHA-256；`fixtures/sources.json` 保存本例所需的固定来源 ID，只在隔离例子里启用。
- `fixtures/original-README.md.snapshot` 与 `fixtures/original-documents/` 保留原导航正文；当前可读文档调整了链接，隔离回归仍恢复历史版本以核验固定指纹。
- `dev_example.py` 只在 `.local/examples/` 下准备可恢复的隔离工作区，按原路径还原证据；验证输出另存 `.local/example-checks/`。

main 根目录 `runs/` 不保留历史运行记录。不要把配套 Run 搬回 main 根目录，不要为了更新路径而手工改写不可变记忆或冻结输入。需要完整查看图表、固定引用、来源或历史回读时使用下面的隔离工作区。

## 准备与验证

在源码工作区根目录运行，使用框架已有 Python，不需要另装绘图库：

```powershell
# 预览：不创建文件。
.\automation\python.ps1 research/floating-point-summation/dev_example.py prepare
# 写入全新的隔离目录；如果目录已经存在会拒绝覆盖。
.\automation\python.ps1 research/floating-point-summation/dev_example.py prepare --apply
# 校验固定字节、回读完整过程与简版报告，并复现 150 个数值结果。
.\automation\python.ps1 research/floating-point-summation/dev_example.py verify
```

不同开发版本可加 `--destination .local/examples/另一个名称`，避免覆盖已有检查现场。成功退出码为 0；完整输出路径在命令回执中。验证只覆盖保存的有限输入和软件读取功能，不证明任意浮点输入均准确，也不代替人工科学复核。

需要在工作台查看时，保留源工作区的 Python 入口并将工作目录切到准备好的隔离目录：

```powershell
$exampleSource = (Get-Location).Path
Push-Location .local/examples/floating-point-summation
& "$exampleSource/automation/python.ps1" automation/scripts/workspace_cli.py workbench
# 停止工作台后再返回源目录。
Pop-Location
```

仅需 CLI 文稿时，在隔离目录用同一 Python 入口执行：

```powershell
& "$exampleSource/automation/python.ps1" automation/scripts/workspace_cli.py memory document --request research/floating-point-summation/fixtures/read-process.request.json
& "$exampleSource/automation/python.ps1" automation/scripts/workspace_cli.py memory document --request research/floating-point-summation/fixtures/read-report.request.json
```

## 清理与后续维护

`rollback` 默认预览；加 `--apply` 才恢复到准备前的不存在状态。清理前逐文件检查哈希；发现新文件、内容变化或路径重定向时拒绝删除，先保存自己的开发结果。

```powershell
.\automation\python.ps1 research/floating-point-summation/dev_example.py rollback
.\automation\python.ps1 research/floating-point-summation/dev_example.py rollback --apply
```

后续实验在隔离工作区用 `new-run --owner RES-FLOATING-POINT-SUMMATION` 创建新运行。需要晋升为长期回归样本时，显式增加冻结输入和核验清单，保留旧历史与版本，不用新输出覆盖旧基准。

发行用 `git archive` 按 `.gitattributes` 的 `export-ignore` 排除实例，或按受控框架清单构建源码附件，并在上传前核对包内容。直接压缩整个 checkout 和私人 portable 全工作区备份均不是公共发行包。
