# 数据控制平面

## 子目录

- `catalog/`：机器可读数据卡和共享盘引用。
- `contracts/`：schema、单位、质量、SLA、兼容性与分类约束。
- `lineage/`：输入—活动—输出事件和以后接入 OpenLineage/元数据平台的映射。
- `samples/`：获批、脱敏、最小化的小样本；任何私有样本放入被忽略的 `samples/private/`。

## 关系

```text
dataset card  --描述--> 数据是什么、从哪来、能否使用
contract      --约束--> 数据必须满足什么
run manifest  --记录--> 本次实际用了哪个版本/指纹
lineage event --连接--> 哪个活动消费并生成了哪些对象
```

不要把目录最后修改时间当成数据版本。对数据库、网络盘和多文件数据集选择稳定快照、批次、内容哈希或确定性清单哈希，并把算法记录在 `fingerprint` 中。
