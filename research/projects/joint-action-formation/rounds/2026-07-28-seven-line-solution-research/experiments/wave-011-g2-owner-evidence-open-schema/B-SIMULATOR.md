# G2-O1 owner-evidence simulator（内部研究者 B）

状态：`IMPLEMENTED / LOCAL SYNTHETIC`  
作用域：本目录 12-world fixture；不是现实主体签署、成熟 SaaS 集成或 V1/V2 一般解。

## 运行接口

```bash
python3 runner.py \
  --fixture fixtures/public_worlds.json \
  --oracle private/oracle.json \
  --output outputs/results.json
```

默认可省略 `--fixture` 与 `--oracle`。runner 对 12 个 world 分别先启动 owner router，
再对四个 arm 各启动一个 method worker，形成 `12 × 4 = 48` 个 run：

- `STRUCTURED_HUMAN_INSTITUTION`
- `EQUAL_ENVELOPE_STRONG_CENTER`
- `ACTUAL_MATURE_COMPOSITION`
- `SIGNED_REPLICATED_STATE`

四臂收到相同 public world、签名 owner evidence、查询边界与 Authority topology。
`state_placement` 由方法决定（前三臂 `CENTRAL`，第四臂 `REPLICATED`），不从
`authority_topology` 推导，因此 shared/plural Authority 与 central/replicated state
是正交轴。

两个 T5 control 不运行 relation arm 的内部路径。四臂在识别到已预编译平台交易后都直接
执行 `READ_PLATFORM_OFFER → RECORD_PRINCIPAL_PLATFORM_DECISION →
CHECK_PLATFORM_SCOPED_AUTHORITY → READ_PLATFORM_TARGET_OUTCOME`，并输出
`platform_direct=true / relation_artifact_created=false / schema_reopen=false`。它们不创建
CMMN/CLM case、central relation decision record 或 replicated relation state。T5-02 的
Principal decline 因此是平台直接路径的正确负结果，不被改写成 formation failure。

## owner-evidence 边界

`workers/owner_worker.py` 读取一个 private world 后，为每个 Principal 和下列 truth-owner
域启动独立 child process：

- world/schema author
- constitution owner
- private-column oracle
- Authority owner
- target/Acceptance owner
- topology owner

每个 child 随机生成独立 Ed25519 key，只返回 public key、签名事件和 PID。private key
不由输入确定、不写盘、不返回。runner 与 `method_worker.py` 都不能实例化
`PrincipalActor`，输出顶层 `security` 明确记录：

```json
{
  "controller_received_owner_keys": false,
  "methods_received_owner_keys": false,
  "key_material_exported": false,
  "owner_key_processes": {"WORLD/PRINCIPAL": 12345}
}
```

owner event 绑定 `actor_id / principal_id / action / exact relation version /
version digest / sequence / local-view digest / body`。controller 只能核验 public evidence，
不能用自己的 ACK、摘要或账户替换主体 stance。`CLAIM_BASE_ONLY` 的 STANCE envelope
绑定 base version/digest，不会迁移到 candidate。

## evaluator 分域

`g2o1/evaluators.py` 的三个公开入口分别处理：

1. `constitution_evaluator`：`constituted / understood / claimed`
2. `authority_evaluator`：`authorized`
3. `target_acceptance_evaluator`：`activated`

最终 axes 不读取 `private/oracle.json.expected`。它们由签名的 Principal、
constitution、Authority 与 target owner 事件，以及结构化 relation/schema 计算。攻击者
翻转或删除 `expected` 不能改变 measured axes。

schema change 使用 `kernel.analyze_schema_delta` 计算；presentation-only rewrite 与
parameter-only update 不冒充 schema change。schema/source owner 的合法
`SCHEMA_OBSERVATION` 才把 fresh ID 带入 method 的 `proposed_schema`。T4 held-out 的
`ALL_TRUE` 与 `SUM_LTE` relation-level constraints 用独立 assignments 求值。

private-column event 只返回：

- `ABSENT`
- `WITHHELD`（不返回隐藏 column）
- `PRESENT`（策略允许时返回最小 column）

因此 absent、存在但拒绝披露、合法可发现三种状态不会被压成 `NO_COLUMN`。

## 输出与失败闭合

每个 run 包含：

- `owner_events` 与 `method_output`
- 五个布尔 axes 及 independently derived `reference_axes`
- `schema_change`
- `private_column_recall`
- `provenance_opposition`
- `stale_revoke`
- `duplicate_reservation`
- `partition_recovery`
- `cost`

误解、拒绝、silence、partial opposition、stale stance、revoke 和 duplicate
reservation 都不会产生一个笼统 `FORMED/GREEN`。partition/equivocation 只改变恢复/同步
诊断；不能据此把 replicated placement 的差异写成 G2 关系构成优势。

## 本地验证

实现完成时的实际自检：

- `py_compile`：通过；
- runner：`12 worlds / 48 runs / 四臂逐 world 完整覆盖`；
- 非退化 axes（当时 fixture）：既有 positive，也有 misunderstanding、refusal、stale、
  revoke、duplicate、column absent/withheld 等 negative；
- T2-01、T4-04、T5-01 为完整正例；T2-02、T2-04、T4-01/02/03 在相应轴 fail closed；
- 生成 key 的 actor processes 每 world 多于三个，且跨至少两个真实 PID。

测试绿灯只证明本地 synthetic contract；它不证明真实 owner 理解/认领、外部系统
Authority、目标域 Acceptance、成熟产品迁移或生产恢复。
