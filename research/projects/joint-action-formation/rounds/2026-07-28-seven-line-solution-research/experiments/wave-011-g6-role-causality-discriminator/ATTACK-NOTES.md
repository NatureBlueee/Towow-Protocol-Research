# G6 Wave 011 adversarial gate notes

状态：`LOCAL SYNTHETIC INVALIDATION HARNESS / NO FORMAL PROMOTION`

## 结论

本目录在 coverage 前设置五道硬门。硬门不是检查结果中是否出现五个漂亮字段，而是运行一个
已知恶意 specimen，并证明 checker 能拒绝它，同时接受语义相同的良性 control。任一门不具备
这种区分力，整轮为 `INVALID`，不得继续报告 coverage。

当前攻击代码只证明本地 checker 能区分五种预注册恶意 double。它不证明 owner API 在真实
组织中准确、传感器可靠、三种方法社会技术意义独立、真人已验收或现实 Effect 已发生。

## 历史失效审计

### 1. Truth direct-copy

Wave 010 的 owner readback 由同一个 `world["truth"]["layers"]` 直接复制；dependency
response 同样复制 private truth。因此原 `7/7` 只证明在 perfect、及时、免费 oracle 已经把
答案送给方法时，方法能路由答案。

Wave 011 的 gate 不比较 response 是否“看起来像 truth”，而审计实际 source access：

- 恶意 `TruthCopyOwnerService` 调用 grader-only `PrivateOracle.read()`；
- 良性 `NativeOwnerService` 只调用 owner-native store；
- oracle 与 owner store 故意给出不同 head；
- checker 同时检查 access trace 与 `source_kind`。

主 runner 集成时必须提供 owner source provenance。只交一份签名 response、source 名称或
相同 JSON 值不足以证明非复制。

### 2. Method alias

Wave 010 的 mature composition 与 strong center 共享同一 `method_decision()`，profile
几乎只有名字不同。输出恒等只能支持代码 alias，不能支持架构因果等价。

本 gate 至少要求三个方法的：

- `executable_sha256`；
- `decision_root_sha256`；
- implementation owner

被独立声明，并拒绝 executable 或 decision root digest 碰撞。独立方法可以在观察上等价，
且任何成熟组合、人类制度或合法强中心都允许胜出；但不能从同一函数的重命名宣称独立比较。

这个门仍不能证明“不同源码绝无共同核心”。若三个 wrapper 使用不同 bytes 却 import 同一
隐藏 decision engine，需要在主 runner 进一步记录 dependency/call-graph digest 和进程
identity。

### 3. Wrong object

错误对象具有两个同时成立的结果：

```text
对当前 episode：CountsTowardQ = false
对现实世界：raw occurrence = true，actual target 受损，recovery relevant = true
```

旧 evaluator 只检查正确 episode 没有被晋升，因此会把 CNC-71 的真实损害吞进 CNC-17 的
`QualifiedEffect=false`。本 gate 要求保留 actual target、affected targets 和 recovery；
只输出“不计入成功”不算检出攻击。

### 4. Read skew

每个 owner head 都真实、签名正确，也可能组合成从未同时存在的 `Done`。典型攻击是：

```text
Acceptance 在 event 8--10 有效
Settlement 从 event 12 开始有效
controller 读旧 Acceptance + 新 Settlement
```

本 gate 要求 head validity intervals 存在真实交集，且显式 cut id 不冲突。恶意 double
令 naive aggregator 输出 `Done=true`；checker 必须拒绝。签名数量、head 分别为真或最新
读取时间都不能替代一致 cut。

### 5. Unauthorized real Effect

G5 deny 或 Authority 失效不保证现实世界没有变化。旧 work order replay 仍可能真实改变
CNC 参数。正确的联合输出是：

```text
raw_occurred = true
Authority = UNAUTHORIZED
episode_bound = true
CountsTowardQ = false
recovery_relevant = true
```

