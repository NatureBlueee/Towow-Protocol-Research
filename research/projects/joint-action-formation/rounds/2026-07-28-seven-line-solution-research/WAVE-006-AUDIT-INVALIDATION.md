# Wave 006 adversarial invalidation

日期：2026-07-29  
状态：`ADVERSARIAL_AUDIT_COMPLETE / CLAIMS_REOPENED`

## 为什么这份记录存在

Wave 006-A/B/C 的原测试共 `45/45 PASS`，manifest、source、shared-task 与结果 hash 绑定也通过。
这些绿灯随后被独立 mutation 审查推翻或显著缩窄。原实验目录保留不改，作为“形式闭包和测试
全绿仍可能没有检验实际主张”的失败证据；本文件覆盖其当前研究解释。

## G2：原比较无效

当前状态：`EVALUATOR_FIXTURE_INVALID`

已复现的攻击：

1. evaluator 不读取候选的 `relation_evidence`、delivery、ACK 或 proposal，只读取成本和候选
   自报 trace；
2. 清空 A 的 `relation_evidence` 后，结果和分数不变；
3. 新增 `D_NO_EVIDENCE`，只令 coordination cost 为零，仍得到 `PASS`、reuse `1`、
   false positive `0`、net value `53`，高于 A 的 `51`；
4. A/B/C 的任务行为相同，winner 由硬编码成本决定；
5. shared world 已经冻结 `ONE_OPERATION_ONLY`、fresh authorization 和
   `PROPOSED_NOT_CONSTITUTED`，因此“不创建 Relation”是输入前提的直接重述，不是由三种
   relation evidence 的差异产生的结果。

因此 Wave 006-D 中“A 在全部非负采样权重下不劣于 B/C”的数学计算只说明：

> 当任务结果和错误计数被预先设为完全相同，额外成本更少的标签得分更高。

它不能证明 delivery receipt 足够，也不能证明 RelationVersion 在原问题上没有材料性增益。

当前只保留一个条件性设计约束：

> 如果任务已被主体明确冻结为 `ONE_OPERATION_ONLY`，系统不得把一次送达、ACK、postcondition
> 或 acceptance 自动物化为持续关系。

## G4：原 winner 降级，成本模型无效

当前状态：`LABEL_COST_INVALID / DISTRIBUTION_AND_WEIGHT_SENSITIVE`

已复现的攻击：

1. false-action loss 从 `18` 改为 `5`，聚合 winner 从 `SLA_RECOVERY` 翻转为
   `DECLARATION`；
2. 复制 steady-low-risk case 20 次，聚合 winner 同样翻转；
3. 成本按 `strategy_id` 标签收费，而不是按实际读取和验证的证据收费；
4. 把 SLA 的决策函数挂到 `DECLARATION` 标签下，仍享受 declaration 的低成本，并以
   `204.9` 击败原 SLA 的 `159.7`；
5. Wave 006-D 的 7,200 点扫描准确揭示了权重敏感性，但仍继承了标签收费和冻结计数，不能
   修复 evidence-access provenance 缺失。

仍可保留：

- fixture 内“probe 成功以后 holder revocation”能够区分静态声明与当前可依赖性；
- `operation success`、`capability`、`safe reliance`、`business effect` 不是同一事实；
- 在原 22 个 decision point、原分布和原权重下，SLA baseline 得分最高；
- 在原冻结计数和采样空间下，winner region 与阈值计算成立，但只作为成本模型诊断。

下一版必须从策略实际读取、验证和请求的 evidence operation log 计费，并报告 Pareto frontier
和分布敏感性，不再先指定策略标签成本。

## G6/G7：端到端结论无效，只保留 signer ladder 的窄证据

当前状态：
`END_TO_END_AUTHORITY_INVALID / SIGNER_LADDER_ATTACKS_4_OF_4_REJECTED`

已复现的攻击：

1. verifier 不校验 holder 对 current contract 的授权，也不读取 `holders_revoked` 或
   `withdrawn_authorities`；
