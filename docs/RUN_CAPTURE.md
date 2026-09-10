# 运行实验并自动保存 L0 材料

“登记”是给文件记一条目录记录：文件路径、所属 Run、用途、登记时间和 SHA-256 文件指纹。指纹用于发现文件是否变化，不表示结果正确。原始文件仍在原位置，L0 根据记录显示和核验它。

本页按 2026-09-09 的 main 执行入口核对。Run 与回执的归属见 [对象保存逻辑](OBJECT_RUN_STORAGE.md)，模块职责见 [ARCHITECTURE.md](../ARCHITECTURE.md)；执行/登记规则变化时按 [文档维护约定](DOCUMENTATION_MAINTENANCE.md) 同步操作示例和 Skill。

## 新实验：运行后自动登记

请 AI “用研究 Skill 执行实验，并把输入、程序、输出和日志保存到 L0”。AI 建立 Run、准备下面的请求并调用 `run-execute`，你不必手填指纹或修改 run.json。

当前执行入口支持使用工作区 Python 运行 `.py` 脚本；无需新增依赖。脚本把结果写到当前工作目录或 `{output_dir}`，以同步方式结束，不启动脱离父进程的后台任务。运行不是安全沙箱，必须是已获授权的脚本。

```json
{
  "script": "research/my-topic/calculate.py",
  "inputs": ["data/my-input.json"],
  "args": ["{input0}", "{output_dir}"],
  "timeout_seconds": 3600
}
```

路径按工作区根解释；args 按数组逐项传给脚本，不经过 shell。`{input0}` 是第一个输入的绝对路径，后续依次编号。实际参数由脚本接口决定；不需要参数的脚本使用空数组。外部输入仍需已有的逐文件来源授权，目录不是输入文件。输入保持只读使用；执行中变化会使本次运行标记失败。

```powershell
.\workbench.cmd new-run --owner RES-ID --title "本轮实验问题"
.\workbench.cmd run-execute RUN-ID --request execution-request.json --preview
.\workbench.cmd run-execute RUN-ID --request execution-request.json
```

每次调用生成 `Run目录/.run-captures/唯一编号/`：`outputs/` 存本次结果，`stdout.txt`、`stderr.txt` 和 `execution.json` 保存日志、实际命令、Python 版本、时间和退出码，`registration.json` 保存登记恢复依据。脚本和显式输入在运行前固定指纹；运行后自动登记该次 outputs 内的全部文件及日志。已有版本不会覆盖；需要留存将来会修改的程序版本时，应先保存独立代码快照或 Git 提交再执行。程序依赖、配置和随机种子仍需 AI 明确提供，不能声称自动发现了所有隐式依赖。

成功和失败运行均保存材料，超时返回失败；Run 状态对应最近一次执行，各次日志保持。退出码：0 为执行与登记成功，1 为执行/材料检查失败但已保存回执，2 为请求、权限或登记冲突等错误。登记失败时保留该次目录与恢复回执，不报告成功。脚本不得依赖此入口自动发现写到其他目录的输出；这些文件用下节显式登记。

工作台选中该 Run 或关联研究的“L0 原始材料”，即可看到材料；也可用 `memory raw-materials` 回读清单。L0 读取仍受指纹、权限与大小限制，正文不自动进入常规知识检索。

## 已有材料与其他工具：一次登记后自动显示

对于已有数据、Notebook、其他语言或外部程序的结果，AI 调用 `run-register`，自动计算当前指纹并写入 Run。记录的是本次取得的版本，不能假称这是历史实验当时的版本。

```powershell
.\workbench.cmd run-register RUN-ID --input "data/input.json" --artifact "research/my-topic/result.csv" --preview
.\workbench.cmd run-register RUN-ID --input "data/input.json" --artifact "research/my-topic/result.csv"
```

可重复使用 `--input` 和 `--artifact`；仅接受明确文件，不遍历整个共享盘。相同文件和指纹重复登记不写入；原路径内容变化时拒绝覆盖旧指纹，先为新版本保存新路径或建立新 Run。登记不复制原数据，不自动复核结论。

## 恢复与维护

```powershell
.\workbench.cmd run-registration-rollback --receipt "Run目录/.run-captures/编号/registration.json" --preview
.\workbench.cmd run-registration-rollback --receipt "Run目录/.run-captures/编号/registration.json"
```

恢复只撤销该次 Run 元数据修改，保留原件、结果、日志和回执；如 Run 已有后续修改则拒绝覆盖。恢复登记不撤销脚本的外部副作用。不要手工编辑回执。预览不执行脚本、不创建目录、不修改登记。

`.run-captures` 是保留的原始材料容器，其内部即使有名为 run.json 的结果，也不作为新业务对象发现；真正的 Run 登记仍在父目录。框架升级保留该容器及所有文件、空目录，公共源码不分发业务产物。标准入口是前台执行后收集，没有增加后台文件监听服务。

AI 负责在阶段结束回读 L0 清单，并按 [分层记录标准](RESEARCH_RECORDING.md) 保存 v3 L1 实验技术单元：固定引用本次 Run，检索说明概括问题与边界，稳定正文块解释方法、参数、公式、结果和限制。文稿用独立章节和 document 编排；执行回执不会自动变成技术单元或研究报告。未执行的方法、推导和分析可以保存对应类型的 L1，不虚构一次 run-execute。
