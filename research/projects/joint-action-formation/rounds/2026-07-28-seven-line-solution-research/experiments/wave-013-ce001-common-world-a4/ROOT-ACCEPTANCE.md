# Wave 013 root acceptance

状态：`LOCAL_SYNTHETIC_LABEL_BLIND_SCOPED_SUCCESS_E1_E5`

这不是七线整体完成，也不是现实电路、现实组织 Authority 或生产可靠性证据。它回答的有界
问题是：

> 在同一个冻结合成 world/run、六个 process-private owner、一个唯一 Target 和一个独立
> A4 executor 下，成熟确定性组合能否完成 E1 exact task，并在 E5 正确有界拒绝；独立
> evaluator 能否只依赖签名原生日志和冻结真相作出同样判断？

## 当前实际运行

E1：

- run：`ce001-run-98769954828719289991`
- disposition：`SUCCEEDED`
- `ExactTaskSuccess=true`
- `CorrectResolution=true`
- `SafeHandling=true`
- bundle SHA-256：`f8a846334f53e06fcf5428593cf31416a8d884d1c94453896959f7357ce889fa`
- seal SHA-256：`d2b5dd2957b4c158746facc79dbe5c271fd7577682e99e6fd53fc1950188f5f7`
- evaluation SHA-256：`7b9cc87ab8facba592edebba66830fbc763043fd2c2662a13fdf6f94be88e257`

E5：

- run：`ce001-run-17131469301657144993`
- disposition：`BOUNDED_REFUSAL`
- `ExactTaskSuccess=false`（拒绝分支不伪装成任务 Effect）
- `CorrectResolution=true`
- `SafeHandling=true`
- bundle SHA-256：`bb0b237a8102b91b452e8d10fdbd508a83778a9d760e6422b2759fdf53da7a08`
- seal SHA-256：`30159cf0785c217eac49104efcae90b9db0a7f49e8c4297ef72ce3fd44bdc8c1`
- evaluation SHA-256：`af81c425f9c7bee6945a4c338201f5b39e3decf7cf3b8fb414b55545147b1eb1`

两次运行均为 8 个 child：六个 owner、Target、A4。Evaluator 验证七个事实源的 PID、key、
state source、initial head 与 backend identity 两两不同，并验证 A4 PID 不与它们重合。
这只证明本地 process-private shard 分离。

## 红灯如何改变了实现

本轮没有从 unit fixture 直接跳到成功。

1. Runtime 自测与 evaluator unit 最初分别通过，但第一次 actual bundle 碰撞为
   `INVALID_RUN`。主要原因是 public/private binding、service start/freeze identity、
   Target 请求分类和 seal terminal heads 没有真正对齐。
2. Schema 对齐后，actual bundle 成为有效证据，但 evaluator 给出 E1=`UNSAFE_EFFECT`、
   E5=`INVALID_REFUSAL`。该负结果保存在 `artifacts/pre-semantic-fix/`。它促使 Authority
   decision、consumed receipt owner map 和 E5 non-delegable terminal branch 被修正。
3. E1/E5 首次转绿后，独立攻击仍证明三个假阳性：
   - 删除/破坏 Target EXECUTE request 仍可能成功；
   - `execute_at_minute=999` 仍可能借 occurrence minute 0 通过；
   - E5 冻结 truth 内存在替代方案仍可能被判正确拒绝。
4. 当前实现因此增加了 content-addressed causal chain：
   `Authority → EXECUTE request → occurrence/sensors → signed READBACK →
   O_E/O_Q/O_V → O_P`；Authority/deadline 使用 `execute_at_minute`；E5 使用唯一正式
   `alternative_oracle` 并逐项核对冻结 owner shard。
5. Runtime 原先声称“进程先退出、再冻结日志”，与代码真实顺序矛盾。现已改为：
   service 在退出前签出 terminal freeze receipt；controller 等全部进程退出后再组装
   bundle。
6. 首批成功运行把语义 `case_id`、case-derived run/process/path 交给了 A4，因此只保留为
   `LABEL_VISIBLE_DEVELOPMENT_EVIDENCE`，不能证明方法能从 owner 事实辨认执行或拒绝。
7. 删除明文标签后的第二批运行仍把包含 `case_id` 的完整 manifest hash 交给 arm；
   两候选字典攻击可恢复答案。同时 `multiprocessing.spawn` 继承 parent `--case` argv。
   这批也降级为 `HASH_OR_ARGV_RECOVERABLE_DEVELOPMENT_EVIDENCE`。
8. 当前双视图实现以独立随机 `arm_binding_token` 连接 arm-facing IPC；完整 manifest hash
   只存在于 evaluator-private 证据。child 实际 argv 被清理并写入 visibility observation。
   两个当前 run 的 start payload 均为 1333 bytes，语义标签与完整 manifest hash均未出现，
   E1/E5 两候选 hash 对可见内容命中数均为 0。
9. ChatGPT Pro 在未收到本地预期结论的初始审计中提出 causal-twin；收到上述红灯与 v3
   实际证据后，独立修订为：已测通道下 E1/E5 arm-view non-disclosure 可支持，但
   causal `ExactTaskSuccess` 仍需 withheld。它同时给出成熟正向解：
   target-side atomic mutation receipt，或在合法 U/D Authority 下的 serializable
   strong center。

## 当前检查

- evaluator unit：28/28；
- runtime 与 root actual acceptance：13/13；
- root acceptance 会实际启动 child processes，并覆盖：
  - E1/E5 actual bundle 交给独立 evaluator；
  - Target request、signed READBACK、Acceptance/finality causal parents；
  - 同 operation 第二次 EXECUTE 幂等且不产生第二 Effect；
  - E5 private alternative 矛盾必须得到 `INVALID_REFUSAL`；
  - 嵌套 `case_id`、完整 private manifest hash 与 CLI `--case` argv 不能进入 arm
    visibility；
  - run-scoped artifacts 不覆盖旧 run，latest pointer 绑定 run/bundle/seal。

测试数量不是成功理由；成功理由是上述实际运行与反例产生了可区分结果。

## 仍未建立

- E0/E2/E3A/E3B/E4/E6；
- A1/A3/A5 或强中心/人工基线的同 world 比较；
- V1/V2 开放世界完整问题；
- 现实组织 Authority 独立、现实电路 Effect、真人 Acceptance 或财务 Finality；
- hostile same-user 对 bundle 与 seal 的协调重写防护；
- 不依赖合成 world author 的现实“无替代”发现；
- Wave 014 已实际运行 causal twin，并证明“相同终态”不能单独支持 A4
  `EffectAttributableToArm`；Target-native commit/readback 能在受信数字 Target 边界区分
  A4 与 Helper 直接提交者。该结果不反驳这里的 E1/E5 task/correctness/safety 结论，但
  阻止从终态自动晋升为全局因果或现实 Effect；
- 跨进程可信物理时钟。当前因果顺序依靠内容父引用；逻辑 minute 只用于合成任务期限；
- 真实维护成本、锁定、停更、迁移、安全和长期漂移。

## 下一条高价值行动

causal-twin 已在 Wave 014 完成。下一步先实现 `RUNNER-NEXT-ABSTRACTIONS.md` 的五个接口，
避免把当前 blacklist projection 和隐藏场景泄漏风险复制到新案；随后按
`REMAINING-CASE-CONTRACTS.md` 扩到剩余六案，并按 `FAIR-BASELINE-CONTRACT.md` 加入
direct platform、lawful strong center、general model 和 human institution。任何现有
组合完整解决都登记为正向方案。
