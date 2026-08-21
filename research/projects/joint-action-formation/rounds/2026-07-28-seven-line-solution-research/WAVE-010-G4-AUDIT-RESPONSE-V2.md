# Wave 010 G4 独立审计回应 v2

日期：2026-07-29  
状态：`REVISED LOCAL SYNTHETIC CHECK / V1 PRESERVED AS FAILURE HISTORY / NOT BLIND`

## 接受审计

审计结论成立，v1 不足以支持此前的两项表述：

1. `LAWFUL_STRONG_CENTER` 只是直接调用 `mature_composition(packet)` 的构造恒等，不是不同
   实现、不同控制策略或独立 strong center。v1 的“因果等价”主张撤回。
2. `recovery_action_accuracy_on_unsafe=1.0` 只表示输出字符串与手写 oracle label 相同，
   没有运行恢复动作、读回恢复后状态或测量恢复时延。它不能称为 recovery correctness。

v1 的三个文件保持不改，继续作为“自检通过但结论过强”的历史证据：

- [`WAVE-010-G4-RELIANCE-FRONTIER.md`](./WAVE-010-G4-RELIANCE-FRONTIER.md)
- [`WAVE-010-G4-RELIANCE-FIXTURE.json`](./WAVE-010-G4-RELIANCE-FIXTURE.json)
- [`WAVE-010-G4-RELIANCE-SIMULATOR.py`](./WAVE-010-G4-RELIANCE-SIMULATOR.py)

后续不得再引用 v1 的 strong-center 等价或 recovery correctness。v2 没有实现、运行或评分
strong center；若未来要比较，必须由不同实现者仅凭公共合同重新实现。

## v2 修复

v2 使用四个新对象：

- [`WAVE-010-G4-RELIANCE-PUBLIC-FIXTURE-V2.json`](./WAVE-010-G4-RELIANCE-PUBLIC-FIXTURE-V2.json)：
  只含模板、公开 overrides 与 split；
- [`WAVE-010-G4-RELIANCE-ORACLE-V2.json`](./WAVE-010-G4-RELIANCE-ORACLE-V2.json)：
  单独冻结 safe truth、预期 decision 与 recovery labels；
- [`WAVE-010-G4-METHOD-WORKER-V2.py`](./WAVE-010-G4-METHOD-WORKER-V2.py)：
  固定方法进程，不含 oracle path、case id 或 evaluator；
- [`WAVE-010-G4-RELIANCE-SIMULATOR-V2.py`](./WAVE-010-G4-RELIANCE-SIMULATOR-V2.py)：
  parent 展开 packet、随机序列化、调用 worker，再用独立 oracle 评分。

每次方法调用只收到：

```text
fresh random opaque_packet_id
fresh random run_nonce
random-key-order serialized method_packet
```

不发送 `case_ref`、split、safe truth、expected decision 或 recovery label。worker 使用
`python3 -I`、临时 cwd 与受限环境变量；相同 packet 连续两次的序列化 SHA-256 不同，固定
worker 输出相同。oracle hash 在全部方法返回前后保持一致。

这个边界只约束当前固定 Python worker。它不是 hostile OS sandbox，也不能防止拥有同一用户
文件权限的恶意 native process 主动读取仓库。

## 新增 held-out 与复合失败

v2 保持 `4 safe / 8 unsafe / 12 total`，用四个 v1 未包含的 runtime split 替换同质 case：

| 新 case | 作用 |
|---|---|
| `T2-STALE-ACTIVE-PERMISSION-HEAD` | status 仍为 `ACTIVE`，但 current head 不匹配；测试 stale-head 不能靠标签绿色 |
| `T2-RECOVERY-UNKNOWN` | operation 当前可跑，但冻结任务要求的 recovery evidence 为 Unknown；测试“当前成功”不能代替可恢复 |
| `T4-MULTI-FAULT` | exact probe fail、permission revoked、reservation conflict、owner stance Unknown 同时存在；测试 evaluator 不只抓第一项或让一个 PASS 覆盖其他失败 |
| `T6-DECLARED-UNQUERYABLE-REVOKED` | dependency 已声明，但 current head 无 query/probe path；测试 `DECLARED` 不等于可判定 |

