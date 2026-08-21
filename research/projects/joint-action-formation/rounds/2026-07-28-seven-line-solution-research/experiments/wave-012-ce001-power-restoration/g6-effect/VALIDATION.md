# Validation record

状态：`LOCAL ONLY`

## 第三轮 response currentness / native closure

第三轮首个实现侧复现为 `0/7`：跨 session Effect、O_Q/O_V Acceptance、O_P
obligation/finality 都能重放闭合；无 native occurrence 的格式正确 Effect payload 可闭合；
recovery/target-state 同源双伪造可在实际 C8 仍为 `POWERED@v1` 时继续；evaluator 不要求
冻结 receipt closure；response envelope 缺 session/nonce/ordinal/native heads。

修复后稳定数字：

```text
preserved prior regression          54/54 PASS
independent third-pass red lights   12/12 PASS
implementation currentness tests   12/12 PASS
full suite                          78/78 PASS
semantic conformance                  6/6 PASS
failure injection                     4/4 PASS
correct resolution                     8/8
G6 line-local closure                  6/8
raw occurrences                          8
wrong-target real Effect                 1
recovery                                 1
duplicate Effect                         0
owner API calls                         63
contract ExactTaskSuccess   NOT_COMPUTED_BY_G6
```

独立 C 的 frozen closure 首次为 `11/12`：fresh closure 自身因 freeze 与 verifier 对 raw
byte fields 的 canonical projection 不一致而失败。统一 canonical receipt projection 后，
保持 C 测试不变为 `12/12`。被 native mismatch 拒绝的 response 仍保留为
`verified=false / consumed=false` 的 raw transport receipt，不会进入 native evidence。

TraceClosure 绑定 plan/result hash、raw request/response bytes、receipt 顺序、五 owner
process、per-owner native ledger head/length。evaluator 显式接收 `trace_closure`；无 closure、
drop、reorder、byte tamper、result hash、actual plan hash 不匹配均 fail closed。OwnerClient
还会在调用时重验当前 `os.getpid()`；两个 detached decoder 均不再是 evidence API。

## 第二轮根红灯修复

第一轮数字以下均保留为历史。当前实现的 truth boundary 已改变：

- 五个 owner 分别运行在独立 `spawn` process，且只收到自己的 state shard；
- method 只消费 canonical transmitted response bytes，`OwnerClient` 不再接受 callable 或
  捕获 world；
- O_Q/O_V 分别产生 unique exact Acceptance act；O_P 独立产生 obligation/finality readback；
- recovery 绑定 damaged occurrence，并要求 versioned target mutation + native readback；
- evaluator 从 SHA-256 冻结的 `grader-input.json` 取 resolution truth，owner 不加载；
- `ExactTaskSuccess` 改为 `g6_line_local_closure`，合同级结果固定为
  `NOT_COMPUTED_BY_G6`，deadline/duration/full safety 均为 `UNKNOWN`。

## 第二轮当前验证

根会话与不知道期待 resolution 的 Agent C 分别复跑。当前结果为：

```text
root red-light attacks       13/13 PASS
full regression              54/54 PASS
preserved first-round tests  41/41 PASS
semantic conformance           6/6 PASS
failure injections             4/4 PASS
correct resolution              8/8
g6 line-local closure           6/8
raw occurrences                   8
wrong-target real effect          1
recovery readback                  1
duplicate Effect                   0
canonical owner API calls         63
contract ExactTaskSuccess         NOT_COMPUTED_BY_G6
```

冻结 grader SHA-256 为
`7b0b6e2f5162b6d0f69e9e689bf6ebedcc7876372edd892aec1630638f9b8860`。

第二轮 C 首跑并非全绿：13 项中 12 项通过，1 项真实失败。两个独立 Acceptance channel
可以在 payload 内声称两个虚构 PID；method 当时只检查 payload PID 不同，没有把它们绑定到
response envelope 的实际 transport PID。测试保持不变，实现增加
`payload.process_id == envelope.process_id` 校验，并只把已验证 transport PID 传给 O_P；
随后定向测试、13 项攻击和 54 项全套均通过。

