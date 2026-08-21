# ChatGPT Pro clean-room return — Wave 025

Task ID：`W025-BLIND-QUALIFICATION-CLEANROOM-001`  
返回日期：2026-08-01  
返回来源：https://chatgpt.com/c/WEB:e32002b0-acb4-450a-8527-a5a8093dfbc6  
捕获方式：in-app browser 可见返回的结构化语义转录  
证据身份：`EXTERNAL_CLEANROOM_CANDIDATE / NOT FORMAL COMPARATIVE EVIDENCE`

> Pro 明确说明：输入中给出的 packet SHA-256 只被它当作标识；因为没有独立附件字节流，
> 它不声称自行重算或验证了该 hash。

## 1. Problem reconstruction

目标不是证明五种 treatment “绝对互不泄漏”，也不是提前比较表现，而是在冻结镜像、接口、
权限和威胁模型下，检验合法世界信息被观察之前，是否存在 treatment-visible signal 使攻击者
高于预设界限地区分 hidden world；并检验后续结果能否被 run residue、feedback、controller
substitution 或 post-hoc applicability selection 解释。

需要拆开五种失效：

| code | channel |
|---|---|
| L | answer leakage：ID/hash/file/argv/timing/UI 等提前编码 hidden truth |
| O | order/residue contamination：前序世界、固定顺序、共享进程或文件预测当前世界 |
| F | evaluator feedback：分数、提示、调试或人工反馈影响后续运行 |
| S | controller substitution：controller/adapter/evaluator 代替 owner 授权、执行或接受 |
| A | post-hoc applicability：看到 truth/refusal/crash/result 后才宣布“不适用” |

因此至少要分别给出 information qualification、authority/applicability qualification、
runtime/evaluation qualification；任何一项失败不能由其他两项通过补偿。

## 2. Minimal architecture and experimental unit

最小逻辑架构：private oracle/world service、public mediator、treatment cell、独立
Owner/Target services、batch close 后才读标签的 offline evaluator。controller 不持有 owner
credentials。

Pro 建议的最小实验单位是 `blinded twin pair`：

- public task、authority topology、object、target、operation、failure schedule 与 owner mandate
  相同；
- 只在一个尚未 lawful reveal 的事实上不同；
- 两个 world 位于 fresh cells，左右、启动顺序、host、time slot 随机；
- `W1` 为 authoritative target readback 表示 exact operation 尚未发生且可执行；
- `W0` 为 exact operation 已 final，再次执行会重复 Effect；
- 冻结 lawful reveal interface `Q*`；在 attacker forced choice 前只允许 non-revealing `Q0`；
  `Q*` 首个合法响应后出现的真实差异不算泄漏。

资格对象不是抽象 treatment 名称，而是：

```text
observation regime =
treatment image + launcher + UI/API rendering + credential set
+ authority stratum + host isolation policy
```

其中任一项变化都应重新资格化。机器 regime 用 fresh VM/microVM 或经过同一攻击套件验证的等价
cell；真人 regime 需要 clean browser/workstation session，并按其真实合法工具而非人为统一界面。

## 3. Information boundaries

- Oracle-private：hidden truth、private manifest/hash、label mapping、future order、其他 treatment
  输出、owner secret、evaluator key、positive-control placement。
- Public before launch：冻结问题、value floor、object/target/operation、authority stratum、允许
  动作、API schema、failure schedule、time budget、treatment charter。
- Arm-visible identifier：只能来自与 hidden truth 独立的 opaque randomness；不能从 private
  manifest、expected result 或 case label 派生。
- Pre-reveal runtime：treatment 原生可见的 argv/env/cwd/files/process/socket/DNS/clock/resource/
  UI/log/cache 与 Q0 transcript。
- Lawful post-interaction：Q* 后的 owner/target response、readback、Effect、Acceptance。
- Post-run sealed：可以封存 transcript/output/log，但不能逐轮返回 label/score/correct answer/comment。
- Batch-complete：全部输出与 applicability 记录封存后，evaluator 才解封标签。

特别警告：不要公开 small candidate-world 的 private manifest hash；padding、timeout、error shape、
response length 不得依赖 hidden truth；Q* 请求到首字节之间的 latency 也可能是通道。

## 4. Attackers and controls

Leak-only attacker 不解决任务、没有 owner credential，只在 Q* 前做 forced choice。ensemble 至少
包含 namespace harvester、derived-identifier dictionary attack、active Q0 probe、sequence
attacker、feedback/residue attacker。attacker、feature extraction 和 thresholds 在 held-out batch
前冻结，正式统计不能事后挑最显著攻击者。

两个独立 positive control：

1. `current-run control`：在预注册的可见 surface（env、filename、sibling argv、port/hostname、
   DOM、Q0 latency、dictionary-decodable hash 等）随机植入一 bit hidden truth；attacker 不预知
   被选择的 surface。
2. `contamination control`：牺牲 predecessor 通过 shared cache/tmp、sibling process title、复用
   model/browser session、evaluator hint、fixed order 或残留 transcript 给后继留下 current truth。

还应有 controller-substitution challenge：controller 用自身 credential 调 owner-only Accept/
Effect，或以 wrong object/version/scope 调用；合格必须看到 endpoint 拒绝、无 Effect、无 owner
receipt，且 evaluator 不把 controller log 当 owner act。

