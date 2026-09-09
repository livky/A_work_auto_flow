# L0 原始材料统一入口

写入端现提供 `run-execute` 自动登记新 Python 实验材料、`run-register` 登记明确已有文件及按回执恢复。用法与边界见[执行手册](../RUN_CAPTURE.md)。下方描述的是共同的只读投影；写入完成后无需再创建 source。

L0 是原始材料层；source 是兼容的内部登记类型，不是用户必须再维护的一层。已有 Run 输入、产物、代码快照和元数据，以及记忆中的固定文件引用，均投影为 L0。只读取登记与显式关联，不扫描任意文件夹、不补造执行时哈希、不重复提交原始材料。

## 范围与接口

`memory raw-materials` 接受 owner_id，返回只读条目、固定版本、来源 ID、使用对象/Run、缺口与快照标识。研究汇总 owner_id、related_research_ids 等显式字段和记忆引用指向的 Run；同物理路径及同固定 SHA 合并，不以相同内容哈希合并不同路径。原 source 的修订与说明保留为来源登记关联。

`memory raw-material` 接受 owner_id、material_id、max_chars，从当前合法登记重新定位，核对权限、路径和原 SHA，再返回有界文本或支持的固定图片。版本变化不替换原引用；没有固定哈希的材料仅列登记缺口。原始大文件不自动送入模型上下文，原始正文仍不加入常规知识检索。

对象记忆的 L0 勾选项显示统一材料列表；source 不再单独重复成卡片。其他层照常多选。L0 导出保存材料清单与固定引用，不批量复制原件。通用 Ref 和已有 source 契约保持兼容，不改历史字节或科学复核状态。

## 实施与验证

```powershell
# request.json: {"owner_id":"实际研究或Run ID"}
.\workbench.cmd memory raw-materials --request request.json
# open.json: {"owner_id":"同一ID","material_id":"上一步返回的RAW-ID","max_chars":20000}
.\workbench.cmd memory raw-material --request open.json
```

列表只读登记，不读原件正文。预览至多读取 64 MiB 并核验完整文件指纹；文本至多返回 64000 字符，默认 20000，截断明确标记。PNG/JPEG 至多 2 MiB 可直接显示，其他二进制格式保留路径交由对应工具打开。未登记文件不会自动纳入；缺指纹不以当前文件冒充执行时原件。

后端新增只读适配器与公开动作；前端独立材料组件、筛选和导出集成；更新 README、记录指南和 Research 工作流。快测加入无 source 的 Run、研究聚合、路径/版本去重、多 Run 使用关系、历史版本变化、权限撤销、缺指纹、恶意路径和有界展开；浏览器检查勾选、打开内容、导出及旧行为。预构建资源更新，真实 setup 扩展旧工作区升级/恢复随 quick 门槛执行。

固定开发 Run：`RUN-20260909T103018Z-E452A936D4C1`。执行结果以该 Run 回执为准，人工/科学复核与软件通过分开。
