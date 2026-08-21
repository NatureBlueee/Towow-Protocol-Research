# Wave 007-C2：独立攻击后重建的 access-metered reliance harness

状态：`LOCAL_REPAIR_REGRESSION_COMPLETE_NOT_INDEPENDENTLY_AUDITED`

## 为什么必须新建 C2

独立 audit 推翻了原
`wave-007-c-access-metered-reliance/` 的承重主张。原 C 的 10/10 本地测试只能保留为历史，
不能继续作为有效性证据：

1. 把 step 7 的合法 `ACTIVE authority_status` 复制到 step 8 已 revoked world 后，
   Declaration、Latest Probe、Receipt Window 都错误 `RELY`。旧 receipt 只有 freshness，
   没有当前 authority head / epoch / contract binding；
2. candidate 调用 `declaration(api)` 后执行 `api._log.clear()`，决策不变，但 evaluator 得到
   `api_operations=0 / cost=0`。所谓 raw log 仍在 candidate 同一进程；
3. candidate 改写返回值中的 `implementation_id`，evaluator 按自报身份分组。

C2 不修改或覆盖原 C，而是新建接口和 runner。以下结果是同一研究者的修复回归，**不是独立
复核结果**。

## 三项结构性修复

### 1. Authority current-head binding

Parent broker 持有不可由 candidate 覆盖的 trusted request。每份 authority status 必须由
Authority Registry 签名并精确绑定：

- `authority_head`
- `authority_epoch`
- `authority_contract_version`
- subject、status 和 key

所有 binding、freshness 和 authority 校验都重新读取 parent 中的 trusted request；candidate
回传的 context 还必须与 trusted bytes 完全相同。仅仅“签名有效且 age <= 1”不再足够。

直接 mutation 将 `w7c-50de71` 的合法 ACTIVE status 原样复制到 revoked
`w7c-a76e20`：

- 四个 strategy 全部拒绝依赖并进入 `UNKNOWN`；
- operation log 显示 `VALIDATE_AUTHORITY_HEAD=false`；
- 即使 malicious candidate 把自己持有的 context 改成 replayed head，也不能覆盖 parent
  trusted context。

### 2. Parent-owned broker ledger

Candidate 在单独 Python subprocess 中运行，只持有 stdin/stdout JSON/RPC proxy。数据库、
private signer、hidden truth、broker object 和 raw operation log 都留在 parent。

Parent broker：

- 只允许固定 evidence API 方法；
- 独立记录 read、verify、binding、freshness、authority、retry、bytes、latency 和 disclosure；
- candidate 结束后才向 evaluator 提交 log snapshot；
- 拒绝任何 `clear_operation_log` 控制 RPC。

精确 malicious strategy 先完成 Declaration，再尝试 `api._log.clear()` 和
`clear_operation_log` RPC。结果仍为 `RELY`，但 parent 保留 10 次实际 operation，清空请求
被记录为一次 `DENIED_RPC`，成本为 `1.554410`。

Candidate 运行期还安装 Python audit hook，阻止新的文件读取、import、process 和 network
扩张；本地 private-truth 读取 mutation 被拒绝。这个 guard 是本合成 runner 的进程内防线，
不是对任意 native code 或 hostile OS principal 的普遍安全保证。

### 3. Parent registry identity

Parent registry 决定：

- evaluator owner identity；
- worker 实际执行函数；
- 仅用于显示的 label。

Candidate 返回的 `implementation_id` 只作为不受信自报字段保存，绝不参与分组、成本和计分。
直接 mutation 让 Declaration 自报 `IMPL_SLA_RECOVERY`，最终仍由 evaluator 归入
`IMPL_DECLARATION`。

## 重新运行的完整回归

C2 没有继承原 10/10 的通过状态，而是重新运行 15 项测试和 mutation：

- 三个独立 audit 原始反例；
- opaque rename、label rename、truth-label flip；
- self-report injection；
- primary evidence、authority status、probe freshness 和 recovery receipt deletion；
- unauthorized signature、command/purpose/key/environment bytes binding；
- duplicate receipt；
- repeated read / verify / freshness billing；
- raw operation-log delete/add/reorder；
- `UNKNOWN / REFUSE / ABSENT` preservation；
- candidate private-state read。

## 当前合成结果

| Parent registry owner | TP | FP | FN | Parent-ledger cost |
|---|---:|---:|---:|---:|
| Declaration | 9 | 1 | 0 | 18.442435 |
| Latest probe | 8 | 0 | 1 | 20.827075 |
| Receipt window | 8 | 1 | 1 | 45.136551 |
| SLA + recovery | 7 | 0 | 2 | 36.579428 |

这些数值与原 C 略有变化，因为 current-head payload 与 broker 校验操作也被实际按 bytes/latency
计费。

当前合成 Pareto frontier 仍是 Declaration 与 Latest Probe。基础 48 点扫描中二者分别在
36 / 12 点唯一胜出；存在 1 个 margin 不超过 1 的近边界点。统一 scenario frequency 下的
27 点扫描为 21 / 6；把 current failure 提高到 8 倍后变成 10 / 17。

这不是普遍 winner。Receipt Window 和 SLA 在当前观察维度与频率下被支配，只是当前有界
fixture 的结果，不否定它们在其他 failure distribution、恢复要求或现实制度中的价值。

## 运行

```bash
PYTHONPYCACHEPREFIX=/tmp/w7c2-pycache \
  python3 private/build_public_fixture.py

PYTHONPYCACHEPREFIX=/tmp/w7c2-pycache \
  python3 evaluator.py --output results/evaluation.json

PYTHONPYCACHEPREFIX=/tmp/w7c2-pycache \
  python3 -W error::ResourceWarning -m unittest discover -s tests -v
```

## 当前证据边界

C2 证明的是：这三个已知 attack 在当前 Python subprocess + parent broker 合成环境中不再复现，
且原来的 cost/sensitivity 分析能够在新边界上重建。它不能证明：

- 真实 authority 服务一定提供可信 current head；
- hostile native process 无法突破 Python audit hook；
- 现实频率、业务损失或 SLA 价值；
- 新实现已经通过独立 mutation；
- 整个通爻问题或其他研究线因此成立。

下一步仍必须由独立审查者直接替换 fixture、worker 和 RPC 序列；若 C2 再被推翻，保留 C2
并建立下一版，不能改写本轮结果。