解释矩阵：null 无 signal 且两类 control 都可检出，才是 tested-boundary scoped qualification；
null 有 signal 且 controls 有效，是真实 leakage/contamination；null 无 signal 但 control 失败，是
detector inadequate；两者都失败则实验无效。训练集 feature importance 不能冒充已定位 witness。

## 5. Suggested randomization and decision rule

Pro 给出的一个明确但不声称普遍最小的 pair 方案（与本地当前 0.55 margin 方案不同，尚未采纳）：

- development：64 pairs = 32 null + 16 current-leak control + 16 contamination control；
- held-out：192 pairs = 128 null + 32 current-leak control + 32 contamination control；
- 合计每个 regime 256 pairs / 512 fresh-cell runs；held-out 全部封存前不揭示标签或 control type；
- pair side、treatment/regime order、pair order、host/time block、authority stratum 平衡随机；run token
  与 truth 独立；crash/refusal/timeout 不得触发重抽或删除；
- distinct regimes 用 family-wise alpha；若 `m=5`，其候选 rule 为 null `K<=69` 才把单侧
  99% Clopper-Pearson upper 压到 0.65 以下，`K>=78` 为相对 chance 的明确 leakage，70–77 为
  inconclusive；
- 每个 32-pair positive control 至少 30/32，缺失或未提交不能作为错误猜测帮助 null 通过。

它强调 pass 是“没有支持 accuracy 达到/超过登记上界的证据”，不是证明 accuracy=0.5。

## 6. Applicability and authority strata

信息公平不是给所有 treatment 同一 credential。至少预冻结：

- `S-U`：authority lawfully unified；
- `S-D`：exact operation 得到精确 delegation；
- `S-P`：plural owners 保留不可代行 authority。

在 truth/order/result 前冻结 treatment×stratum×object×version×operation applicability、credential
manifest 与理由。strong center 只进入 S-U 或覆盖 exact operation 的 S-D；equal-information
center 不得获得 owner act/acceptance credential；general model 保留 mature execution stack；
deterministic composition 保留 workflow/IAM/outbox/fence/readback/human escalation；human institution
使用真实人员和 non-recommending console。hidden truth 不能改变 topology/applicability；readback
后的 refusal/unknown/defer/crash 是结果，不能重标“不适用”；每个 randomized applicable run 都进
intention-to-treat denominator；不同 strata 内比较，不能插值 plural-authority 世界的缺席 treatment。

## 7. Strongest false-green counterexample

Pro 提出的最强反例不是普通漏扫文件，而是只有 actual treatment 能解码的 keyed covert channel：

```text
arm-visible token = nonce || HMAC_K(nonce, hidden_truth)
```

若 `K` 只存在于实际 treatment binary/model weights/proprietary adapter/system prompt，leak-only
attacker 不拥有它，而 evaluator/world generator 与 treatment 预共享它，则 token 对普通 classifier
像随机数；fresh VM、随机顺序、无 shared file、positive controls 仍可能全绿，但 actual treatment
直接恢复 truth。

因此任何通过都必须继续排除 evaluator-treatment collusion、preinstalled decoder、opaque model 的
特殊记忆、恶意 hypervisor/hardware。可复现 build、code/prompt inspection、独立 oracle、artifact
冻结后才生成 mapping 只能缓解，不能证明 universal noninterference。另一个假绿是 evaluator 在
结果后改变 applicability/failure/success rubric，所以 scoring/applicability 也要在 oracle reveal
前冻结。

## 8. Highest-information next local test

Pro 建议做 sibling-process/shared-state canary A/B launcher challenge：

- weak launcher：相同 public payload/argv/task/random order，但同 OS user，可读 host tmp/process/
  cache；oracle 只把 truth 放进 sibling argv 与随机临时文件；
- candidate launcher：每 trial fresh microVM/equivalent cell，oracle 在 cell 外，无 shared writable
  filesystem/PID/browser/model session，run token 与 truth 独立；
- 两者运行相同 leak-only attacker 与 forced-choice rule。

它直接区分“记录字段 equality + random order”与“attacker 实际不能访问 sibling/residue/feedback”。
前者是审计记录，后者才是待验证 observation boundary。

## 9. Assumptions, failures and unknowns

必要假设包括 oracle/owner/evaluator 诚实且不串通、Q* 前 public twins 语义相同、randomness 与 truth
独立、attacker 权限不弱于 actual treatment、artifact/launcher/credential/UI/host policy 在资格与
比较之间冻结、owner credential 未复制给 controller、human 无隐蔽跨 trial 通讯、batch seal 前
无 evaluator feedback。

任一 truth-derived visible token、shared residue、fixed order、逐轮 feedback、controller 越权、
post-hoc applicability、删除失败/重抽 world/调 rubric、control failure、统计不确定、attacker 权限
更弱或后续 regime 变化，都必须失败或保持不确定。

即使通过，仍未知 universal noninterference、untested/keyed covert channels、阈值以下的弱泄漏、
microarchitecture/hypervisor/hardware channel、长期 human/organization memory、proprietary decoder、
rubric 的现实价值、五 treatment 的性能/排名/coverage、未测 topology/UI/host/version/failure
schedule、receipt 是否等于现实 Effect/Adoption/Acceptance/Settlement，以及外部可迁移性。

Pro 的最终收缩是：以 distinct observation regime 为资格对象，以 blinded twin forced choice 为
实验单位，并把 statistical green、detector validity、authority non-substitution 和 applicability
pre-freeze 分别设为必要条件；其作用只是允许或拒绝同边界下的后续 bounded comparison。
