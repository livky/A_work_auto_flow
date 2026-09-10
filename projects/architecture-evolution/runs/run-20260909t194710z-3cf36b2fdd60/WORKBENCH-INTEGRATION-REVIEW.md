# P5 工作台接入前置核查

核对时间：2026-09-10 03:54（Asia/Shanghai；UTC 2026-09-09 19:54）。代码 HEAD：`647d786`，设计与在研修改位于工作树。本报告只读核对设计、后端/前端入口及本机依赖，不修改产品代码、不安装依赖、不启动浏览器或可见窗口，也未运行功能测试。

## 接入位置与单工作台状态

- 现有完整调用链是 `workbench.Controller.app → workbench_app.Service → evidence_view.create_server → workbench_app.web.get/post`。`Service` 在 Controller 构造时创建一次，HTTP Handler 闭包持有同一实例（`automation/scripts/workbench.py:32`；`automation/scripts/evidence_view.py:101`）。在该 Service 中装配一个材料应用服务/QueryCoordinator，并在 `Service.close()` 关闭其任务执行器与取消事件，即可跨 HTTP 请求保留查询状态。
- 不照搬 `web.py:52/88` 的旧 `memory/*` 路由：它每次新建 MemoryService。新路由应调用 Service 持有的协调器，后者按服务端会话绑定 query_id、原请求指纹、候选与固定依据、累计账本、到期时间、操作游标和取消事件。
- “持久”首期指**工作台进程存活期间跨请求保留**。按 CONTRACTS 第 6 节，查询状态不要求跨重启恢复；TTL 默认创建后 15 分钟，过期或进程重启应返回 EXPIRED。维护计划另存受控 `.local` 计划区，不能混进查询内存表或规范业务提交。
- 服务使用 `ThreadingHTTPServer`，同一 query 的活动操作需独立锁和冲突响应；cancel 的 Event 必须能绕过长操作持有的锁。不要持有 `Service.guard` 运行整个查询，否则其他请求和取消会互相阻塞。活动耗时账本与用户等待/TTL 分开；poll 只观察同一任务，不重做搜索或重扣候选额度。
- 旧 `Jobs` 有单线程池和进程 lease，但持久化的是 job_id/status/result（`workbench_app/jobs.py:13`）。它不能直接代替 query 状态：其“成功/失败”不足以表达部分结果、剩余额度和固定候选。可以复用受控执行设施，查询账本仍由协调器唯一维护。

## 路由与前端

`workbench_app/web.py:get/post` 增加明确的 `representations/*`、`materials/*` 白名单，调用共享材料应用适配层。`definitions` 使用 GET，其余按设计 POST JSON。请求必须经过运行校验器，拒绝未知字段和客户端 Context；dataclass 注解本身不验证输入。返回值转换成标准 JSON 结构，tuple 编码数组，不返回类实例、私有数据库对象或 Context handle。

前端继续通过 `automation/frontend/src/api.ts:2` 的相对 `api/v1/` 访问随机前缀，不增加绝对 URL 或开发代理。`App.tsx:18` 的 pages 和 `:198` 附近页面分支登记新的“材料查询”；旧 MemorySearch 保持旧调用语义。当前 MemorySearch 只有 busy 状态、单次 search/expand 和旧 Ref/Result，不能直接视为已经具备新页状态机。

新页需有专用 `Result<T>` helper，保留 status/value/code/warnings/consumed/basis/stop_reason；按 request sequence 和 query_id 忽略旧响应。条件变化使旧结果标为过期输入并清空选择，assemble 携带 expected_request_digest。`null` 与空数组、显式 scope_ceiling、正式 applicability、部分结果和过期提示须真实传递，不能在 React 中写成另一套领域规则。

当前 `scripts/contracts.mjs` 只生成 graph schema 类型和 memory-v3 schema 副本，没有生成新 v0.2 契约。父任务落实产品契约后，需将它接入生成/校验流程；不直接从 design 路径运行产品，也不手写第二套表示枚举。

## 必须解决的契约冲突

