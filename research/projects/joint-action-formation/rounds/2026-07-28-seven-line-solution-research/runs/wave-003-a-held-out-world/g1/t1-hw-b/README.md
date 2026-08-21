# Wave 003-A / G1 / T1-HW-B

这是独立于 HW-A 的 G1 留出世界 truth/scoring 包。它用于比较候选方法是否能在分区、本地私有、
动态和 policy 约束下恢复可发现机会，同时保留不可发现性与认识论状态。

本目录不包含候选方法，也不运行候选解。`fixtures/scorer_conformance_receipt.json` 是人工构造
的 scorer 校准件，只证明评分器能够接受一份闭合回执；不能计作候选实验结果。

## 权限边界

- 方法可见：`method-visible/README.md`、`method-visible/submission_schema.json`，以及
  controller 从 `delivery-packets/` 中选择的一个 recipient packet。
- Controller-only：`controller_input.json`、`packet_builder.py`、跨 recipient index。
- Scorer-only：`oracle_truth.json`、`scorer.py`、fixture、mutation 和测试。

目录分隔不是密码学隔离。正式盲跑必须使用独立读取域：coordinator 只能读
`coordinator.json`；每个本地 solver 只能读自己的 `local/<recipient>.json`；任何候选进程
都不能获得整个 delivery 目录、controller source、oracle、scorer 或校准件。

## 生成与验证

```bash
python3 packet_builder.py --output-dir /tmp/t1-hw-b-packets
python3 -m unittest discover -s tests -v
python3 scorer.py --submission fixtures/scorer_conformance_receipt.json
```

Scorer 只接受候选自有 ID 与可观察签名，输出不会回显 latent item ID。评分结果只说明一份回执
在这一个合成留出世界中的符合性，不证明现实频率、净价值、普遍性或协议独占性。
