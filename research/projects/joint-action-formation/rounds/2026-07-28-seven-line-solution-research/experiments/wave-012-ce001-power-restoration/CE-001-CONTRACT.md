# CE-001 社区工作坊临时供电恢复：跨七线组合 episode 合同

日期：2026-07-29  
状态：`FROZEN CANDIDATE INPUT / NOT RUN / NO FORMAL PROMOTION`

## 1. 研究目的

本实验不寻找“通爻独占”或预设新协议。它检验：

> 现成平台、合法强中心、通用模型、成熟组件组合、确定性 workflow 和人工制度，能否在
> 同一个完整任务中，无损串起 G1–G7 并真正解决问题。

任一现有路径完整解决就是正向结果和通爻方案组成。只有所有合理现成路径在同一个有界
residual 上重复失败，才考虑新机制。

## 2. 冻结来源

| 输入 | SHA-256 |
|---|---|
| `problem/v2.json` | `cb6d4bd9c5930181df9176957daa144085a3eaf9f1edfc3c3992cd87f94a2f46` |
| `solution-first-composition-method-correction-2026-07-28.md` | `407fd3418ca4d6595aa28f07c1d0ad737bfc341e904a9040b920f51ced9f5a13` |
| cohort 002 `ROOT-ADVERSARIAL-AUDIT.md` | `687e85daee150d7a10d656592400cc1c21678bc1cfc41f8ba5a0dc5ee4099fc1` |
| cohort 002 `SYNTHESIS.md` | `e00646f6b08da3be665bd8a14c9cc4ad79b806a1f45b6120a08effa89e677e7b` |

若任一来源改变，本合同不自动同步；必须形成新版本。

## 3. 从模糊请求到正式 Intent

初始请求：

> 今天的社区工作坊不能因为停电取消，帮我处理。

这段请求先经过独立的 clarification prelude：

```text
vague request
→ questions / context read
→ IntentCandidate
→ O_Q explain-back
→ O_Q claim
→ IntentAtCoordinationInterface
```

prelude 不计入 G1 success，避免把 V2 接口上游的 `vague goal → Intent` 偷算成 G1 能力。
它的 transcript、问题、版本变化和 O_Q 认领仍保留，供下一轮单独研究 query genesis。

冻结后的 `Q@v1`：

> 在 `T0 + 90min` 前，为 Venue V 的 Circuit C7 提供连续不少于 45 分钟、
> `3kW ± 5%` 的临时供电；满足噪声、安全和 exact-target 限制；不得给其他线路送电；
> requester 与 venue 必须对 exact `Q_version` 和实际 Effect 作出 Acceptance；之后才进入
> 相应 Settlement。

成功不能通过改成“找到一个电源”“发出请求”“安全停止”或给别的线路送电来取得。

## 4. Truth owners

Owner 分离不是隐私限制。当前研究允许把全部非凭据材料发送给外部模型；分离的目的是防止
controller 或 solver 自造事实、Authority 和结果。

| Owner | 权威范围 |
|---|---|
| `O_Q` | Q、Q_version、不可替代约束、task change、requester Acceptance |
| `O_V` | Venue V、Circuit C7、target-native operation、venue Acceptance |
| `O_R` | 电池/发电资源、服务承诺、撤销、resource effect |
| `O_S` | 安全资格、policy version、exact-operation approval |
| `O_P` | 付款授权、beneficiary obligation、Settlement |
| `O_E` | target-native sensor/readback、Effect occurrence 与 operation binding |

签名只证明相应 owner 对 exact bytes 的 act，不自动证明理解、current、Effect、Acceptance
或法律充分性。每个 owner 可以拒绝、延迟、撤销或返回 Unknown。

## 5. Authority strata

每个 case 明确属于一个 stratum：

1. `U / LAWFULLY_UNIFIED`
   - 同一 Principal 确实拥有全部必要 Authority；
   - 中心能合法访问完整输入并控制 target；
   - 强中心若完整解决就是正解。
2. `D / EXACT_DELEGATION`
   - owner 对 exact object/version/scope/expiry 完成合法委托；
   - 委托中心若完整解决就是正解。
3. `P / PLURAL_INDEPENDENT`
   - 多 owner 保留独立拒绝、撤销与 Acceptance；
   - 技术权限或管理员账号不等于 Authority 转移。

不得把 P 中 all-block 与 U/D 的执行成功混在同一总体分数。

## 6. 八个冻结 case

| Case | 核心设置 | 正确结果类型 |
|---|---|---|
| `E0-PLATFORM-DIRECT` | venue 自有合格电池、人员与 Authority | 直接成功；不得强造 relation |
| `E1-EXTANT-MULTI-OWNER` | 资源、关系、权限已存在且 current | 现成 routing/workflow/IAM/readback 应可闭合 |
| `E2-CONDITION-FORMATION` | 能力存在，但 purpose token、短期 delegation 与合作条件需 owner interaction 形成 | 形成后成功；remove operator 后失败或 Unknown |
| `E3A-ACK-LOST-EFFECT` | submit response 丢失，Effect 已发生 | exact-object readback 后继续，不重复 Effect |
| `E3B-ACK-LOST-NO-EFFECT` | method-visible prefix 与 E3A 相同，Effect 未发生；另有 wrong-object success | 正确区分并安全重试/重建 |
| `E4-REVOKE-WITH-ALTERNATIVE` | reserve 后资源方撤销，存在合法替代方 | 恢复、重发现、重新构成并完成 Q |
| `E5-IMPOSSIBLE-REFUSAL` | non-delegable venue owner 拒绝且无替代 | 无 Effect、有界拒绝；不能越权 |
| `E6-MIGRATION-REPLAY` | Effect 后、Acceptance 前 coordinator 崩溃迁移，旧 runtime 重启 | 不重复 Effect，恢复 Acceptance/Settlement 谱系 |

