# CE-001 G1 独立敌对审查

角色：内部 Agent C  
状态：`ATTACK RUN / FIVE REDS REPAIRED AND RECHECKED / NO METHOD WINNER ASSUMED`

## 审查边界

本审查在 B 的实现可见前先冻结攻击计划，不预设强中心、成熟组合、人工、模型或新机制应当
胜出。攻击对象是 G1 module 是否允许通过 hidden truth、最终方案、预枚举 path、目标偷换、
source/Authority alias 或 invalidity bypass 获得伪成功。

Agent C 只新增本文件与 `tests/test_adversarial.py`，没有修改 `g1prov/` 实现。

## 首轮运行

命令：

```bash
python3 -m unittest discover -s tests -v
```

首轮实现稳定后结果：

```text
Ran 25 tests
OK (expected failures=5)
```

这里的退出码 0 只表示 20 个已关闭攻击正常通过、5 个已知红灯被准确重现；不能把
`expected failure` 描述为模块通过。

### 已关闭的攻击

- method 源码和递归 interface key scan 未发现 `L_benchmark`、`D_actual`、
  `correct_path`、`t0_paths`、`final_proposal` 或 private expected label；
- 替换为此前方法从未见过、但 owner-backed 且进入冻结 population 的动态候选后，method
  能通过 `candidate/resource/partner` 三类 query 形成合格 handoff，说明不是 hard-code
  candidate ID；
- 注入排序更靠前的 wrong-object decoy 时，decoy 不会获得 false positive；
- valid-key/wrong-Authority 与 same-source alias 均在 positive interpretation 前 hard fail；
- 只有正确 final proposal 字符串、没有合法 evidence 时不获资格；
- `FULL_ACTUAL_TRACE` 的 t1 partner receipt 被复制到 `T0_REPLAY` 后 hard fail；
- E2 operator 正常、remove、reverse 三支分别得到 qualified、Unknown、revoked invalid，
  因果变化来自 owner-backed evidence，不来自 intervention label；
- E3A/E3B 使用同一 `candidate_id` 时，summary 已按
  `(episode_id, candidate_id)` 计数，不再跨 episode 串分。

### 首轮红灯

#### R1：benchmark membership 被误当 validity

合法、current、owner-backed 的新候选若不在当前冻结 `L_benchmark`，gate 返回
`NON_BENCHMARK_CANDIDATE / INVALID`。

正确边界应是：

- 当前 `L_benchmark`、`D_actual` 与 population hash 不变；
- 当前 recall 不追溯改写；
- 新 path 保存为 `NOVEL_CANDIDATE_FOR_NEXT_VERSION`，等待独立资格化。

否则开放 discovery 被 evaluator 重新压成“只能发现预先枚举候选”。

#### R2：query budget 可在 gate 前越过

method 先用三次合法 query 形成 proposal，再发第四次超 `max_queries` query。session 会
返回空并写 note，但 evaluator 仍把已有 proposal 判为 `QUALIFIED_CANDIDATE`。

这表明 action envelope 目前只是 service 层局部阻断，不是 invalidity-first gate。超预算的
trace 仍可保留早先 positive credit，违反“所有读取/询问必须在共同 envelope 内”的硬门。

#### R3：冻结 Q 在 interface 被截短

interface 的 `intent_text` 保留了 T0+90、C7、45 分钟、3kW、噪声和安全条件，但遗漏 CE-001
合同冻结 Q 的：

- requester 与 venue 对 exact `Q_version` 和实际 Effect 作出 Acceptance；
- 之后才进入相应 Settlement。

G1 不应实现 Acceptance/Settlement，但必须保留完整任务输入；否则后续组合 runner 收到的是
缩小后的 Q。

#### R4：prelude lineage 只核对回显，不重算 preimage

修改 `world.prelude`，同时保留旧 interface receipt hash 后，method 与 evaluator 仍可通过。
当前 gate 只比较 trace 回显 hash 与 interface hash，没有重算
`digest(world.prelude)`。因此“linked by hash”尚不能发现 prelude preimage 被替换。

#### R5：query scope 未下推到 record 过滤

