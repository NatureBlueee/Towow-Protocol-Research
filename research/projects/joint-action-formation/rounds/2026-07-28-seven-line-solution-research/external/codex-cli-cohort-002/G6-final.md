# 第二批 Codex CLI G6 最终返回

日期：2026-07-29  
状态：`VALID LOCAL SYNTHETIC GATES PASS / 12-PAIR DISCRIMINATOR COMPLETE / NO FORMAL PROMOTION`

## 结论

本 cohort 已在指定目录实现并实际运行 G6 的 12 组 paired worlds。整轮先通过
truth-copy、method-alias、wrong-object、read-skew 与 unauthorized-real-effect 五道失效门，
再启用 private-oracle comparison。

当前最强结果是：

> 在这组有限、合成、owner source 可读且规则冻结的 worlds 中，普通
> transaction/outbox/workflow/readback composition、人类制度和合法强中心都能无损重建
> G6 的承重差异。S1 unified authority 和 S3 exact lawful delegation 中的中心闭合是完整
> 正结果；S2 independent owners 中同一中心的 substitution 被阻断。当前没有观察到需要
> 新 Effect protocol 的 residual。

这不是“架构都一样”。三个 Authority stratum 的结果不同：

- S1：单一主体真实拥有相关 action、target、acceptance 与 settlement authority 时，中心
  可以直接闭合；
- S2：Authority 未转移时，中心不能代签 owner；真实 Effect 仍保留，但不能计入 episode
  success，且必须恢复；
- S3：精确对象、criterion、期限和 delegator chain 均有效时，委托中心闭合是正解。

这也不是固定五级 ladder 的胜利。本轮实现保留：

- raw occurrence；
- owner claim/current head；
- episode binding；
- Authority；
- `CountsTowardQ`；
- recovery relevance；
- causal attribution；
- obligation-specific Settlement；
- temporally consistent derived control。

同一 occurrence/claim 可通过独立 `RoleAssignment` 在不同 episode 承担多个角色；不会为
每个 role 复制一份现实。

## 实际多 Agent

本 CLI 实际创建并运行三名内部研究者，没有 capability failure，也没有模拟子 Agent：

1. `/root/g6_semantics_a`
   - 职责：occurrence/claim/role/Authority/obligation 的无损语义；
   - 产物：`model.py`、`SEMANTICS.md`、`tests/test_semantics.py`；
   - 结果：raw occurrence、qualification/authority、obligation/control 三图层；
     owner ledger 仅承载 claim/current head；Settlement scheme subgraph；
   - 验证：13/13 tests PASS。
2. `/root/g6_runner_b`
   - 职责：owner-native readback 与 12-pair runner；
   - 产物：八类 owner source、private oracle、owner services、三个 worker、runner；
   - 结果：12 pairs × 3 strata × 3 implementations = 108 records，216 次 worker 执行；
   - 修复：method packet 使用 opaque token；P3 保留 wrong-target causal edge；P4 从 head
     自算 freshness；P11 从有效区间自算 consistent cut。
3. `/root/g6_attacks_c`
   - 职责：攻击 truth-copy、method alias、wrong object、read skew、unauthorized real
     Effect；
   - 产物：`gate_runner.py`、`tests/test_invalidation_gates.py`、`ATTACK-NOTES.md`；
   - 结果：五门都要求恶意 double 被检出且 benign control 被接受；五类 matrix mutation
     均令整轮 `INVALID`。

主会话逐项读取三份返回，拦截并修复了四个会削弱判别力的问题：

- `P1-A/P1-B` 标签可能从用户提示旁路泄漏，改为 opaque world token；
- worker 一度把 role 内嵌到 occurrence，改为统一独立 `RoleAssignment`；
- wrong-target Effect 一度可能被归为 pre-existing/other，改为
  `EXACT_ATTEMPT_WRONG_TARGET`；
- cut/freshness 一度可能直接读取 `consistent/STALE` 标签，改为由各 worker 从
  head/version/validity intervals 独立计算。

Agent 数量不作为证据。三个 worker 虽有不同源码、路径和 decision root，但由同一 cohort
构造；这不是三个外部组织或模型的独立现实复现。

## 实现

目录：

`research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/`
`experiments/wave-011-g6-role-causality-discriminator/`

关键文件：