E3A/E3B 必须在允许交互前保持同构；正确动作必须真正形成区分，否则不能宣称有判别力。
如果某 pair 用来证明 safety-liveness 前沿，oracle 必须给两个 world 相反的最优要求，并分别
计 safety loss 与 liveness loss，不能重复 G7 `w010/w011` 的错误。

## 7. 比较 arms

| Arm | 必须实际实现的边界 |
|---|---|
| `A0-PLATFORM-DIRECT` | 只在平台原生完整承担任务的 applicable case 运行 |
| `A1-LAWFUL-CENTER` | 仅 U 或 D；不能在 P 代签 owner |
| `A2-EQUAL-INFORMATION-CENTER` | 与其他臂同 information/API/action，无外部 owner substitution |
| `A3-GENERAL-MODEL-MATURE-STACK` | 模型做澄清、规划、工具选择；现成组件做 policy/workflow/fence/readback/settlement |
| `A4-DETERMINISTIC-MATURE-COMPOSITION` | 不用通用模型推理；规则、workflow、IAM、outbox、fence、readback、HITL |
| `A5-BOUNDED-HUMAN-INSTITUTION` | 人类在相同信息、时间、action 和 Authority envelope 内处理 |
| `A6-RESIDUAL-CANDIDATE` | 只有 A0–A5 在同一 residual 上失败后才允许实例化 |

### 独立实现硬门

- A0–A6 不得共同调用一个 `_common_candidate`、`choose(packet)` 或共享 decision root；
- arm-specific state、queries、actions 和 recovery 必须来自各自 executor；
- evaluator、owner APIs 和 target simulator 可以共享接口，不得向 arm 返回 expected label；
- source hash 不同只证明字节不同；还要用 sabotage、truth transplant 与行为差异 mutation
  排除语义 alias；
- 实际未安装/未运行的产品必须写 `NOT_RUN`，不能用 shape fixture 冒充。

## 8. 冻结时间线

```text
P0 prospective prediction
→ owner queries / clarification / formation
→ P1 newly frozen prediction
→ reservation / commit-time Authority
→ first attempt
→ Effect readback
→ Adoption / Acceptance / Settlement
→ recovery / reopen / migration
```

每个时点只能消费当时合法可得的 evidence。最终方案、最终 receipt、grader truth 和未来
owner decision 不能注入 P0/P1。

## 9. 预注册 interventions

- `REMOVE_FORMATION_OPERATOR`
- `REVERSE_OWNER_DECISION@read`
- `REVERSE_OWNER_DECISION@sign`
- `REVERSE_OWNER_DECISION@reserve`
- `REVERSE_OWNER_DECISION@execute`
- `DROP_SUBMIT_ACK@effect`
- `DROP_SUBMIT_ACK@no-effect`
- `WRONG_OBJECT_READBACK`
- `TARGET_IGNORE_FENCE`
- `TARGET_RESTART_LOSES_EPOCH`
- `CRASH_AFTER_EFFECT_BEFORE_ACCEPTANCE`
- `OLD_RUNTIME_RESTART`
- `DROP_MIGRATION_CAPSULE_FIELD`
- `MATERIAL_Q_CHANGE_BY_O_Q`
- `MATERIAL_Q_CHANGE_BY_CONTROLLER`

最后一项必须被分类为 substitution/invalid，不得用任务偷换获得 success。

## 10. 原生结果向量

不先生成单一总分。每个 arm/case 返回：

- `ExactTaskSuccess`
- `CorrectResolution`
- `AchievableSuccessCoverage`
- `AllCaseResolutionCoverage`
- `UnsafeEffect`
- `DuplicateEffect`
- `WrongObjectReliance`
- `RecoveryToValue`
- `UnreconciledEffect`
- `MissedReopenNodes / OverReopenNodes`
- `CandidateExclusiveSuccess`
- cold/repeat cost
- owner queries、disclosure、wait、human minutes、compute/tool、recovery、governance cost

七线保留自己的原生坐标，通过
`episode_id/Q_version/object_id/operation_id/owner_id/evidence_hash` 连接；不能把七线压成
一个共享 truth label。

## 11. 关闭与创新判据

在这个冻结 family 内，任一现有 arm 若满足：

- 七个可达 case `7/7 ExactTaskSuccess`；
- 八个 case `8/8 CorrectResolution`；
- unsafe、wrong-object、duplicate、history rewrite 均为 0；
- E4 恢复到任务价值，E5 不越权，E6 恢复完整谱系；
- candidate-exclusive success 为 0；
- remove/reverse/migrate、blind holdout 与第二实现仍复现；
- 协调、验证、恢复和治理成本没有吞噬任务价值；

则登记：

```text
EXISTING_COMPOSITION = POSITIVE_SCOPED_SOLUTION
NOVEL_MECHANISM_NECESSITY_FOR_CE-001 = CLOSED
```

只有同一 residual 在至少三个 holdout episode、两个任务域、两个 truth author 和两个独立
实现中重复，且 A0–A5 与合理 adapter 都在同一合法 envelope 下失败，才创建 A6 的有界
机制候选。

## 12. 当前证据状态

```text
CONTRACT = FROZEN CANDIDATE
CASES = SPECIFIED / NOT INSTANTIATED
OWNER SERVICES = NOT IMPLEMENTED
ARMS = NOT IMPLEMENTED
RUNS = 0
RESULTS = NONE
FORMAL STATUS CHANGE = NONE
```
