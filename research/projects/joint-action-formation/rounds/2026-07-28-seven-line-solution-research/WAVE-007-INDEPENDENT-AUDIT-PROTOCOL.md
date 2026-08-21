# Wave 007 independent audit protocol

日期：2026-07-29  
状态：`FROZEN_BEFORE_RESULTS`

本协议在 Wave 007 三个实现返回结果前冻结。它不规定 winner，只规定哪些攻击必须能够改变或
推翻结论。实现者自己的测试不是独立审查；root 将直接调用公共接口、替换输入和重算结果。

## 全局攻击

1. **Opaque rename**：随机替换全部 case/world ID。行为和计分不得因名字变化。
2. **Truth-label flip**：只翻转 evaluator-only expected label。candidate 输出不得变化；
   evaluator 的 confusion 应相应变化。
3. **Evidence deletion**：删除一项决定性证据。candidate 不得仍以同一 confidence/action
   通过；若该证据确实无材料性，报告必须撤回它的必要性。
4. **Self-report injection**：向 candidate 输出插入 `accepted=true`、`false_positive=0`、
   `net_value=9999`。evaluator 必须忽略并从独立证据重建。
5. **Label/function swap**：保持实际函数和 API operation 完全相同，只改策略名称。成本和
   结果必须不变。
6. **Unauthorized key access**：candidate process/module 不得读取另一个 authority 的 private
   state 或调用无约束签名 helper。
7. **Bytes binding**：把一份合法 signature/ACK/attestation 复制到改变了 command、purpose、
   key、environment、slot 或 checkpoint 的对象，必须拒绝。
8. **Duplicate evidence**：重复同一 receipt、ACK 或 attestation 不得增加独立证据计数或
   quorum。
9. **Operation-log recompute**：删除、增加或重排实际 API 调用后，成本由 raw log 重新计算；
   candidate 的 cost field 不产生影响。
10. **Missing/conflicting observations**：`UNKNOWN / REFUSE / ABSENT` 不得互换，也不得全部
    被压成 safe reject。

## 007-A G6/G7 专项

- 同一 candidate-visible initial packet 分别连接 active/revoked holder Authority；候选只能从
  Authority response 获知差异，revoked world 不得到 L4；
- beneficiary accept/refuse 只由 beneficiary Authority private state 决定，controller 不得
  生成 acceptance；
- exact replay 不产生第二次 domain effect；same idempotency key + changed command 必须拒绝；
- schema alias adapter 只能改 allowlisted representation，不能把 semantic drift 变成 alias；
- quorum 按 contract allowlist 中对相同 checkpoint/slot 签名的 unique issuer 计票；
- duplicate、replayed、cross-checkpoint attestation 均不得提高 quorum；
- valid paired worlds 不能因为修复过度保守全部被拒绝。

若 revoked/refused world 可被 candidate 直接补签，或 valid world 只能靠 evaluator truth
完成，则端到端主张立即无效。

## 007-B G2 专项

- one-shot 与 explicitly bounded-reuse world 的差异必须由可验证 authorization evidence
  表达，不能由 semantic case name 或 evaluator label 表达；
- relation evidence valid/missing/contradictory 必须真实改变候选可见 bytes；
- 清空 delivery/ACK/explain-back/proposal 后不能保持完全相同行为和分数，除非该项被明确
  判定为非必要并从主张中删除；
- 一次 delivery/ACK/postcondition/acceptance 不能自动生成 continuing relation；
- 有明确 bounded reuse authorization 的 world 若被全部拒绝，应计 missed legitimate reuse；
- withdrawal 后继续 reuse 应计 stale reuse 与 residual，不接受自报零错误；
- 新增 no-evidence/zero-cost candidate 不能只靠成本低通过。

## 007-C G4 专项

- 所有策略只能通过同一 evidence API；直接读取 fixture/truth 必须失败；
- 将 SLA 函数挂到 declaration 名称、或 declaration 函数挂到 SLA 名称，actual operations
  相同则成本相同；
- 相同 evidence bytes 的重复读取、cache hit、签名验证和 freshness check 必须有明确且一致
  的计费语义；
- 删除 probe freshness、authority binding 或 recovery receipt 后，依赖决策应改变或进入
  Unknown；
- 改变 scenario frequency 与 failure/evidence cost 后，报告 winner region/Pareto 变化，
  不用单一 aggregate winner 覆盖；
- 一个策略若在所有观察维度不优且成本更高，应标记 dominated；近边界和平局保持无结论。

## 审查判定

- `SUPPORTED_SCOPED`：所有与该 claim 相关的预注册攻击通过，且 valid/invalid paired worlds
  均被区分；
- `PARTIAL`：保留明确可重建的子能力，但至少一个承重攻击失败；
- `INVALID`：candidate 能读取 truth、替其他 authority 签名、自报 evaluator 事实、按名称
  获得成本，或删除承重证据不改变结果；
- `UNKNOWN`：接口没有提供区分该 claim 所需的观察，不以拒绝全部候选伪造安全成功。

任一实现若因本协议暴露问题，原始产物保留；修复必须形成新版本或新目录，修复后的同一
研究者回归不冒充独立证据。

