# Cohort 003 G1 最终返回

日期：2026-07-30  
状态：`LOCAL SYNTHETIC COMPONENT MODULE COMPLETE / NO FORMAL PROMOTION`

## 结论

已在唯一获准目录中完成 CE-001 的 G1 provenance module。模块从冻结的
`IntentAtCoordinationInterface` 开始，把 clarification prelude 作为上游 hash-linked
artifact 保留但不计入 G1 success；method 只通过通用
`discover(kind, predicates)` owner/service 接口取得现场 evidence，自行构造
candidate/resource/partner，不读取预枚举正确 path、`L_benchmark`、`D_actual`、private
expected label、public/final proposal 或 controller operator 菜单。

任何 positive interpretation 前先运行 invalidity gate。合法输出至多是带当前 owner/evidence
谱系的 `CANDIDATE_NOT_COMMITMENT`，或 `UNKNOWN / REFUSED_OR_UNAVAILABLE /
NOVEL_CANDIDATE_FOR_NEXT_VERSION / INVALID` 等本线结果；没有生成 G2–G7 的 Relation、
Authority、Commitment、Effect、Acceptance 或 Settlement。

本轮没有比较多个 arms，也没有选择方法赢家。现成平台、强中心、成熟组合、模型或人工完整
解决仍然都是正结果；本模块只提供后续组合 runner 可消费的 G1 原生边界。

## clarification prelude 与接口分界

冻结链为：

```text
vague request
→ questions/context
→ IntentCandidate
→ O_Q explain-back
→ O_Q claim
→ IntentAtCoordinationInterface
```

method 只收到最后一个接口对象。prelude 的原文、问题、draft、explain-back 与 claim 不进入
method input，也不进入 G1 recall；接口只携带重新计算并核验的 prelude receipt hash。若
prelude preimage 被替换而 hash 未更新，gate 返回 `PRELUDE_LINEAGE_MISMATCH`。

接口无损保留 CE-001 的 exact `Q@v1`：T0+90min、Venue V/Circuit C7、至少 45 分钟、
3kW±5%、噪声/安全/exact-target/no-other-circuit，以及 requester 与 Venue V 对 exact
Q_version 和实际 Effect 的 Acceptance、之后才可 Settlement。后两项作为冻结任务要求保留，
不是 G1 已实现结果。

## 合法 discovery 与 provenance

candidate、resource、partner 通过三类通用 query 取得。owner service 在 evidence 签发前
检查 query kind、预算、Q/object/deadline/power/exact-target predicates 和 record scope；
wrong-object decoy 不会先泄露再由后置 scorer 拒绝。

每份 evidence 绑定：

- episode、candidate、kind、subject；
- issuer、claim Authority、canonical source；
- recipient、purpose、scope/Q version；
- object/Q payload、t0 existence、observed time；
- disclosure/current 状态与 content hash。

evaluator 分别解析 source alias 与 Authority alias。合法 key 但错误 claim Authority、同源
重命名、跨 episode truth、payload 篡改、t1 receipt 回灌 t0 都在 positive credit 前 hard
fail。事件向量分开 `candidate_sources`、`qualification_sources`、Authority roots、
fact/path-at-t0、qualification/operator change 和 G1 不负责的变化坐标。

## `L_benchmark`、`D_actual` 与 replay

本地冻结 population：

```text
|L_benchmark| = 9
|D_actual| = 6
```

`L_benchmark` 是独立于 method 输出冻结的结构性 candidate/resource/partner path class；
`D_actual` 是其中在 t0 actual policy、query envelope、budget 与 horizon 内存在合法 evidence
path 的子集。signed refusal、policy-blocked 与 t0 尚未形成的 path 不计 actual-policy miss。

当前 population receipt 为：

```text
sha256 = 628d1cc02f8aade57c45b3b167f2e4e35edadff56cf75ffb6d66b924fb81327c
method_sha256 = 9e2a13abba734276a461f43ee8e8efb538d204320165465271e256c423fa91bf
```

receipt 逐 episode 绑定 prelude/interface hash、`L_benchmark`、`D_actual` 与 private
evidence/source/Authority oracle roots；改变分母不能保留同一个 population hash。这些私有
字段不进入 method input。

在冻结 L 外现场发现的合法 owner-backed path 不被伪装成 current-run recall，也不被误判为
provenance invalid；它返回 `NOVEL_CANDIDATE_FOR_NEXT_VERSION`，保留给下一 population
version。

E2 的 operator 由 controller 在 method 运行前施加，method 看不到 answer-shaped operator
menu。三支结果为：

```text
actual  = QUALIFIED_CANDIDATE
remove  = UNKNOWN
reverse = INVALID / REVOKED_EVIDENCE
```

`T0_REPLAY` 重新调用 cloned owner service 签发 t0 evidence；把 full trace 的 t1 partner
receipt 复制进 t0 会返回 `POST_TREATMENT_EVIDENCE_IN_T0_REPLAY`。

## 组合 runner 接口

`python3 runner.py` 输出
`ce001-g1-provenance-module-output-v1`。每个 `g1_handoff` 包含：