2. revoked-holder contract 和 withdrawn `LAB-SEEK` contract 均可由 `build_effect` 生成并
   通过到 L4 `BENEFICIARY_ACCEPTANCE`；
3. 只重命名 `case_id`，`REAUTHORIZE` 即可抹掉 holder revocation 或 beneficiary refusal，
   并返回 `ACCEPTED`；
4. 只重命名 partial-recovery case，`IMMUTABLE_REPLAY` 的恢复结果就改变；
5. `false_positive` 和 strategy-row `false_promotion` 被常量写为零；
6. `valid_current_possible` truth 标签可直接改变 false-negative；
7. `complete_from_partial` 与 `REAUTHORIZE` 持有全部测试私钥，直接为 recipient、simulator
   和 beneficiary 制造签名，等于把成功写进策略。

仍可保留：

> 五级 verifier 在当前局部 fixture 中确实拒绝了四种“上一层 signer 自行晋升下一层”的错误
> signer 攻击，结果为 `4/4 rejected`。

不能保留：

- 三种 reopen strategy 的逐 case winner；
- “成熟技术组合完整解决当前 G6/G7 scope”；
- revoked/refused cases 能被端到端安全拒绝；
- false positive、false negative 或恢复净值的原数值。

## 方法上的修正

下一轮不是增加更多测试装饰，而是改变被测系统边界：

- case ID 必须 opaque，策略不得从名字读取 truth；
- Authority service 独立持有 holder、recipient、simulator、beneficiary key；
- 策略只能提交 request，不能直接制造其他主体的签名；
- revoked、withdrawn、refused 的 Authority 必须拒签，并留下可验证 refusal；
- evaluator 从独立 truth 和实际 operation/evidence log 重建错误、成本与恢复；
- 使用 paired hidden worlds，让 active/revoked、accept/refuse 等只有 authority state 不同；
- mutation 必须覆盖重命名、删证据、标签换函数、伪造成本、truth-label 翻转。

## Anchor equivocation：理论条件保留，quorum 实现重开

当前状态：
`SINGLE_VIEW_BOUNDARY_SUPPORTED / QUORUM_IMPLEMENTATION_DUPLICATE_VOTE_INVALID`

Wave 006-E 的首轮 `13/13 PASS` 支持两个局部判断：

- 同一合法 key 对同一 slot 签两个分支时，每个只看到一个分支的 client transcript 与某个
  honest single-branch world 不可区分；
- client gossip 获得第二个分支后能够验证冲突。

但 root 的二次 mutation 发现 `obtain_quorum` 按 attestation 数量而非独立 issuer 数量计票：

```text
branch A witnesses = [WITNESS-1, WITNESS-1] -> quorum = true, unique issuers = 1
branch B witnesses = [WITNESS-2, WITNESS-2] -> quorum = true, unique issuers = 1
```

由此两个冲突分支都能获得当前实现声称的 2-of-3 quorum。原测试只使用去重后的 witness list，
没有检验 duplicate/replayed attestation。

因此保留的是条件性理论句：

> 若 quorum verifier 只计算 contract allowlist 中不同 witness identity 对同一
> checkpoint/slot 的有效 attestation，且 `2q > n` 并至少一名 quorum-intersection witness
> 不对冲突分支双签，则两个冲突分支不能同时获得 quorum。

当前实现没有满足前半句，不能作为该理论条件的实现证据。Wave 007 必须增加 unique issuer、
checkpoint/slot binding、duplicate vote、replayed attestation 与 cross-checkpoint
attestation 攻击。

## 研究含义

这不是 Wave 006 “没有产出”。它找到了一类会反复制造伪成功的 evaluator 结构：

> 当候选能够自报 trace、成本由名称决定、策略持有 truth-correlated case label 或所有 authority
> keys 时，测试和 hash closure 可以全部通过，但它们只证明实现忠实执行了答案泄漏。

这一失败直接改变后续实验架构，并保留了少量仍经攻击成立的局部能力。任何未来材料引用
Wave 006-A/B/C/D/E 时，必须同时引用本文件。
