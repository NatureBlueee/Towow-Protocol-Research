# CE-001 integration preflight

状态：`LOCAL SYNTHETIC VALIDATOR / NOT A CONTRACT EVALUATOR / NOT A REAL PRODUCT RUN`

这个最小 preflight 只阻止假闭包。它接受严格 namespaced 的 G1–G7 局部证据 envelope，
拒绝单线合同字段直通、模拟多 owner、伪 Acceptance、未被 target 消费的 Authority、
非 exact Effect、非独立 O_P、跨 episode component、未知 case 以及缺少真实迁移边界的
E6 输入。

即使输入通过，它也只返回：

```text
preflight_status = QUALIFIED_COMPONENT_OUTPUTS
contract_score_status = CONTRACT_SCORE_NOT_COMPUTED
```

它不实现 A0–A5 完整策略，不计算 `ExactTaskSuccess`、`CorrectResolution` 或
`RecoveryToValue`，也不改变 CE-001 的 `NOT RUN` 与任何正式状态。

## 运行

```bash
python3 preflight.py fixtures/qualified-e1.json
python3 preflight.py fixtures/qualified-e6.json
python3 -m unittest discover -s tests -v
```

拒绝的输入以退出码 `2` 返回；合格的局部输入以退出码 `0` 返回。所有 fixture 都是手写
的本地合成 envelope，只用于验证 preflight 自身，不是 owner、target、现有产品或完整
策略曾经运行的证据。

## 输入边界

- 顶层必须正好有 G1–G7 七个命名空间；
- 每线只能提交 `QUALIFIED_COMPONENT_OUTPUT`，不能自报合同结论；
- 每线必须用 `binding` 逐字段匹配 selected episode 的
  `episode_id/case_id/q_version/object_id/operation_id/target_id`；
- 当前只实现 E1 positive success closure 与 E6 migration-success structure。其他冻结
  case 在 `SUCCESS / REFUSAL / UNKNOWN_OR_REOPEN` admission branch 完成前返回
  `CASE_ADMISSION_NOT_IMPLEMENTED`，不能用 E1 的成功形状冒充 E5 bounded refusal；
- owner source 声明只是 preflight 所检查的 envelope 约束，不证明现实独立性；
- G5 Authority receipt 必须由 G6 target-native consumption 精确消费；
- G6 occurrence、O_Q/O_V Acceptance、O_P finality 必须绑定同一个 episode/Q/object/
  operation/target/Effect；
- E6 另外要求不同 source/target runtime boundary、实际 old-runtime restart 与 old-epoch
  拒绝、lineage hash 和 owner-source recovery。

`fixtures/negative-*.json` 分别固定每个重要拒绝路径，避免以后把红灯悄悄改成绿灯。
当前测试为 `17/17 PASS`。手写 fixture 只证明这些结构拒绝路径；同一 world/run/source
registry 的真实绑定由相邻 `integration-binding-audit/` 独立检查。