- `episode_id / Q_version / object_id / operation_id`；
- `candidate_id / resource_id / partner_id`；
- owner、evidence、source、Authority、recipient/purpose/scope bindings；
- native event vector 与 invalidity reasons；
- `raw_trace_sha256`；
- handoff `output_hash`；
- `explicit_non_claims`。

8/8 baseline handoff 都带 `raw_trace_sha256` 和 `output_hash`。后续组合 runner 可以消费这些
原始 G1 对象，但必须从其他 owner/line 独立取得 Relation、Commitment、Authority、Effect、
Acceptance 与 Settlement，不能从 G1 handoff 推出。

## 实际内部 Agent

1. `/root/g1_a_reconstruct`
   - 只读独立重建原始 G1 问题与 CE-001 接口；
   - 定位 wave-011 的两类 answer leak：`t0_paths` 预枚举，以及 worker 复制
     `final_proposal/public_proposal`；
   - 冻结 prelude/interface、双分母、invalidity gate、事件向量、replay 与组合 handoff
     最小契约；
   - 未编辑文件，未读取期待赢家。
2. `/root/g1_b_implement`
   - 只在 `g1-provenance/` 实现 owner/service session、method、evaluator、runner、fixtures
     与 tests；
   - method 通过动态 receipt 自行构造 candidate；
   - 未写本 final，未实现其他六线。
3. `/root/g1_c_attack`
   - 在不知道期待赢家的前提下先冻结攻击计划；
   - 只新增 `tests/test_adversarial.py` 与 `C-ATTACK.md`，未修改实现；
   - 攻击 truth-copy、answer leak、wrong Authority、source alias、目标偷换、伪成功、
     action envelope、t0/t1、operator 与跨 episode 串分。

Agent 数量不作为独立证据；最终判断来自可重放攻击、raw trace 与根会话复核。

## 红灯历史

首轮 C attack 为：

```text
Ran 25 tests
OK (expected failures=5)
```

这里的退出码 0 不代表模块通过。五个 executable reds 是：

1. 冻结 L 外合法 candidate 被误作 hard invalid；
2. 第四次超预算 query 未使已有 positive invalid；
3. interface 截掉 Acceptance/Settlement 条款；
4. prelude 只比较回显 hash、未重算 preimage；
5. C8 wrong-object record 在 C7 query 下先被披露。

五项均修复，`expectedFailure` 标记被移除并转成普通通过测试。实现过程中还出现过一次
tamper 分支缺少 `dataclasses.replace` import 的 3 个 error，修复后复跑通过。默认
`compileall` 首次尝试写 macOS 用户 cache 被 sandbox 拒绝；将
`PYTHONPYCACHEPREFIX` 指向 `/tmp` 后同一源码编译通过。根会话最后又发现并修复
population receipt 未绑定 L/D/oracle roots 的完整性缺口。

## 最终运行

在目录
`experiments/wave-012-ce001-power-restoration/g1-provenance/` 执行：

```bash
python3 -m unittest discover -s tests -v
python3 runner.py --output /tmp/g1-final-check.json
g1_cache_dir=$(mktemp -d /tmp/g1-pycache.XXXXXX)
PYTHONPYCACHEPREFIX="$g1_cache_dir" python3 -m compileall -q g1prov tests runner.py
```

结果：

```text
tests = 26/26 OK
baseline cases = 8
baseline qualified = 6
baseline refusal/unknown outside D_actual = 2
D_actual = 6/6
L_benchmark = 6/9
failure injections = 5/5 hard INVALID
operator variants = QUALIFIED / UNKNOWN(remove) / INVALID(reverse)
```

五类 failure injection 分别为：

- `WRONG_AUTHORITY`；
- `SOURCE_ALIAS`；
- `TAMPER_PAYLOAD`；
- `TRUTH_TRANSPLANT`；
- `POST_TREATMENT_T0`。

## 能支持 / 不能支持

当前能支持：

- clarification prelude 与 G1 ingress 已形成可执行分界；
- 当前 8-case local fixture 中，candidate/resource/partner 来自动态 owner receipt，而非
  预枚举正确 path 或 final proposal；
- 双分母、source/Authority alias、invalidity-first、t0 replay 与 operator
  removal/reversal 具有可运行判别；
- 输出 schema 可被后续组合 runner 消费且不冒充其他六线。

当前不能支持：

- 真实产品、真实 owner、真实 Authority 或真实供电已运行；
- `6/6 D_actual` 是一般 discovery 能力、现实频率或方法胜负；
- session interface 能抵抗恶意/反射同进程 worker；
- E2 已完成 G2/G3 的关系、条件或 delegation formation；
- E3/E6 的 Effect/readback/migration 已由 G1 解决；
- 完整 CE-001、V1/V2 或七线组合已经闭合；
- 新机制必要性或任何正式机制状态变化。

## 文件

模块：

`experiments/wave-012-ce001-power-restoration/g1-provenance/`

关键入口：

- `README.md`
- `runner.py`
- `g1prov/model.py`
- `g1prov/fixtures.py`
- `g1prov/session.py`
- `g1prov/method.py`
- `g1prov/evaluator.py`
- `g1prov/runner.py`
- `tests/test_g1_module.py`
- `tests/test_adversarial.py`
- `C-ATTACK.md`

本轮未修改 contract、NOW、PROGRAM、Problem、LineContract、机制状态或其他六线目录。
