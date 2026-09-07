# 工作台开发与扩展

使用者通过 `setup.cmd --register --open` 安装并打开；开发者才需要 Node。预构建资源随源码分发，Python 服务不调用 npm，不从 CDN 取脚本。

## 代码边界

| 位置 | 职责 |
|---|---|
| `automation/frontend/src/App.tsx` | 应用外壳、静态页面注册、导航与任务状态 |
| `src/Relations.tsx`、`src/Evidence.tsx` | 材料关系、证据页面及交互状态 |
| `src/components.tsx`、`src/group-view.ts` | Canvas、详情对话框、只供展示的聚合 |
| `src/graph-model.ts` | 选择、排除、局部 BFS、范围一致的摘要 |
| `src/cluster.worker.ts`、`src/cluster.ts` | Louvain 与跨组候选的独立 Worker |
| `contracts/graph.schema.json`、`src/generated/contracts.ts` | 图 API 契约与生成类型 |
| `automation/scripts/workbench_app/web.py` | `/api/v1/` 路由、资源清单校验 |
| `service.py`、`cli.py` | 网页与命令行共享用例与输入边界 |
| `projection.py`、`analysis.py` | 业务材料适配、关键词及只读向量分析 |
| `jobs.py`、`storage.py` | 串行任务、进程锁、取消、原子本机存储 |
| `automation/scripts/workbench.py`、`evidence_view.py` | 启动、兼容旧入口、并发 HTTP 与同源保护 |
| `automation/ui/workbench-assets/` | 随发布包交付的 JS、CSS、Worker、许可和哈希清单 |

物理目录不是业务图数据库。正式材料仍为现有 JSON/Markdown 和受控原件；投影、分析、视图偏好和候选独立保存。聚合边不写回正式依赖；`supports`、`input` 与 `contradicts`、`background` 保持原义及方向。

## 开发命令

本次构建环境为 Node 22.11、npm 10.9，依赖精确版本见锁文件。

```powershell
cd automation/frontend
npm ci
npm run build
npm test
npm run e2e
npm run format:check
```

`npm run dev` 监视源码并构建资源与清单。另开终端从仓库根运行 `workbench.cmd workbench --demo`，使用返回地址；修改后手动刷新浏览器。开发与生产使用相同的随机路径和 API，不另开绕过同源保护的代理。首次构建完成后再启动服务；重建瞬间资源不齐时，刷新重试。修改 Schema 后运行 `npm run contracts`，不要直接编辑生成文件。

E2E 在 Windows 使用已安装的 Edge，测试服务仅监听回环地址，`windowsHide` 启动，测试结束关闭。夹具按调用生成到 `.local` 或 `tmp`，不发布实例。非 Windows 开发者需要为 Playwright 配置可用浏览器；当前交付验收针对 Windows。

## 增加页面

在 `src` 添加组件，在 `App.tsx` 的 `pages` 静态数组与页面分支登记，并通过 `api.ts` 调用相对 API。最小页面可只读能力信息：

```tsx
// 固定内部接口；状态失败应显示原因，不将未加载误报为空。
export function Overview({text}: {text: string}) {
  return <section className="card"><h1>概览</h1><p>{text}</p></section>;
}
```

数据写操作走固定服务用例；禁止将用户材料作为 HTML 或脚本执行。需要交互回归时加入 Playwright 场景；测试范围优先验证真实选择、边界及失败行为。

## 增加材料适配器

在 `projection.collect` 中映射已登记源，复用 `file_node`、`target`、`edge`，不要扫描整个共享盘。已有业务 ID 优先，普通文件按相对路径生成身份。最小关系映射示意：

```python
# 必须保留原字段与定位；belongs_to 是归属，不是验证依据。
edge(owner_id, target(existing_ref), 'belongs_to', metadata_path, 'related_ids')
```

新字段需明确其关系方向、指纹来源、缺失行为以及读取边界。把元数据中的 `project_id` 引用误当新主体会造成身份污染；主体只从对应身份卡建立。不要因添加工具适配器创建核心算法卡。

## 增加计算任务

在 `service.request_job` 固定允许的任务类型，计算放独立函数，通过 `Jobs.submit` 排队：

```python
def compute(progress):
    # progress 在批次间检查取消。先完成临时结果，再原子替换缓存。
    result = calculate_from_authorized_inputs(progress)
    progress(1, 1)
    return self.store.write('new-analysis', result)
```

结果记录方法版本、源指纹、范围、排除与遗漏。任务失败不得替换旧缓存。向量只读函数检查既有集合、模型身份与源版本；不创建集合、启动索引或删除锁。CPU 图计算优先 Worker；页面可继续查询轻量状态。HTTP 固定动作，不开放任意命令执行。

## 契约、资源与发布

图 Schema 版本为 1。`contracts.py` 测试 Python 输出；前端类型由同一 Schema 生成。增加接口字段应同步契约、使用方和边界测试；不兼容变更提升 API 版本。

构建后 `asset-manifest.json` 包含资源 SHA-256、所有前端源码哈希和总体源码指纹，附生产依赖及传递依赖许可。启动和框架升级检查源码与构建一致，每次资源响应校验文件。前端源码、锁文件、预构建资源需要一起交付；`node_modules`、测试实例与浏览器报告均排除。

`deployment.framework_files` 按资源清单纳入升级及备份，`portable.py` 排除开发缓存。修改资源后必须重新构建，再运行 Python 回归和 `workbench.cmd verify --profile full`。最后 `refresh-index`、`validate`、`index-knowledge`。完整验证必须包含真实本地模型；基础配置缺模型应明确报告，不能将跳过当作完整通过。

当前保留旧 `evidence-view --serve` 与静态证据页；它们不具备材料图写入接口。新工作台使用生产 CSP，不允许内联脚本。本文扩展代码是接口示意，必须结合已有授权范围和错误处理落地。