它们标为 `HELD_OUT` 是相对 v1 denominator 的新运行 split，不是不同研究者生成的盲 holdout。
worker 与 oracle 仍由同一研究流形成，不能据此宣称独立泛化。

## 精确结果

运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/wave010-g4-v2-pycache \
python3 WAVE-010-G4-RELIANCE-SIMULATOR-V2.py --self-test
```

实际结果以 `SELF_TEST_PASS` 结束：

| 固定方法 | confusion | safe recall | unsafe false RELY | abstention | unsafe label-match |
|---|---|---:|---:|---:|---:|
| Declaration only | TP 4 / FP 8 / TN 0 / FN 0 | 4/4 | 8/8 | 0/12 | 0/8 |
| Readiness only | TP 4 / FP 8 / TN 0 / FN 0 | 4/4 | 8/8 | 0/12 | 0/8 |
| Probe + CI + IAM | TP 4 / FP 5 / TN 3 / FN 0 | 4/4 | 5/8 | 1/12 | 2/8 |
| **Reference composition + HITL** | **TP 3 / FP 0 / TN 8 / FN 1** | **3/4** | **0/8** | **5/12** | **8/8** |

最后一行只能解释为：

- 4 个 safe case 中实际 `RELY` 3 个，另一个 unobservable hidden-valid case 被
  `ABSTAIN`，所以 recall 是 `3/4`；
- 8 个 unsafe case 中没有 `RELY`，所以 false reliance 是 `0/8`；
- 总共 12 个 case 中 5 个 `ABSTAIN`，不是零成本安全；
- `8/8` 只表示 unsafe case 的 decision 与 recovery **label** 精确匹配手写 oracle；
  没有执行任何恢复，不能支持恢复成功、时延、Effect、Acceptance 或再次运行。

四个新 held-out case 的结果是 `0/4 unsafe false RELY`、`4/4 label-match only`。这仍是同一
研究流的固定规则回归，不是 blind external evidence。

冻结与运行证据：

```text
public fixture sha256
  f24619a384d89fd3c756d76484a27bf67b1dd460278f2422952861596371bdbb
oracle sha256 before == after
  218b16937760ce36a4b92029d11d5756db529c8069f8ce7239455a7d8f8f6dcb
hidden valid/revoked method packets identical
  true
strong center
  not implemented and not scored
```

JSON 解析、两个 Python 文件编译和完整 self-test 均实际通过。

## 当前仍能保留的判断

本地 fixture 继续支持一个窄方法判断：

> readiness、declaration、probe/IAM 的局部绿灯不足以覆盖 resource、recovery、current head、
> owner stance 与 unqueryable dependency；保守组合能够避免当前 8 个 unsafe case 的 false
> reliance，但会以 hidden-valid case 的 missed reliance 为代价。

它不能证明：

- reference composition 是成熟产品组合的真实实现；
- lawful strong center 与该组合等价、优于或劣于它；
- recovery label 能兑现为安全恢复；
- 这 12 个手写 case 代表现实分布；
- evaluator/oracle 独立于研究者；
- 真实 X1 output、X2 ingress、Authority、reservation service 或 target readback 已运行。

## 下一项高价值行动

不再扩充同作者标签 fixture。下一步应二选一：

1. 由不同实现者只读 public contract，独立实现 strong center 或成熟组合 arm；truth owner
   在其提交后才解封新的 serialized packets 与 oracle；或
2. 优先把 `REAUTHORIZE / RE_RESERVE / RECOVERY_REHEARSAL / GLOBAL_REOPEN` 从 label 变为
   可执行状态转换，运行后由独立 owner readback 新 head、资源状态和再次 attempt。

在这两项至少一项发生前，G4 当前状态是：

```text
REFERENCE_RULE_FIXED_POLICY_LOCAL_SYNTHETIC
STRONG_CENTER_NOT_IMPLEMENTED
RECOVERY_NOT_EXECUTED
REAL_RELIANCE_UNKNOWN
```

本回应不修改 NOW、PROGRAM、X1/M01、X2 合同或正式机制状态。
