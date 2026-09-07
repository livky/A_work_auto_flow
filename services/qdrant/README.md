# 工作区本地检索运行时

本目录定义 Qdrant Python local 持久化模式、CPU 多语言嵌入模型和 OCR 的便携环境。通过根 `setup.cmd` 安装；配套依赖包可离线导入。无需训练模型，不启动 HTTP 服务；同一数据库串行使用。

从工作区根运行 `automation/workspace.ps1 index-knowledge` 或 `retrieve-context "问题"`。正常运行强制本地推理，缺模型报错，不自动联网。

- runtime：便携 Python 3.12.10 Windows x64、Qdrant client 1.19.0、FastEmbed 0.8.0 等依赖。
- models：量化多语言 MiniLM（384 维），模型文件 SHA-256 记录于 model-manifest.json。
- storage：可重建的 Qdrant 数据库。
- downloads / wheelhouse：离线恢复安装包；checksums.json 校验完整性，requirements.lock.txt 记录依赖版本。
- install.py：默认预览；`--apply --offline` 从本目录缓存恢复依赖。
- download_model.py：默认预览；`--apply` 下载公开模型，可用 `--revision` 指定版本。

分发运行环境使用 `setup.cmd --pack-dependencies --apply`；包内包含按发行清单复制的 runtime、标准嵌入模型及随 RapidOCR 包分发的 OCR 模型，使用端无需 wheelhouse。原有 downloads / wheelhouse 保留用于另一种离线重装方式。详情见 [依赖包与 Release](../../docs/DEPENDENCY_RELEASE.md)。

整个私人工作区搬迁可用 `portable.cmd pack --apply`。外部资料仍需可访问并重新登记路径；搬迁后重建索引。原件、Run 和反馈需要独立备份，不能从向量库恢复完整历史。

完整配置、上下文策略和限制见 [检索手册](../../docs/RETRIEVAL.md)。