- `README.md`：范围、运行、结果与边界；
- `model.py` / `SEMANTICS.md`：无损 G6 semantic model；
- `fixtures/pairs.json`：runner-private pair index；
- `fixtures/execution_sensor.json`：Attempt boundary sensor；
- `fixtures/target_store.json`：target-native transition store；
- `fixtures/adoption_store.json`：operational adoption store；
- `fixtures/acceptance_acts.json`：institutional act register；
- `fixtures/obligation_store.json`：obligation/scheme subgraph；
- `fixtures/authority_store.json`：S1/S2/S3 mandate/delegation current head；
- `fixtures/claim_heads.json`：owner claim/current-head carrier；
- `fixtures/cut_store.json`：owner head validity intervals；
- `private_oracle/expected.json`：运行后 grader oracle；
- `owner_services.py`：owner-native API；
- `workers/strong_center.py`；
- `workers/mature_composition.py`；
- `workers/human_institution.py`；
- `runner.py`：108-record matrix；
- `gate_runner.py`：五道整轮失效门；
- `evaluator.py`：private-oracle finite fixture comparison；
- `experiment.py`：one-command runner；
- `tests/`：31 项语义、门禁与集成测试；
- `RESULTS.json`：紧凑结果；
- `RUN-RAW.json.gz`：完整 method output、owner observations、trace 与 comparison。

`RESULTS.json` 绑定压缩 raw archive 的 SHA-256、压缩和未压缩字节数。完整 raw JSON 经过
gzip 保存，使落盘输出保持在当前 LineContract 的 2 MiB output budget 内。

本轮没有修改 `research/NOW.md`、`PROGRAM.md`、Problem、LineContract、MechanismProfile
或任何正式研究状态。

## 五道失效门

实际 matrix gate readback：

| Gate | 攻击读回 | Benign control | 结果 |
|---|---:|---:|---|
| truth-copy | reference access-trace attack 被检出；actual 8 个 owner fixture paths，oracle hash 不变 | 8/8 native paths | PASS |
| method-alias | shared executable/decision-root double 被检出 | 3 个不同 source hash、module、executable identity | PASS |
| wrong-object | 9/9 wrong-target rows 保留 raw Effect、not-counting 与 recovery | 150/150 | PASS |
| read-skew | 9/9 non-overlapping head vectors 阻断伪完成 | 189/189 | PASS |
| unauthorized real Effect | 12/12 rows 保留 real Effect、`CountsTowardQ=false` 与 recovery | 204/204 | PASS |

任一 detector 被禁用，或对实际 matrix 注入对应 semantic collapse，整轮均变为：

```text
INVALID
coverage_allowed = false
```

truth-copy actual gate 的边界必须如实保留：它检查受信 runner 的独立 fixture paths、source
manifest 与 oracle hash immutability；自包含恶意 double 使用真实 access trace。它不抵抗
拥有同目录读取权限的恶意本机进程。

## 12 pairs 的结果

每一 pair 在 3 strata × 3 implementations 下各有 9 records：

| Pair | 判别 | 结果 |
|---|---|---:|
| P1 | authorized no-effect / unauthorized real-effect | 9/9 |
| P2 | pre-existing current state / exact attempt caused | 9/9 |
| P3 | correct target / wrong-target real damage | 9/9 |
| P4 | fresh head / signed stale head | 9/9 |
| P5 | Effect only / Effect + actual Adoption | 9/9 |
| P6 | correct Acceptance object / same owner wrong version | 9/9 |
| P7 | one owner Accept / another Reject | 9/9 |
| P8 | provider Settled / beneficiary PaidOut | 9/9 |
| P9 | payout complete / chargeback or reversal open | 9/9 |
| P10 | timeout before commit / timeout after Effect | 9/9 |
| P11 | consistent cut / read-skew | 9/9 |
| P12 | independent owners / lawfully delegated single center | 9/9 |

private evaluator 对每个 implementation/stratum 检查 88 个已冻结字段：

```text
strong center       S1 88/88  S2 88/88  S3 88/88
mature composition  S1 88/88  S2 88/88  S3 88/88
human institution   S1 88/88  S2 88/88  S3 88/88
```

这些数字只表示有限 fixture conformance。正确的 `REJECT`、`RECOVER_AND_BLOCK`、
`BLOCK_DISPUTED` 与 `BOUNDED_UNKNOWN` 都计作正确，不表示 episode 全部完成。

