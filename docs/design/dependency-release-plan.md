# Windows 依赖分发与术语修订计划

目标：正式框架统一使用“核心算法”；为 Windows x64 提供从本机已验证环境生成的可公开分发依赖 ZIP，使源码 ZIP 在没有系统 Python、Node、Docker 的机台上也能离线一键安装或升级。

## 执行步骤

- [x] S1 清理现行规则、模板、CLI、导航和 Skill 中固定的“测校项”称谓，保留历史记录和明确示例。
- [x] S2 新增独立依赖打包器：按 Python 官方嵌入包、已锁定发行包 RECORD 与模型指纹清单取文件；排除工作数据、数据库、模型下载缓存及未登记文件。提供版本清单、文件 SHA-256、许可证和 ZIP 校验旁车。
- [x] S3 将打包、依赖导入与恢复接入 setup.cmd。PowerShell 在无 Python 时验证并解压依赖 ZIP；版本不匹配提前失败。依赖通过暂存、备份、切换安装，目标配置和业务数据保留，完整自检及索引成功才报告安装完成。
- [x] S4 增加损坏、越界、版本不匹配、恢复冲突、私有数据排除和真实 Windows 中文路径的部署回归；实际打包本地环境，并验证离线安装、升级及数据保留。
- [x] S5 更新 README、部署/迁移说明和状态，运行索引刷新与验证，记录固定 Run 的输入、检查及限制。

## 分发与兼容边界

独立依赖 ZIP 可附在 GitHub Release；源码继续走 Git。当前 Qdrant 是 qdrant-client local，不需要服务器；目标数据库属于业务派生缓存，不进入公共依赖包，升级后按目标来源重建。预构建前端在源码中，使用端无需 node_modules。开发端仍通过 package-lock.json 安装工具链。

不公开现有 portable 全工作区快照，不上传任何内容。本轮先完成可核验的本地产物及发布操作说明。仅支持 Windows 10/11 x64 CPU；第二台物理机和真实业务验证必须明确区分于本机隔离目录验证。

## 参考

- [GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)：可附带二进制，每个资源须小于 2 GiB。
- [Qdrant Python Client](https://github.com/qdrant/qdrant-client/blob/master/README.md)：local 模式不启动服务端。

实施验证：RUN-20260907T094813Z-4EE938390289；125 项回归及真实离线安装、升级、接收端再次打包、恢复通过。分发包已在本地生成，尚未上传 Release。