恶意 qualification collapser 把它缩成“Effect 不成立”。本 gate 使用独立 occurrence
specimen 检查 raw occurrence、Authority、CountsTowardQ 和 recovery 四维是否同时保留。

## 接口

### 自包含恶意 doubles

```bash
python3 gate_runner.py
```

输出：

```text
gate_results.<gate>.attack_present
gate_results.<gate>.attack_detected
gate_results.<gate>.benign_control_accepted
gate_results.<gate>.passed
overall_valid
round_status
coverage_allowed
```

测试 detector 缺失时：

```bash
python3 gate_runner.py --disable-gate read_skew
```

应非零退出，且 `round_status=INVALID`、`coverage_allowed=false`。

### 主 runner 集成

`evaluate_main_run(payload)` 不读 grader expected table；它消费以下运行证据：

- `provenance.owner_api_sources`：owner store/sensor/institutional act 的 source access；
- `methods`：独立 executable 与 decision-root identity；
- `occurrence_assessments`：raw occurrence、target、Authority、episode binding、
  `CountsTowardQ`、recovery；
- `done_evaluations`：实际参与 Done 求值的 head validity interval/cut 和派生结果；
- `attack_manifest` / `attack_detections`：truth-copy 与 alias 恶意 specimen 确实运行并被
  runner 拒绝的 receipt。

P1/P3/P11 标签本身不是 truth。集成 gate 按 occurrence 属性和 head 时间区间识别攻击：
wrong target、unauthorized raw Effect、无共同 cut 的 head。若攻击行被删掉，gate 是
`attack_present=false`，整轮 fail closed。

## 运行与局限

定向测试覆盖：

- 五个 reference attacks 全部被检出，良性 control 不被拒绝；
- 逐一关闭任一 detector，整轮都变为 `INVALID`；
- main-run adapter 在完整结构证据下通过；
- 缺攻击证据或空 payload 时 fail closed。
- concrete `runner.run_matrix()` 的 108 条 pair/stratum/implementation records 可由
  `evaluate_main_run()` 直接审计；五类定向 mutation 分别使对应 gate 与整轮失效。

2026-07-29 对 B runner smoke artifact 的实际 gate readback：

| gate | attack rows / evidence | 结果 |
|---|---:|---|
| truth-copy | 8 个不同 owner-native fixture paths；oracle hash 运行前后相同；reference direct-copy 被检出 | PASS |
| method alias | 3 个不同 executable identity/source hash/decision module；reference rename alias 被检出 | PASS |
| wrong object | 9/9 wrong-target transition 保留 raw occurrence、排除 counts、进入 recovery | PASS |
| read skew | 9/9 无共同有效区间的 head vector 阻断 counts/continue；189/189 consistent controls 保留 | PASS |
| unauthorized real Effect | 12/12 未授权真实 transition 保留 raw occurrence、排除 counts、进入 recovery | PASS |

这表示 `GATES_PASS / coverage_allowed=true`，不是 coverage 本身。当前测试总数为 10：
全部通过；其中 concrete matrix test 还逐一篡改 owner source path、worker identity、
wrong-object recovery、read-skew control action 与 unauthorized raw occurrence，并确认每次
均使整轮 `INVALID`。

证据边界：

- 本地 Python 对象和 access trace 依赖受信 runner；不是抵抗同目录恶意进程的密码学隔离；
- digest 独立只检测直接 alias 和申报碰撞，不证明算法、作者或训练上下文独立；
- owner-native store 仍可能错误、陈旧或 fork；truth-copy gate 只关闭 grader direct-copy；
- temporal interval gate 假定 owner 的 event index/validity interval 已正确形成；
- 本 harness 没有现实 Effect、付款、chargeback、真人 Acceptance 或生产写入；
- 五门通过只允许 runner 继续评分，不等于 12 pairs、成熟组合、强中心或人类制度已经通过。
