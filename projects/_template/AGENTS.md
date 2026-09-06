# `{{project_slug}}` 项目局部规则

## 按需入口

1. `project.json`
2. `README.md`
3. `context/MODULE_MAP.md`
4. 当前任务相关的核心算法卡、数据卡、契约、ADR 和最近 Run

## 项目特有约束

- 在此填写设备/业务安全边界、主语言、环境建立方式和标准验证命令。
- 在此填写共享盘路径的“别名”，不要写凭据或可外发的真实敏感路径。
- 在此填写项目独有的单位、坐标系、时间基准和接口版本策略。

## 标准命令

```text
setup: TBD
unit-test: TBD
integration-test: TBD
benchmark: TBD
report: TBD
```

实际使用某个命令前补充对应内容；尚未涉及的部分可以保留 TBD，不阻塞首次探索。不要重复根规则或把通用流程全部复制到这里。