session 会验证 query predicates 与 interface 完全相等，但随后按 `kind` 返回全部 records。
在 C7 query 下插入 payload 绑定 C8 的 owner record，会先发生披露，再由后置 evidence gate
拒绝。

这避免了 false success，却仍产生：

- unrelated owner data disclosure；
- 多余 disclosure cost；
- 排序靠前 decoy crowd out 合法候选的 liveness loss。

query predicate 必须在 owner/service 发出 evidence 前约束 record。

## 当前可支持与不能支持

首轮可以支持：

- method 没有读取显式预枚举正确 path 或 final proposal；
- 指定的 Authority/source alias、t0/final-proposal、operator remove/reverse 与 decoy
  false-positive 攻击已具备可运行判别；
- 当前输出保持 `CANDIDATE_NOT_COMMITMENT`，没有实现 G2–G7。

首轮不能支持：

- invalidity-first gate 已覆盖完整 action envelope；
- 开放 discovery 与冻结 benchmark 已无冲突；
- interface 无损保留 CE-001 exact Q；
- prelude hash 已绑定实际 preimage；
- discovery service 在披露前完整执行 query scope。

这些是 local synthetic harness 的具体红灯，不证明真实产品、主体 Authority、真实供电、
Acceptance、Settlement 或 CE-001 完整解决。

## 修复后复查

B 没有删除或改弱上述攻击，而是逐项修复实现：

- benchmark membership 与 evidence validity 分离；新 owner-backed path 返回
  `NOVEL_CANDIDATE_FOR_NEXT_VERSION`，当前 `L_benchmark/D_actual` 不变；
- invalidity gate 从 raw trace 复核 query count、kind 和 exact predicates，超 envelope 返回
  `ACTION_ENVELOPE_BREACH`；
- interface 恢复 requester 与 Venue V 的 exact-Q/Effect Acceptance 以及之后 Settlement
  条款，但 G1 handoff 仍显式不宣称这些后线结果；
- gate 同时重算 `digest(world.prelude)` 并核对 trace/interface receipt；
- owner service 在签发 evidence 前按 `q_version/object_id` 过滤 record，C8 decoy 不再进入
  C7 trace，也不再 crowd out 合法候选；
- summary 继续按 `(episode_id, candidate_id)` 计数。

Agent C 移除五个 `expectedFailure` 标记，并在相同命令下复跑：

```text
Ran 26 tests
OK
```

这关闭的是本文件列出的五条 local synthetic attack。它没有把模块晋升为恶意同进程隔离、
真实 owner service、真实供电、完整七线组合或现实 CE-001 解。

最终入口复核：

```text
baseline cases = 8
|L_benchmark| = 9
|D_actual| = 6
D_actual discovered = 6/6
L_benchmark discovered = 6/9
baseline invalid = 0
failure injections = 5/5 hard INVALID
operator variants = QUALIFIED / UNKNOWN(remove) / INVALID(reverse)
handoff output_hash present = 8/8
handoff raw_trace_sha256 present = 8/8
```

`python3 runner.py --output <temp>` 成功生成
`ce001-g1-provenance-module-output-v1`。默认 `compileall` 首次尝试写 macOS 用户 cache 时被
sandbox 拒绝；将 `PYTHONPYCACHEPREFIX` 指向独立 `/tmp` 目录后同一源码编译通过。这个红灯
属于当前执行环境的 cache 写权限，不是 G1 语义或测试失败。

## 第二轮根红灯与修复

上述“session interface”结论后来被根会话推翻：method 与 `DiscoverySession` 同进程，
恶意 worker 可经 `session._world`、bound `__self__`、传递 import 或 frame/reflection
取得 `expected/L_benchmark/D_actual`。原 `raw_trace_sha256` 也不是实际 IPC bytes 证据。

第二轮默认路径改为三个不同 PID：

```text
standalone worker ⇄ exact JSONL byte relay controller ⇄ owner service/state
```

- worker 是复制到临时 cwd 的单文件 stdlib 程序，以 `python -I -S` 启动；
- controller/evaluator private bytes 在 worker 启动前实际包含
  `expected/L/D/oracle roots/private canary`；
