# Wave 025 pre-run synthesis

日期：2026-08-01  
状态：`ROOT SYNTHESIS / NO QUALIFICATION RESULT YET`

## 发现了什么

四个异质输入没有把“blindness”收敛成单一绿灯，反而把它拆成了层级：

```text
prefix candidate-visible leakage
    -> dynamic lawful-divergence / broker leakage
    -> actual-treatment-specific observation regime
    -> authority/applicability non-substitution
    -> evaluator/selection freeze
    -> lifecycle contamination across real provider/human sessions
```

Wave025 第一实现只触及第一层。它若通过，只能说明冻结 leak-only collector 在固定 OCI prefix
cell 中没有检出超过 0.55 登记界限的 S/R signal，同时两个登记正控可被检出。它不能把下一层
自动写成通过。

## 独立输入真正改变了什么

1. `independent-problem-reconstruction.md` 把资格主体从 arm 改成 batch/stratum，并区分 deployment
   package、reasoning core、ablation 和 lifecycle estimands；本轮合同因此拒绝按 A1–A5 分别自报
   blindness。
2. `red-team-preflight.md` 给出 L01–L15 与 Q01–Q13，迫使本轮保存 raw stdout/out/inspect、使用
   positive control、fresh holdout 和 equivalence bound，而不把 `p>0.05` 当无泄漏。
3. `runtime-reuse-architecture.md` 表明历史 SQLite/signature/fence/readback 链可以复用，但同 UID
   multiprocessing 与 local self-seal 不足；第一实现采用成熟 Docker/OCI、CSPRNG、canonical
   receipts 与外部 pre-run root，通爻只持有 exact projection/evidence semantics。
4. Pro clean-room 没有看到本地 Q0–Q11 或 Docker 方案，却独立提出 distinct observation regime、
   blinded twin forced choice、current-run 与 contamination 两类 control、authority/applicability
   pre-freeze，以及 keyed covert channel 假绿。它使本地 D0/D1 从“两个泛化 leak control”变成
   predecessor residue 与 current-run canary 两种不可互相替代的检测能力。

## 最重要的新反例

即使 leak-only collector、fresh container、random order 与 ordinary classifier 全部绿色，actual
treatment 仍可能拥有 collector 不具备的 decoder：

```text
visible = nonce || HMAC_K(nonce, hidden_truth)
```

当 `K` 预置在 proprietary model、binary、adapter 或 system prompt 中时，普通 collector 只看到
随机 token，真实 treatment 却能恢复 truth。因此：

- prefix collector qualification 不能自动迁移到 opaque actual treatment；
- 后续每个 native treatment 需要以其真实 artifact/launcher/UI/credential/host policy 重新形成
  observation regime；
- world mapping 最好在 artifact freeze 后才产生；
- evaluator/world generator 与 treatment 串通、pretrained decoder、hypervisor/hardware channel
  必须继续在威胁模型外或另开挑战，不能被 Docker green 覆盖。

## 现有技术组合的地位

当前没有证据要求自研容器内核、随机数、数据库、签名或分类算法。成熟组合若通过真实 batch，
就是通爻正向解决方案。通爻需要保留的薄层是：

- 原问题/observation cut/stratum 的精确冻结；
- hidden/private/public/lawful-post-response 的投影；
- treatment-native modality 与 lawful authority 不被统一接口偷换；
- precommit、host-observed evidence、close/reveal/evaluator 的因果绑定；
- scoped qualification state 与下一层重新资格条件。

若成熟组合失败，创新对象也应是被 witness 精确定位的剩余通道，而不是重新发明已有基础设施。

## 为什么还不能开始 A1–A5 比较

当前真实状态仍是：collector 已实现并有单槽 structural smoke；host runner、independent evaluator、
feature plan 正在独立实现；formal batch 尚未 precommit、外部锚定或运行；actual comparative
runs=`0`，winner=`NONE`。即使 prefix formal 通过，还要分别建立 dynamic broker、earliest lawful
divergence、actual native regimes、A3 provider、A5 human session、authority/applicability 和
evaluator feedback 的资格挑战。