| 冲突 | 证据与处理 |
|---|---|
| 首次搜索尚无可取消身份 | 原设计 search 同步返回 SearchReceipt，QueryRequest 没有预分配 ID；浏览器等待首个响应时不知道该 cancel 哪个 query。父任务已决定增加 `materials/start` 即时返回 query_id、`materials/poll` 读取进度，QueryCoordinator.search 保留同步 CLI/测试入口。start/poll 应复用同一任务与账本；HTTP AbortController 只结束客户端等待，不当作服务器已取消 |
| 新 Result 会被旧 HTTP/前端当普通成功 | `evidence_view.py:167` 的 GET 恒 200；`:235` 的 POST 只区分 memory 与 jobs。`api.ts:18` 只在 HTTP 非 2xx 时读取旧 `value.error`。新 rejected/failed 若沿用现状会丢失正确失败语义，且旧异常分支会丢 consumed/basis；按下一节新增专门映射 |
| 结构树逻辑节点缺少展开身份 | 设计 `TreeNode.ref` 可为 null，但 `TreeRequest` 只有 parent_ref，FixedRef 仅 record/file（`contracts.py:307/316`）。全局、owner、L1 等逻辑容器不能伪装成 record Ref。需增加受控 parent_node_id 或明确等价层级游标，服务端验证所属树/会话及当前授权 |
| 缺可验证语义审查回执的 UI 不能自报完成 | 维护 review 接收计划，但 semantic_reviewer/reviewed_refs 不可信任页面自填。首期按已定有界任务包导出/回填桥执行；无真实读取依据时显示待审或可用的人工审查状态，不显示“AI 已审查” |

start/poll 的受理、运行和完成状态应单独表达，不把尚未执行完的任务包装成 Result.ok 的空 SearchReceipt；允许 GET/POST、返回类型和轮询语义需随产品契约与 WORKBENCH 设计同步。

## evidence_view 的具体状态与异常集成

1. 在 `do_GET` 调用新路由的返回点和 `do_POST` 的 `:235` 分支，委托新 API 的统一 `http_status(Result)`；保留旧 `memory.api.response_status`、jobs 的 202 与旧接口错误形状。新状态映射不全局改旧 API。
2. 建议 `ok/partial/cancelled → 200`；`VALIDATION → 400`、`DENIED → 403`、`CONFLICT/STALE → 409`、`EXPIRED → 410`、`UNSUPPORTED → 422`、`INTERNAL/INDEX_FAILED → 500`。有用部分结果保持 200＋partial。无部分结果的 BUDGET/SOURCE_MISSING 映射在现有 CONTRACTS 中未逐项固定，建议明确为 422 后再写测试；异步 start 的传输受理状态另行确定。
3. 新应用适配边界将预期旧 MemoryError 映射为新 Result 及明确 code，保留已有消耗和依据；不要让它落到 `evidence_view.py:242` 的旧 `{error, save_status}`。非预期异常返回清理后的 INTERNAL，不把路径、凭据或未授权对象信息发送到页面。
4. 已通过 Host/Origin/随机前缀检查的新路由若发生 JSON/字段/类型错误，应给新 VALIDATION 回执；尚未创建账本时 consumed 为明确零值，已有查询操作则保留实际累计值。当前 `ValueError/KeyError/TypeError` 分支只返回错误字符串，需要有新路由适配。前置同源/路径拒绝继续通用 403/404，不进入业务处理。
5. 保留现有 500,000 字节普通 v1 JSON 请求上限（clusters 特例 2,000,000）。维护草案/任务包要有大小检查或分批约定，不能因为预算允许读取 2 MiB，就假定 HTTP 也允许同样大的提交。

## trusted access 的实际边界

现有保护是回环监听、精确 Host、随机路径和 POST 精确 Origin（`evidence_view.py:95/161/215`），并非多用户认证或多浏览器隔离。首期可以将 Service 的生命周期作为单本地工作台会话，并由服务端生成 opaque access handle；同一随机入口的页面属于该会话。若以后要求浏览器之间隔离，必须另做真实会话身份，不能仅使用用户可填写的 query_id 或 owner_id。

