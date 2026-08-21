# Wave 025 prefix qualification contract

日期：2026-08-01  
状态：`V1.3 FROZEN AFTER REAL-SMOKE AND FIVE-ATTACK CLASS-WISE POWER CORRECTION / NO ARM COMPARISON`

## 1. 三个挑战臂

本合同比较的是实验基础设施，不是解题 treatment：

| Challenge | 目的 | 预期 |
|---|---|---|
| `D0-HOST-LEAK` | 弱 launcher：predecessor 把 current role 留在同 UID/shared-state/cwd/process surface | contamination detector 必须检出 |
| `D1-OCI-CANARY` | 与正式 OCI cell 同权限，但显式加入 role-correlated canary | leak detector 必须检出 |
| `T-OCI-ISOLATED` | role 仅在 host-private assignment 中；candidate 只见固定 public bytes | fresh holdout 不得超阈值 |

`D0/D1` 通过只证明 detector 对登记泄漏有敏感性，不证明 `T` 无其他未知泄漏。`T` 通过也只
支持 prefix 作用域。

`D0` 不要求把 collector 安装到 macOS `/challenge`。第一实现可以在受控 weak OCI launcher 中
额外挂入同 UID 可读的 shared residue 作为 cwd，或开放登记的 sibling process surface；关键是
residue 由 sacrificial predecessor 在 current slot 前写入、包含 current role，且 T 中相同通道
不存在。`D1` 则在与 T 相同的 isolation profile 内植入 current-run canary。两者分别检验跨 run
污染与当前 run 泄漏，不能互相替代。

## 2. 冻结 candidate 与 public packet

candidate 是 `attackers/leak-only-collector/collector.js`。它不调用 lawful truth API，只收集
自身实际可见的 argv/env/cwd、有限目录树、hostname、PID/namespace、uid/gid、计时、input
bytes、固定 error probes 和 canary surface，输出 canonical JSON feature receipt。

public packet 只允许：

```json
{"schema":"WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}
```

role、expected、order、seed、case、private hash 或任何未知字段必须 fail closed。正式 `T` 中：

- mount target 固定为 `/challenge`；
- 目录项、文件 bytes、metadata 等价；
- argv、env、cwd、user、hostname shape 和 resource envelope 不由 role 派生；
- candidate 没有 Docker socket、host path、其他 run root、网络或 evaluator material。

## 3. OCI isolation profile

第一实现绑定本机已存在的 `node:20-slim` manifest digest，不使用 mutable tag 作为证据身份。
每个 slot 使用 fresh container，并至少启用：

```text
network=none
read-only root filesystem
non-root uid/gid 65534:65534
cap-drop=ALL
no-new-privileges=true
private PID/IPC/UTS/mount/network namespace
pids/memory/cpu limits
fixed read-only /challenge bind mount
no host Docker socket or unrelated volume
stdout + exclusive `/out` tmpfs result channels
```

host receipt 必须保存实际 image digest、container config、mounts、user、capabilities、security
options、network mode、PID namespace、start/exit 与命令；container 自报不构成该证据。host 必须
逐字比较 collector 的 stdout 副本与 `/out/leak-features.json`；`/out` 只能是本 slot 的 tmpfs，
batch 证据只保留 host 读取后冻结的副本及哈希，不把可写 host evidence 目录挂入 candidate。

2026-08-01 的 pre-formal real-smoke 证明 Docker Desktop 的 archive/`docker cp` 路径在 container
仍 running 时也看不到 `/out` tmpfs。它不能作为正式取证通道；该负结果保留在 `SMOKE-LEDGER.md`。
V1.1 因而冻结一个 observation-cut-aware supervisor/extraction protocol；V1.2/V1.3 进一步修正
class-wise CI 的单攻击与五攻击联合功效所需人口：

1. 同一 role-free PID 1 script 启动 collector，把 collector stdout/stderr 分别重定向到
   `/out/collector-stdout` 与 `/out/collector-stderr`；collector 自己仍写
   `/out/leak-features.json`。
2. collector 退出后，supervisor 才写 `/out/collector-ready` 与原 exit code，并向 daemon log
   发出精确、role-free 的 ready frame；随后只等待 TERM。ready 前 host 只可读取 daemon logs 与
   inspect，不得在 container 内启动任何 exec process。
3. host 验证 ready frame 和 container 仍 running 后，才可按冻结顺序执行五个精确命令：
   `docker exec --user 65534:65534 <exact-name> /bin/cat <exact-/out-path>`，分别读取 ready、exit code、
   collector stdout、collector stderr 与 leak-features。不得用 shell、glob、可变 path、额外 env、
   写命令或 privileged exec；每次 stdout/stderr/exit code 与先后顺序都进入 host command receipts。
4. host 必须在 TERM 后读取该 exact container 生命周期的 daemon events，核对只有上述五组登记的
   `exec_create/exec_start/exec_die`，并把原始 JSONL 纳入 slot receipt。缺事件、额外 ExecID、命令/
   user/path 不一致或时序落在 ready 前均 fail closed。event audit 用于发现普通 pipeline 漂移，仍
   依赖受信任 daemon，不能证明 daemon 没有隐瞒自己的行为。
