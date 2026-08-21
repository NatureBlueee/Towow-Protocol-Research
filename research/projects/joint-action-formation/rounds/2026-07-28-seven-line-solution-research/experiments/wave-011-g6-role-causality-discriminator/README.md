# Wave 011 G6 role/causality discriminator

状态：`LOCAL_SYNTHETIC / SECOND CODEX CLI COHORT / NO FORMAL PROMOTION`

本目录实现 G6 审计要求的 12 组 paired worlds。目标不是制造新的 Effect 协议，也不是用
一组绿色测试证明现实闭环，而是先判断以下语义能否在独立 owner observation、独立方法实现
和受攻击 evaluator 下无损保留：

- raw occurrence、claim/current head、episode binding、Authority、`CountsTowardQ` 与
  recovery relevance 分开；
- role 是 occurrence/claim 到 episode 的多对多 assignment；
- occurrence/provenance、qualification/authority、obligation/control 是三个可引用图层；
- owner ledger 只承载 claim/current head，target state、sensor observation 和
  institutional act 分别由 owner-native service 产生；
- Settlement 按 obligation 与 scheme-specific phase/finality/reversal subgraph 判断；
- S1 单一统一权威、S2 独立 owner 同权限、S3 合法委托是不同 Authority strata；
- strong center、mature composition 与 human institution 使用不同 executable，允许任何
  一个在其适用 stratum 内完整获胜。

## 12 组 pairs

| Pair | A / B |
|---|---|
| P1 | authorized no-effect / unauthorized real-effect |
| P2 | pre-existing current state / exact attempt caused |
| P3 | correct target / wrong-target real damage |
| P4 | fresh head / signed stale head |
| P5 | Effect only / Effect + actual Adoption |
| P6 | correct Acceptance object / same owner wrong version |
| P7 | one owner Accept / another Reject |
| P8 | provider Settled / beneficiary PaidOut |
| P9 | payout complete / chargeback or reversal open |
| P10 | timeout before commit / timeout after Effect |
| P11 | consistent cut / read-skew |
| P12 | independent owners / lawfully delegated single center |

Pairs 是有限合成本地判别器，不估计现实频率。它们不得被包装为 X2 主评分 population，也
不得改变 `NOW.md`、`PROGRAM.md`、Problem、LineContract 或 MechanismProfile。

## 整轮失效门

coverage 或方法比较之前必须先运行五道 gate：

1. `truth-copy`：owner API 不能由 grader/private oracle row 直接复制；
2. `method-alias`：三个方法不能是同一 decision function 的改名；
3. `wrong-object`：错误目标的真实损害不能被正确 episode 的不合格状态吞掉；
4. `read-skew`：来自不同有效切片的真实 head 不能合成伪 `Done`；
5. `unauthorized-real-effect`：未经授权的真实 Effect 必须保留 occurrence 与恢复责任，同时
   `CountsTowardQ=false`。

任一 gate 未检出其预注册攻击，整轮状态必须是 `INVALID`，不得报告 coverage。

## Truth boundary

方法进程只接收公开 episode packet 与 owner-native API response。private oracle 只供
evaluator 使用。owner service 从自己的 store、sensor 或 institutional act 生成 response；
owner ledger 仅保存 owner claim/current head。相同进程与本地文件权限不构成恶意本机隔离，
因此这里的保证是受信 runner 下的 solver/evaluator 数据流隔离，不是密码学沙箱。

## 文件

- `model.py` / `SEMANTICS.md`：无损语义模型与三图层约束；
- `fixtures/`：八个相互分离的 owner-native sources；`pairs.json` 仅供 runner 使用；
- `private_oracle/expected.json`：只供运行后 evaluator 使用；
- `owner_services.py`：从 store/sensor/institutional act 生成 owner response；
- `workers/`：strong center、mature composition、human institution 三个独立 subprocess；
- `runner.py`：产生 12 pair × 3 stratum × 3 implementation = 108 records；
- `gate_runner.py`：五道 mandatory invalidation gates；
- `evaluator.py`：运行后 private-oracle fixture conformance；
- `experiment.py`：一条命令完成 runner、gates、evaluation 和结果保存；
- `RESULTS.json`：紧凑结果；
- `RUN-RAW.json.gz`：全部 method output、owner observation、trace 与 oracle comparison 的
  gzip 压缩 JSON，hash 由 `RESULTS.json` 绑定。

## 运行

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g6-role-causality-discriminator

PYTHONPYCACHEPREFIX=/tmp/g6-wave011-pycache \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/g6-wave011-pycache \
  python3 experiment.py --output RESULTS.json --raw-output RUN-RAW.json.gz
```

## 本 cohort 的实际结果

```text
tests                         31 / 31 PASS
matrix                        12 pairs / 24 worlds / 108 records
worker executions             216
invalidation gates            5 / 5 PASS
private-oracle record checks  108 / 108 PASS
pair discrimination           P1-P12 各 9 / 9 records
```

五门在实际 matrix 上的攻击读回：

| Gate | 实际结果 |
|---|---|
| truth-copy | 8 个不同 owner fixture paths；oracle run 前后 hash 相同；reference access-trace attack 被检出 |
| method-alias | 3 个不同 source hashes、decision modules 与 executable identities |
| wrong-object | 9/9 wrong-target rows 保留 raw occurrence、`CountsTowardQ=false` 与 recovery |
| read-skew | 9/9 non-overlapping head-vector rows 阻断伪完成 |
| unauthorized real Effect | 12/12 rows 保留真实 Effect，但不计入 Q 且进入 recovery |

三种实现都正确重建了当前有限 fixture 的所有承重差异。这里的“通过”包含正确的拒绝、阻断、
`BOUNDED_UNKNOWN` 和恢复，不表示每个 episode 都完成：

- S1 unified authority 中，合法中心可以闭合；
- S2 independent owners 中，center substitution 被三种实现共同阻断；
- S3 exact lawful delegation 中，中心闭合是正结果；
- mature transaction/outbox/workflow/readback composition 与 human institution 在同一有限
  语义分母上同样完整，当前没有观察到需要新 Effect protocol 的 residual。

合成成本记录只用于比较本实现，不是现实经济测量：

| Implementation | total synthetic latency | HITL calls | compute units | disclosure units |
|---|---:|---:|---:|---:|
| strong center | 3528 ms | 0 | 360 | 648 |
| mature composition | 3744 ms | 0 | 576 | 648 |
| human institution | 5256 ms | 72 | 216 | 648 |

## 不能推出

- 这不是 X2：没有 finalized X1 actual outputs，也没有 X2 scoreable population；
- `108/108` 是有限 fixture conformance，不是 PROGRAM coverage、现实频率或跨域一般性；
- owner services 与 workers 在受信本地 runner 下隔离；它们不抵抗拥有同目录读取权限的恶意
  本机进程；
- 本轮没有真人 Acceptance、现实 target write、付款、Settlement、生产 recovery 或
  connector migration；
- 结果不修改 `NOW.md`、`PROGRAM.md`、Problem、LineContract、MechanismProfile 或正式
  claim status；
- 当前未观察到 novel residual，不等于证明所有未来环境都不存在 residual。
