# Wave 006-E anchor equivocation

状态：`LOCAL_SYNTHETIC_THREAT_CONDITIONAL_RESULT`

共享任务：`W6-STERILE-ROUTE-SIMULATION-001`  
共享任务 SHA-256：
`0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3`

本实验不改变 shared operation、truth、client-visible receipt、anchor key 或 beneficiary
acceptance。它只改变客户端怎样发现同一个 anchor 用正确 key 向不同 client 签发冲突历史。

## 最承重发现

`SINGLE_PINNED_VIEW` 能验证签名和自己分支的 hash chain，但原则上不能检测同 key 跨视图
equivocation。

反例很直接：anchor 对相同
`(task, sequence=1, previous_head=None)` 签发两个不同 head：

- Client A 只看到合法 branch A；
- Client B 只看到合法 branch B；
- 每个 transcript 都与“anchor 诚实、世界里只有这一条分支”产生的 transcript 完全相同。

因此，任何只使用单一 transcript 的 sound verifier 都没有能够区分两种世界的信息位。更强
算法、更多本地哈希或重放同一签名都不能补出缺失的 cross-view observation。

## 三种策略的实际结果

| 策略 | 分区时检测 | rejoin 后检测 | 接受冲突 pair | 诚实 false reject | 消息 | 证据 | rejoin 恢复 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `SINGLE_PINNED_VIEW` | 否 | 否 | 1 | 0 | 0 | 2 | 不可用，除非加入新 cross-view 输入 |
| `CLIENT_GOSSIP` | 否 | 是 | 1（分区期间） | 0 | 2 | 2 | 2 步：交换、隔离冲突 heads 并 reopen |
| `INDEPENDENT_WITNESS_QUORUM` | 是 | 是 | 0 | 0 | 8 | 4 | 1 步：获取 quorum branch |

Witness 配置为 `n=3, q=2`，因为 `2q > n`，两个 quorum 必须相交。实验中 branch A 先获得
W1+W2；恶意 anchor 再向 W2+W3 请求 branch B，W2 因同 slot 已签另一 head，返回独立签名的
`WITNESS_EQUIVOCATION_PROOF`，branch B 只有 W3，不能达到 quorum。

代价也没有被隐藏：如果只有一个 witness 可达，一个诚实 head 不能获得 quorum，状态保持
`UNKNOWN_DEFERRED`，产生一次 missed valid action。它不是错误地判为恶意，但确实降低可用性。

## 哪个方案胜出

没有全局胜者：

- 威胁模型只有本地完整性、明确不要求检测同 key equivocation：
  `SINGLE_PINNED_VIEW` 是成本最低的正向方案；
- 允许分区期间暂时接受，但要求 client 最终重连后发现冲突：
  `CLIENT_GOSSIP` 用最小新增 cross-view 信息解决；
- 要求 client 分区期间也不能形成两个被接受的 head：
  `INDEPENDENT_WITNESS_QUORUM` 才满足，但承担消息与 witness-partition 可用性成本。

这三者都是成熟技术组合，不需要为了冻结问题创造新协议。没有加入 transparency log，因为当前
材料已经由 gossip 与交叉 quorum 区分了三个目标；增加第四方案不会改变当前承重判断。若后续
目标变为公开可审计、长期多观察者一致性，再单独比较 transparency log。

## 反例与边界

- 同一个 receipt 重放给两个 client 不是 fork，gossip 不误报；
- 两条冲突 branch 都由正确 anchor key 签名，本实验不是伪签攻击；
- gossip 只能检测并隔离，不能凭空判断哪个 branch 的业务 truth 正确；
- quorum 证明“没有两个有效交叉 quorum”，不证明 witness 永远诚实；
- 2-of-3 结论依赖至少一个交叉 witness 不双签；
- 本地对象隔离与 synthetic Ed25519 keys 不等于生产密钥托管、网络或 Byzantine 安全。

结果只支持本地合成 threat comparison，不能推出现实攻击频率、生产可靠性或主体接受。

## 运行

```bash
PYTHONPYCACHEPREFIX=/tmp/wave006-anchor-pycache \
  python3 -m unittest discover -s tests -v

python3 evaluator.py --output results.json
```