- worker 只收到 interface 与 owner service raw responses；
- owner service 从自己的 state 生成 event hash、service PID、state version 与 exact
  request hash；
- controller 对 query/response 都逐字节转发，保存每帧 length/hash/base64，并与 worker
  自报 stdin frame receipt 对账；
- manifest 绑定 Python source tree、public/private input receipts、boundary trace、
  evaluator raw trace 与 result bytes；
- handoff 明确不宣称
  `RELATION/COMMITMENT/AUTHORITY/EFFECT/ACCEPTANCE/SETTLEMENT`。

受控 reflection/closure/frame/gc/import/env/argv 与临时 cwd path scan 没有命中 private
canary 或私有字段；但 absolute-path probe 保留为
`RED_NOT_ISOLATED`。同一 OS 用户若预先知道仓库绝对路径，仍能确认 private fixture 源码
可读。因此当前只建立默认 worker 的进程/API 非传输边界，不建立 same-user hostile OS
机密性，也不建立 evaluator/controller 进程分离。

## 第三轮 process/source identity 加固

根审计随后指出第二轮仍主要相信 child 自报 PID 与 origin。第三轮不把 owner process
误写成独立 owner：其 source 固定为
`CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE`，records/operators 仍由 controller 从同一
synthetic `World` 注入，真实 owner truth/origin 均为 `NOT_ESTABLISHED`。

controller 现在为 owner source/state/process 与 worker process 分配每次启动的 instance
ID，并将 READY、每条 owner event、worker query/result 的声明同时绑定到：

- controller 保存的 launch instance；
- controller 观察到的对应 `Popen.pid`；
- owner response state version 与 event state version；
- 实际 raw request hash。

四个真实 subprocess 注入均在转发/评分前 fail closed，并保留 actual `Popen.pid`、分配的
instance、拒绝码和 raw frames：

```text
OWNER_PID_MISMATCH              -> OWNER_READY_PID_MISMATCH
WORKER_PID_MISMATCH             -> WORKER_READY_PID_MISMATCH
ORIGIN_SELF_REPORT_INCONSISTENCY -> OWNER_EVENT_ORIGIN_PID_MISMATCH
WRONG_SOURCE_INSTANCE           -> OWNER_EVENT_SOURCE_INSTANCE_MISMATCH
```

新的 `g1_line_envelope` 是 G1-prefixed line-local 输出；递归 validator 拒绝合同成功和后线
claim key/value，且不复制旧 handoff 的 explicit non-claims 清单。旧 handoff 只为保留既有
30 项风险回归面。以上仍不对抗 same-UID hostile OS；absolute-path probe 继续是
`RED_NOT_ISOLATED`。

## 第三轮独立 C 来源错配攻击

`/root/g1_fix2_c_blind_attack` 未读 tests、README、本文件或任何 final，只读必要运行
源码并用临时内存探针攻击实际 subprocess。它复现：

- owner/worker READY 伪报 `424242` 在任何正向评价前 fail closed；
- event origin 与 wrong source instance 的无效 owner raw response 均未进入 worker；
- worker query/result 另行伪报 PID 或 process instance 同样在 owner forward/评价前拒绝；
- E1 正例三进程不同，3 次双向 query/response 均保持 exact raw bytes；
- 8 个 baseline 的 canary/forbidden marker 均未进入 worker，same UID probe 仍为
  `RED_NOT_ISOLATED`。

C 同时发现一个新红灯：首版 line envelope 把内部 `authority_id` 改名为
`g1_claim_root_id`，词法 validator 因此给出假绿；字符串值检查也只拒绝精确等于禁词的值。
根会话已删除该导出字段，把所有字符串值改为 token 级拒绝，并补入
`RELATION_ESTABLISHED` 反例。E3 的 exact episode ID 含后线词，因此 envelope 只携带其
可复算 SHA-256 引用，exact ID 留在 envelope 外的 forensic result。原五个语义 injection
名称也不再进入 worker input，避免恶意 worker 按已知攻击类型特判。最终绿灯只支持 G1
line-local candidate provenance，不支持任何后线状态。