Context 由路由/应用入口注入，access/budget/cancellation handle 不能从 JSON 获取。请求中的 scope 和 ceiling 只能缩小当前可信范围；include、树选择、已有查询身份都不能扩大来源权限。每次 search/poll 返回内容、assemble/deepen、维护 apply 均按当前来源登记、sensitivity、discovery 和固定来源闭包重检，不能把启动时的全量 owner 列表当永久授权。

树分页与 has_children 要先做可见性判断，再计算数量；不从旧全量 catalog 直接截取一页后才删除被禁止节点。physical/storage view 只返回获准登记位置的解释，不允许任意磁盘路径浏览。新 FixedRef 与旧六字段 Ref 的转换必须使用既有来源登记/固定读取服务，不能依据前端路径重造授权。

## 本地构建与浏览器能力：本次实际结果

| 项目 | 观察结果 |
|---|---|
| 已注册 Node | `C:\nvm4w\nodejs\node.exe`，实际 `v22.11.0`；符号链接目标 `D:\software_work\nvm\nvm\v22.11.0` |
| 已注册 npm | `C:\nvm4w\nodejs\npm.cmd`，实际 `10.9.0` |
| Codex bundled Node | `C:\Users\livky\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`，实际 `v24.19.0`；可作独立运行时，不能据此认为项目锁定包已安装 |
| 本项目开发依赖 | 检查时 `automation/frontend/node_modules` 不存在；runner 要求的 vitest/vitest.mjs、@playwright/test/cli.js、typescript/bin/tsc 均缺失，故 frontend-dev 仍不可用 |
| 其他已注册模块路径 | 检查 Codex bundled node_modules 与 `C:\nvm4w\nodejs\node_modules`，未找到本项目 package.json 的 25 个直接依赖；没有遍历整盘查找未登记副本 |
| npm 缓存 | 配置路径 `C:\Users\livky\AppData\Local\npm-cache`；只读 `npm cache ls` 在 `_cacache/index-v5` 遭操作系统 EPERM，不能据此判断缓存内容齐全或缺失 |
| Edge | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` 存在，版本 `152.0.4191.66` |
| Python 测试入口 | 本工作区 `services/qdrant/runtime/python.exe` 存在；本次未启动测试服务 |

父任务已确认本轮允许按锁文件安装前端开发依赖，并将执行 npm ci；本协作核查没有安装或联网。因此“依赖缺失”是上述时点的状态，安装完成后应重新检查。不要用 bundled Node 中的其他版本包替代 package-lock.json。

## 可复用的真实验证入口

- Python HTTP/安全基础：`automation/tests/test_workbench_relations.py:145` 实际启动 ThreadingHTTPServer，测试 v1 路由、Origin 拒绝和资源哈希；同文件 `:63/:129` 覆盖工作台 lease、任务取消及重启。新材料路由另补真实请求用例：未知字段/Context 注入、同查询并发、初搜 start/poll/cancel、过期、部分回执、结构树空集与权限收紧。
- 浏览器配置：`automation/frontend/playwright.config.ts` 已设 Windows `msedge`、headless、单 worker、1440×1000。`e2e/workbench.spec.ts` 与 `e2e/memory.spec.ts` 使用 `windowsHide:true` 启动隔离 Python 服务；对应 `automation/tests/serve_workbench_test.py`、`serve_memory_test.py` 创建合成工作区，并以 `open_browser=False` 启动。可以复用模式补材料页真实交互，不操作现有业务工作台。
- 新页组件/浏览器验收重点：条件变化后的旧响应、null/[] 范围、组合选择的 digest、防止假取消、初始空态、partial/缺口/预算、逻辑树展开、固定来源与正式/联想分区。旧 MemorySearch 的 busy/search/expand 不涵盖这些行为。
- 安装依赖后在 `automation/frontend` 执行锁定的 `npm run contracts`、`npm run typecheck`、相关 Vitest、选定 Playwright 场景及 `npm run build`。构建会更新预构建资源/许可/源码指纹；`workbench.py:115` 启动时检查源码哈希，不能只改 React 后用旧资源做验收。
- 分级测试 runner 可通过 `--node C:\nvm4w\nodejs\node.exe` 固定本机 Node（`automation/testing/runner.py:422`）。本次只核查入口和依赖可用性，未把任何待执行组件、浏览器、完整升级或第二台物理机检查记为通过。