Agent C 还在同一 Python harness 中验证了 OwnerSession 关闭后的五个 child：
`is_alive=false` 且 exit code 均为 0。系统级 `ps/pgrep` 受 sandbox 限制，故这里只证明本
harness 持有的 child 生命周期闭合，不声称完成全机进程表核验。

## 第一轮红灯历史（保留）

首次运行：

```text
python3 -m unittest discover -s tests -v
Ran 18 tests
FAILED (errors=11)
```

失败不是语义断言被拒绝，而是 raw API receipt 在计算 hash 时没有先把 dataclass response
canonicalize 成 JSON，导致 `AuthorityObservation is not JSON serializable`。这暴露了 trace
边界确实在序列化 owner-native response，而不是预填一份统一 packet。

修复：`model._jsonable()` 先识别 dataclass 并递归转换，再计算 receipt hash。

修复后的同命令：

```text
Ran 19 tests
OK
```

## 敌对复核红灯

Agent C 随后在不知道期待赢家的攻击面补入 11 个 tests；第一次运行是 1 个 control green、
10 个红灯。失败分别暴露：

- O_R/resource-domain occurrence 可被移植成 target-native Effect；
- other-episode attempt、pre-existing state 和 post-effect/wrong-actor Authority 可错误计入；
- 对 C7 的 Authority 仍会跟随到实际 C8 occurrence；
- 零 owner query 可被方法误写成正确 refusal；
- transplanted Adoption 和同一个 owner 的两份 Acceptance 可闭合；
- wrong obligation/scheme 的 provider phases 可被判 FINAL；
- recovery action 的返回值没有 target-native readback 也可继续闭合。

实现逐项收紧后，未修改或弱化攻击断言：

```text
python3 -m unittest discover -s tests -v
Ran 30 tests
OK
```

Agent C 的二轮攻击扩展到 20 项，另发现 3 个真实红灯：

- O_P 返回的 obligation 可以绑定另一 Effect；
- `observed_at` 在 cut 之后的未来 scheme phase 可提前制造 finality；
- 同一 operation 产生两个不同 occurrence ID 时，按 ID 去重会漏掉 duplicate Effect。

同时根复核发现 E3A/E3B 的 public plan 分别只有 1/2 个 attempt，case id 又明示 A/B，违反
“允许交互前同构”。修复后两支给 method 的 plan 是同一个 opaque episode、同样两个
attempt；A 在 exact readback 后不执行 fallback，B 在 wrong-target recovery readback 后才执行
fallback。grader case id 只在 method 返回之后由 runner 追加。

最后一次敌对复核还揭露：字段完全正确的 recovery occurrence 与 recovery-event list 仍可能
在 target state 没改变时伪造闭合。最终实现让 simulator 维护独立 target state；recovery
action、recovery occurrence 和 O_E target-current-state readback 成为三个步骤，只有受损
对象确实回到原状态才允许 fallback。历史 damage/reversal occurrence 不删除。

第一轮最终完整复跑：

```text
python3 -m unittest discover -s tests -v
Ran 41 tests
OK
```

第一轮 `python3 run.py --mode all`：

```text
semantic conformance      6/6
failure injections       4/4
CE-001 correct resolution 8/8
CE-001 exact task success 6/8
raw occurrences          8
wrong-target real effect 1
recovery readback        1
duplicate Effect         0
owner API calls          70
```

第一轮的 `6/8 ExactTaskSuccess` 不等于 G6 失败：E5 是冻结的正确拒绝，不应算 success；E3B 虽先恢复
错对象 damage 再以新 operation 完成 C7，但历史已违反 “不得给其他线路送电”，因此不能用
后续成功把 exact-task 分母改写成成功。

上段数字只保留为第一轮审计历史。第二轮当前数字以本页“第二轮当前验证”和重新运行后的
`artifacts/` 为准；G6 不再计算合同级 `ExactTaskSuccess`。