## 语义上真正改变了什么

### 1. `QualifiedEffect=false` 不再删除现实

P1 unauthorized real Effect 与 P3 wrong-target damage 都同时保留：

```text
raw occurrence       = TRUE
episode binding      = false 或 Authority invalid
CountsTowardQ        = FALSE
recovery relevance   = REQUIRED
causal attribution   = exact attempt
```

这使未授权或错对象损害不会从恢复、责任和 affected target 中消失。

### 2. readback 只回答它真正观察到的内容

P2 分开：

- current postcondition 已由第三方预先建立；
- exact attempt 产生 transition。

P4 的签名旧 head 不因“有签名”成为 current truth。P11 的每条 owner head 都可能真实，但
无共同有效 cut 时不能派生 `Done`。

### 3. Settlement 不是 bool

P8/P9 按 obligation + scheme subgraph 区分：

```text
provider settled
beneficiary paid out
payout reversible
reversal/chargeback open
final
```

payment provider 的 `Settled` 不自动解除 beneficiary 或合同义务。

### 4. Authority 而非中心化拓扑决定可闭合性

P12 是本轮最有价值的正结果：

- independent owner 自己 action/accept：合法；
- center 在 S2 代行：阻断；
- center 在 S1 unified authority：合法；
- center 在 S3 exact delegation：合法。

因此不能把“中心”写成失败，也不能把“中心技术上能做”写成 Authority。

## 合成成本

三种方法都获得相同 owner APIs、输入和 disclosure：

| Implementation | synthetic latency | HITL calls | compute units | disclosure units |
|---|---:|---:|---:|---:|
| strong center | 3528 ms | 0 | 360 | 648 |
| mature composition | 3744 ms | 0 | 576 | 648 |
| human institution | 5256 ms | 72 | 216 | 648 |

这只反映当前本地 cost constants。不能据此声称真实强中心成本最低、人工方案更差，或做商业
净价值排序。

## 验证

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g6-role-causality-discriminator

PYTHONPYCACHEPREFIX=/tmp/g6-wave011-pycache \
  python3 -m unittest discover -s tests -v
```

结果：

```text
Ran 31 tests
OK
```

完整运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/g6-wave011-pycache \
  python3 experiment.py --output RESULTS.json --raw-output RUN-RAW.json.gz
```

结果：

```text
status              VALID_LOCAL_SYNTHETIC_GATES_PASS
gate_status         GATES_PASS
pair_count          12
world_count         24
record_count        108
passed_record_count 108
```

附加检查：

- `py_compile`，pycache 指向 `/tmp`；
- 所有 JSON 与 gzip raw archive 可解析；
- raw archive 内 `record_count=108`；
- oracle before/after SHA-256 相同；
- `git diff --check`。

## 证据边界

本轮可以支持：

- role 不是固定 ladder，而是 occurrence/claim 相对 episode 的 assignment；
- raw occurrence、Authority、episode binding、CountsTowardQ 与 recovery relevance 必须
  正交；
- owner ledger 是 claim/current-head carrier，不是自动 reality oracle；
- mature components、human institution 和 lawful center 都是完整解候选；
- 当前有限分母没有观察到 novel Effect protocol residual。

本轮不能支持：

- X2 已运行：X1 finalized actual outputs 不存在，本目录不是 X2 population；
- 真实 Effect、真人 Adoption/Acceptance、现实付款或生产 recovery；
- owner API 在 hostile local process 下不可读取/篡改；
- 三种实现的现实成本、可靠性、迁移或一般优越性；
- connector migration、长期漂移或跨组织 legal finality；
- PROGRAM coverage、正式 claim promotion 或机制状态改变；
- “未来所有环境都不需要新机制”。

下一项若要改变证据强度，不应继续复制更多同源 synthetic pairs，而应选择：

1. 让另一实现者只读公开 schema，独立重实现至少 mature composition 或 human institution；
2. 把 workers 放入无权读取 private oracle/owner stores 的权限域；
3. 使用低风险、可撤销的 target-native sandbox readback，真实注入 ACK loss、stale head 和
   exact delegation；
4. 等 X1 actual finalized outputs 存在后，再按 X2 contract 机械形成 population。

本轮未联网、未执行现实 target write、未付款、未取得真人 Acceptance，也未发送任何外部
消息或材料。
