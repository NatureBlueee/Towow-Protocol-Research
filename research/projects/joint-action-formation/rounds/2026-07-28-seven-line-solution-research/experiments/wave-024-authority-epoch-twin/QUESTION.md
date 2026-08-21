# Wave 024：Target-consumed Authority fence × ACK-lost recovery twin

日期：2026-08-01  
状态：`FROZEN QUESTION / IMPLEMENTATION AND RUN PENDING`

## 原问题谱系

本轮不新增一个宏大机制。它从 Problem V1/V2 与 CE-001 中抽取一个承重且尚未共同闭合的有界问题：

> 在同一个 exact Q、object、Target、operation、Authority source、Effect、Acceptance 与恢复谱系
> 中，静态上同形的执行路径能否在 Target 的同一持久化边界区分“尚无 superseding fence”与
> “已消费 superseding fence”，并在 ACK 丢失、
> runtime 终止后分别得到一次 exact Effect 后恢复完成，或零 Effect 的权威拒绝？

如果成熟的 ledger、fence、capability、signed readback 与 workflow 组合完整解决，这就是正向
Towow 结果；只有该组合真实剩余的缺口才可能要求创新。

## 两个隐藏世界

candidate 在两边必须是同一冻结 executable，并在第一个 lawful current-Authority response 前
获得逐字节相同、值级不编码答案的公开前缀。

### S：Target 尚未消费 superseding fence

- 在 Target execute linearization point 前，没有 matching superseding fence 被该 Target
  持久安装；Target 按其已消费的 grant/head/scope view 原子判定 eligible；
- Target 只允许一个 exact occurrence；
- commit 后 ACK 丢失，candidate process 在拿到提交结论前被受控终止；
- 恢复进程必须从 Target-native exact status/readback 判断已提交，禁止 replay；
- O_Q/O_V 只在核验 exact Effect 后各自追加 Acceptance；
- O_P 只在两份 Acceptance 后追加一次 finality。

### R：Target 已消费并确认 superseding fence

- 静态 delegation、candidate 与公共前缀同形；
- 独立 Principal/Authority 域推进 revocation epoch，Target 随后持久安装 matching fence；
- `Authority revoke → Target durable matching fence ACK → execute ingress` 必须形成可复算的
  happens-before；Target 再以其已消费的 head/fence 拒绝 stale credential；
- ACK 同样丢失，candidate process 同样在获知权威结论前被受控终止；
- 恢复进程从 Target-native status/readback 得到未提交与 `REVOKED/STALE_AUTHORITY`；
- 不得 retry、不得产生 Effect、Acceptance 或 success finality；拒绝本身需要 Target-native receipt。

### U：Authority 已撤销但 Target 尚未 ACK（负控，不计分）

- Authority 已记录 revoke，但 Target 尚未持久安装并确认 matching fence；
- execute 与 revocation 传播没有足以支持 R 的完整顺序；
- evaluator 必须返回 `CONCURRENT_OR_UNORDERED / NOT_SCORED`，不得把它强塞进 S 或 R，
  也不得用它证明全局即时撤销。

## 本轮实际检验的 claims

1. `CL-024-TARGET-CONSUMED-AUTHORITY-FENCE`：对 exact Target 与 mutation boundary，authenticated
   matching fence 的安装和新 semantic Effect 的执行由同一个 Target-native durable state
   machine 串行化。若 `fence f>e` 在 execute linearization point 前已安装，`D@e` 不产生新
   Effect；否则 eligibility 只按 Target 已消费的 grant/head/scope view 判断。它不是启动时
   credential、controller case label 或事后状态推断，也不建立 Authority-global currentness。
2. `CL-024-EXACTLY-ONCE-RECOVERY`：ACK 丢失与 runtime 终止后，signed exact status/readback 足以
   使 S reconcile 且不 replay，使 R 保持零 Effect 且不把 refusal 修成 success。
3. `CL-024-NATIVE-POSTCONDITIONS`：Effect、O_Q/O_V Acceptance 与 O_P finality 分别由其原生域
   append-only 产生，controller 不得代写。
4. `CL-024-ISOMORPHIC-BLINDNESS`：第一个 lawful Authority/Target response 前，S/R candidate
   可见 preimage 与启动面逐字节相同；case、expected、epoch role 不得经 ID、路径、顺序、错误
   形状、时延或 opaque handle 值泄漏。

四项可以分别支持、保持 Unknown 或被反驳。任一项通过都不能晋升其他项或 Problem V1/V2 整体。

更强命题 `CL-024-GLOBAL-AUTHORITY-CURRENTNESS` 明确为 `NOT_TESTED`：本轮不证明 Authority
记录 revoke 后（包括传播延迟或分区期间）任何 Target 都不再提交。该命题需要额外的 permit、
lease 或跨域事务语义，不能由本地 Target fence twin 推出。

## 必须独立的事实域

- Principal/Authority：独立 key、delegation head、revocation head 与 signed fence update；
- Target：原子 currentness gate、operation ledger、Effect/refusal receipt、status/readback；
- Candidate runtime：真实独立进程，只消费公开 API，不写 owner/Target truth；
- O_Q、O_V、O_P：三个独立 append-only store/process；
- Controller：冻结 world、调度故障、启动/终止进程、收集原始文件，但不决定任务结果；
- Root evaluator：不导入 runtime summary，从冻结原生 stores 重算 claims。

本地 key registry 只能支持“冻结合成 Principal 域”的有界结论，不得称为现实法律 Authority。

## 首轮成功与失败形状

首轮只运行同一成熟组合 candidate 的 S/R discriminator，不比较 A1–A5，不选赢家。

```text
S: Effect count = 1; retry Effect = 0; two Acceptance; one finality
R: Effect count = 0; retry Effect = 0; Authority rejection = 1;
   Acceptance = 0; success finality = 0
```

两个世界若最终都“成功”、都“拒绝”、都能 replay、都由 controller 补 receipt，或者 pre-response
公开前缀不同，则本轮不成立。若 Target 缺 currentness gate，R 仍提交，构成成熟组合的必要性反例；
若仅移除模型/目录/RAG 不改变结果，不把它们虚构成本轮必要机制。

## 本轮不负责

- 不证明 Authority-global instantaneous revocation、物理供电、法律 Authority、生产可靠性、
  恶意同权限本机 writer resistance；
- 不证明 A1–A5 任一 arm 的总体能力、成本或优胜；
- 不证明 relation formation、全开放世界发现、NAC、ARD、RAG 或协议整体；
- 不用本轮单个合成 twin 宣称 V1/V2 完整解决或新协议必要。

## 下一层准入

只有本轮产生实际独立进程、原生 DB/receipts、独立 evaluator、攻击重放和 root-bound artifact，
才能作为 Wave 023 之后的 `LOCAL_SYNTHETIC_DISCRIMINATOR`。进入 A1–A5 公平 batch 还需真实
A3 provider、A5 human、每 treatment 多 replicate、共同预算与 cost receipts，不能由本轮替代。