5. 这些 `cat` 是 collector 已退出之后新增的只读进程，不属于 candidate observation prefix；它们
   仍是受信任 host/daemon extraction TCB，不能被写成抵抗恶意 daemon、host admin 或同权限内核的
   无泄漏证明。若 post-cut 顺序无法重建，slot fail closed。
6. 读取后 host 只向 PID 1 发 TERM；supervisor 必须以 collector 原 exit code 退出。缺 ready、任一
   exec 非零/有 stderr、stdout 与 out 不相等、exit-code 不一致、无法正常终止或 post inspect 不匹配，
   均使 slot 失败。

supervisor script hash、exact ready frame、extraction command template/process surface 必须进入
precommit 与 actual evidence。该修订发生在任何 formal batch 之前；旧 smoke 的 precommit 不因
合同修订被改写，也不得并入 V1.1 evidence。

## 4. 随机平面与 pre-run commitment

至少使用三个不共享 state/counter 的 domain：

```text
PRIVATE_ASSIGNMENT_ORDER
PUBLIC_ID
MEASUREMENT_PADDING
```

assignment 在每个 block 中严格平衡后 Fisher–Yates。private seed 与 commit nonce 由 OS CSPRNG
产生；pre-run root 只公开带不可见 nonce 的 commitment 和算法/version/code hash，不公开 seed、
nonce、order 或 mapping。batch freeze 后 reveal，独立 evaluator 重建全部 slot。

本地同目录 self-hash 不算 external root。正式 evidence run 前，precommit hash 必须写入 candidate
无权改写的任务对话记录或另一权限域中的 append-only root；缺失则最高 `NOT_QUALIFIED`。

## 5. 样本、训练与 fresh holdout

正式二元 `T` challenge 冻结：

- training/calibration：400 episodes，S/R 各 200；
- fresh holdout：2400 episodes，S/R 各 1200；
- assignment/order 按 140 个 block × 每 block 20 episodes 平衡随机；calibration 20 blocks，
  holdout 120 blocks；
- calibration 和 holdout 使用不同 domain-derived assignment streams；
- D1 默认 200 episodes（100 calibration + 100 fresh holdout，两个 split 内 S/R 平衡）；
- D0 默认 200 episodes（100 calibration + 100 fresh holdout，两个 split 内 S/R 平衡）；
- 任一业务失败不重跑；只有预注册的 prelaunch infrastructure failure 可在同 slot 恢复。

不得先跑少量数据观察后再放宽 N、阈值、feature 或 classifier。开发 smoke 与正式 batch 使用
不同 batch id，开发结果不能回填正式 holdout。

## 6. 预注册攻击与 decision rule

至少冻结四类分类器：

1. deterministic exact/categorical rule scan；
2. regularized linear/logistic model；
3. bounded decision stumps/tree；
4. k-nearest-neighbour on frozen normalized feature encoding。

所有 preprocessing、feature allowlist、hyperparameters 与 tie-breaking 在 holdout 前冻结。decision：

- `D0` contamination 与 `D1` current-run canary 的每个登记 family，holdout balanced accuracy
  下界必须 ≥0.90；否则
  `DETECTOR_INADEQUATE`，`T` 不得判通过；
- `T` 任一 deterministic rule 在 fresh holdout 可稳定恢复 role，立即
  `BLIND_QUALIFICATION_FAILED`；
- `T` 任一预注册 classifier 的 balanced accuracy one-sided 95% 上界 >0.55，失败；
- 另做 label permutation、role/order permutation 与 Holm 校正；普通 `p>0.05` 不是等价证据；
- 缺样本、缺 raw feature、容器配置漂移、无法重建 assignment 或 classifier 异常均为
  `NOT_QUALIFIED`，不得写成 chance。

## 7. evaluator 隔离

独立 evaluator：

- 不 import runner 或 collector；
- 在 batch evidence freeze 后才读取 reveal；
- 从 raw slot receipts 重算 public bytes、assignment、container config、feature matrix 与统计量；
- 交换 role label、slot order、path 和 opaque ID 后，资格判断只按冻结语义变化；
- 不向 candidate/runner返回逐 slot 分数、错误距离或剩余 holdout；
- 输出 claim-by-claim 状态，不产生 A1–A5 score、coverage、Pareto 或 winner。

## 8. 第一批不能宣称的内容

即使全部通过，仍保持：

```text
DYNAMIC_LAWFUL_DIVERGENCE = NOT_TESTED
CROSS_RUN_PROVIDER_OR_HUMAN_MEMORY = NOT_TESTED
EVALUATOR_TRUTH_VALIDITY = NOT_TESTED
A1_A5_NATIVE_TREATMENT_QUALIFICATION = NOT_RUN
ACTUAL_COMPARATIVE_RUNS = 0
WINNER = NONE
```

下一层必须把 fixed broker、earliest divergence、cache crossover、evaluator permutation、真实 A3
provider 与 A5 human session 分别加入资格，而不是从本 prefix batch 自动继承。
