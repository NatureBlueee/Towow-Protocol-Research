# Codex CLI cohort 002：七线 discriminator 综合

日期：2026-07-29  
状态：`SEVEN COMPLETE / ROOT REVERIFIED / ADVERSARIAL INTERPRETATION REVISED /
LOCAL SYNTHETIC / NO FORMAL PROMOTION`

## 一、这一轮真正回答了什么

第二批不是再写七份方案，而是把第一批 Codex CLI 研究和七份 ChatGPT Pro 审计转成了
七个可运行的小型 discriminator。七条母线分别由独立 Codex CLI 主会话执行；每个主会话
实际建立 A/B/C 线内研究者，根会话再重新运行主要测试与结果。

七线 final 初步给出了多个“现有组合同分或闭合”的乐观解释；根会话完成三路只读敌对复核
后，撤回了其中由共享实现、controller 赋值或 oracle 口径预定的部分。当前最重要的结果是：

```text
G1
  provenance evaluator、invalidity gate 和双分母变得可运行；
  但方法只在预枚举 t0_paths 中选择，不能证明一般 discovery/formation。

G2 / G3
  都形成了有用的语义分类器；
  但多臂共享同一核心决策，方法同分是 alias-by-construction，
  不能支持成熟组合、中心、人工或 candidate 的经验等价。

G4
  是当前最有区分力的局部 harness：
  success/resolution、P0/I/P1、pair quantifier 和实际 readback 均已分开；
  四臂仍都没有解决当前分母。

G5
  race/fence/materiality/Standing/migration 回归例可运行；
  但强中心与 Saga 的部分“闭合”由 controller 直接赋值，真实 policy products 均未运行。

G6
  证明完整 owner observation 给定后的 12 对语义投影可以保持；
  但三实现高度同构，不是 transaction/workflow/人工/中心的端到端比较。

G7
  形成了 18-world recovery/migration harness；
  但 w010/w011 的 expected action 相同，当前没有真正编码 safety-liveness 对立，
  所以不可区分边界的强结论撤回。
```

因此当前可以写：

```text
EXISTING_TECHNOLOGY_VALUE = POSITIVE
LAWFUL_STRONG_CENTER = MAY_FULLY_SOLVE_IN_ITS_AUTHORITY_STRATUM
LOCAL_FIXTURE_CONFORMANCE = POSITIVE_SCOPED
G2_METHOD_COMPARISON = ALIASED_BY_SHARED_EVENT_DERIVATION
G3_METHOD_COMPARISON = ALIASED_BY_CONSTRUCTION
G5_REAL_PRODUCT_COMPARISON = NOT_RUN
G6_IMPLEMENTATION_INDEPENDENCE = NOT_ESTABLISHED
G7_SAFETY_LIVENESS_FRONTIER = NOT_TESTED_BY_CURRENT_ORACLE
REAL_EXISTING_TECH_FULL_SOLUTION = NOT RUN
GENERAL_MODEL = NOT YET ISOLATED AS A DISTINCT EXECUTED ARM
NOVEL_PROTOCOL_NECESSITY = NOT DEMONSTRATED
FULL_V1_V2_EPISODE_SOLUTION = NOT RUN
```

“未证明新机制必要”是正向研究结果，不是通爻价值为零。若下一轮把这些成熟能力无损串联后
解决完整任务，这个可复现组合本身就是通爻解决方案。

## 二、逐线最窄结果

| 线 | 实际分母与运行 | 当前最窄结果 | 不能外推 |
|---|---|---|---|
| G1 | 主候选 10 worlds；`|L_benchmark|=9`、`|D_actual|=2`；19+18 tests | evaluator 能拒绝 wrong Authority、same-source alias、post-treatment evidence 等攻击 | `t0_paths` 已预枚举 allowed/cost/evidence；2/2 只是极小 path-selection 上界，不能选 discovery 方法胜者 |
| G2 | 12 worlds × 4 arms = 48 runs；五轴 240/240；13 tests | owner-event semantic evaluator 能分开 constituted/understood/claimed/authorized/activated 与 T5 platform-direct | 四臂都走 `_common_candidate` 并共享 owner events/evaluator；同分不能支持四种方法等效或 replication 无增益 |
| G3 | 6 worlds × 5 arms = 30 runs；16 tests | `C/N/E/T/V` 六类量词、actual miss、open Unknown 与 task substitution 可以被 evaluator 区分 | 五臂都直接调用同一 `choose(packet)`；candidate-exclusive 0 是构造结果，不是方法比较 |
| G4 | 14 worlds / 7 pairs / 4 arms；13+6 tests | success 与 resolution 分离；成熟组合和同权限中心 success 都为 `TP=5,FP=3,TN=2,FN=0`；合法委托中心 success `TP=1,FP=0,TN=5,FN=2` | hard universal 只到 action depth 2；没有 blind truth owner；成本是 fixture 账 |
| G5 | 50 race cells、7 local native cases、13 provider-shape cases、4 owner processes；6+10 tests | no-common-transaction 暴露 4 次 transient stale Effect；hold/confirm/fence 的当前回归边界可运行 | controller 直接消费部分 fixture truth；Saga 只记录 compensation intent；OPA/Cedar/OpenFGA/XACML 都未运行 |
| G6 | 12 pairs × 3 strata × 3 workers = 108 conformance records；31 tests | 完整 owner observation 给定后，三份语义投影都保存 raw occurrence、Authority、CountsTowardQ、recovery 和 settlement 差异 | 108/108 包含正确阻断/Unknown；三 worker 高度同构并共享 owner/evaluator，不是三种端到端方案 |
| G7 | 18 worlds × 6 methods = 108 method-world traces；24 tests | 23 exact-pass cells、5 unsafe cells、17 unjustified cells、12 unreconciled cells、0 history rewrite | hidden pair 两侧允许相同保守动作，未编码 liveness 对立；12 unreconciled cells 只来自 2 个 unique worlds |

G2 与 G6 在根会话首次并行复跑时分别触发 30 秒和 10 秒子进程 timeout；停止并发后，
G2 `13/13` 在 119.03 秒通过，G6 `31/31` 在 49.38 秒通过。这说明语义结果可复现，但当前
harness 对资源竞争脆弱。它是研究基础设施的真实失败边界，不能用“串行最终绿灯”抹掉。
完整敌对处置见 `ROOT-ADVERSARIAL-AUDIT.md`。

## 三、为什么“大家都有这些技术”，完整问题仍未被证明解决

本轮进一步排除了一个错误解释：问题不是因为别人缺少某种神秘协议。更准确的情况有四种。

### 1. 很多现有能力已经成为正向候选，但这一批没有完成公平比较

本轮的 owner evidence、量词、race/fence 和 Effect-role 语义，都能由常见成熟机制表达。
这是现有技术的重要正向信号，但 G2/G3 的方法同分由共享函数预定，G5 没有运行真实产品，
G6 又是在完整 observation 已给定后做同构投影。因此不能把“表达得出”升级为“现有产品已经
端到端解决”。

当前可以把以下内容转成下一轮的可替换组件与回归控制：

- G2：owner evidence、逐轴构成与 platform-direct bypass；
- G3：planner/workflow 对封闭条件形成的求解；
- G5：owner receipt、bounded confirm/hold、target-enforced fence、compensation；
- G6：occurrence、Authority、CountsTowardQ、recovery 与 obligation-specific settlement
  的分离。

### 2. 现有系统常把承重事实作为免费输入

产品分别能搜索、规划、授权、签名、工作流、事务、readback 和迁移，但通常不共同保证：

```text
谁是当前 owner
→ 对哪个 exact object/version 作出了什么 act
→ act 在使用点是否仍 current
→ target 是否真正执行 fence/conditional write
→ 哪个 Effect 实际发生且由谁造成
→ 哪个主体对哪个 Effect/goal 作出 Acceptance
→ 漂移或迁移后哪些 justification 仍成立
```

当 benchmark 预先给出这些答案，组件串联看起来天然闭合；当它们必须通过合法 owner
observation、commitment、target enforcement 和 readback 取得，G1/G4/G7 的失败才出现。

### 3. 真正的不可区分 residual 仍需正确实验，而不是靠叙事宣布

G7 的 `w010/w011` 确实产生相同 public transcript，且 `w011` 中继续会 unsafe。但 oracle
同时允许两个 world 都 `BLOCK/BOUNDED_UNKNOWN/GLOBAL_REOPEN/HUMAN_AMEND`，没有要求
`w010` 继续。因此当前只证明 unsafe 分支存在，没有证明“保安全必损 liveness”的前沿。

下一版必须让 valid 分支要求继续或对 conservative block 计 liveness loss，再检验能改变
结果的条件：

- 合法的新 owner observation；
- 新 commitment、lease 或 delegation；
- target-side fence；
- 人工 discovery 或制度裁决；
- 全局阻断；
- 显式接受 safety-liveness 权衡。

如果成熟制度或保守退出最好地实现这些条件，它仍然是正解。只有正确编码的对立在异质任务
和实现上重复，且所有合理现成路线同样失败，才有新机制理由。

### 4. 七条局部 harness 尚未组成同一个 episode

当前没有一次运行同时要求：

```text
G1 合法发现
→ G2 多主体构成与认领
→ G3 条件形成
→ G4 可靠依赖
→ G5 commit-time Authority
→ G6 Effect/Acceptance/Settlement
→ G7 漂移、恢复与迁移
```

因此不能把语义 conformance 相加成完整 V1/V2 闭合。下一轮的承重任务不是继续平均扩展
七个 benchmark，而是让真正独立的现成实现、中心、人工制度和通用模型在同一个冻结 episode
中实际取得信息、形成 Authority、执行 Effect、恢复和迁移。

## 四、下一轮：跨七线组合 episode，而不是第八个概念

### 4.1 具体任务：CE-001 社区工作坊临时供电恢复

下一轮不用抽象的“联合行动任务”占位。先冻结一个能产生真实执行语义的高保真模拟：

```text
初始请求：
“今天的社区工作坊不能因为停电取消，帮我处理。”

经独立前奏澄清、由 Q owner 认领后的 IntentAtCoordinationInterface：
在 T0+90min 前，为 Venue V 的 Circuit C7 提供连续不少于 45 分钟、
3kW±5% 的临时供电；满足噪声、安全和目标对象限制；不得给其他线路送电；
requester 与 venue 必须对 exact Q_version 和 Effect 作出 Acceptance，
之后才能进入相应 Settlement。
```

`vague goal → Intent` 的澄清前奏单独执行，不偷算进 G1。方案不预设为发电机，也不预设
必须形成新关系；场地方自有电池、标准租赁平台、合法中心、成熟供应链、通用模型 +
workflow 或人工协调都可以完整获胜。

### 4.2 两个互补 Authority family

先建立两个相同任务目标、不同 Authority topology 的高保真模拟 family：

1. `E-U / LAWFULLY_UNIFIED`
   - 同一 Principal 合法拥有全部必要 Authority；
   - center 可以访问完整合法输入并直接控制目标端；
   - 预期强中心应成为完整正解；若不成功，优先修实现或任务表示，不制造分布式机制。
2. `E-P / PLURAL_OWNER_WITH_HIDDEN_EDGE`
   - 多个 owner 保留独立拒绝、撤销与 Acceptance 权；
   - 至少一条 dependency 在初始 packet 中不可观察，但存在有成本的合法 query、
     commitment 或 fence 路径；
   - 用来区分“信息可以被构造”与“完整交互后仍不可区分”。

两个 family 都使用 CE-001 的 exact Q、target、Acceptance 与 Settlement，不换行业皮肤。
在两个 Authority family 内冻结七个 episode 模板：

| 模板 | 主要区分 |
|---|---|
| E0 platform direct | venue 自有合格电池、人员和 Authority；应直接完成，不强造 relation |
| E1 extant multi-owner | 资源、关系、权限已存在；现有 routing/workflow/IAM/readback 应足够 |
| E2 condition formation | 能力存在，但 exact purpose token、短期 delegation 和合作条件需要 owner interaction 形成 |
| E3 ACK-loss pair | submit response 丢失；一支 Effect 已发生、一支未发生，并放置 wrong-object success 干扰 |
| E4 revocation with alternative | reserve 后撤销，但存在合法替代资源方；系统需恢复到任务价值，不能只安全停止 |
| E5 impossible negative control | non-delegable venue owner 拒绝且无替代；正确结果是无 Effect 的有界拒绝 |
| E6 migration/replay | Effect 后、Acceptance 前 coordinator 崩溃迁移；旧 runtime 重启，必须避免重复 Effect 并恢复谱系 |

E3 是两个冻结分支，因此首轮共八个 case。它们同时覆盖成功、合法拒绝、恢复与迁移，不用
扩大成大量同源 world。

### 4.3 比较臂

- `P0_PLATFORM_DIRECT`：平台能够完整承担任务时直接走平台；
- `P1_LAWFUL_STRONG_CENTER`：只在 E-U 或 exact delegation 成立时直接闭合；
- `P2_EQUAL_INFORMATION_CENTER`：与其他臂同 information/API/action，但不能代签 owner；
- `P3_GENERAL_MODEL_MATURE_STACK`：通用模型负责澄清、规划与工具选择，组合目录、CLM/HITL、
  IAM/policy、workflow/outbox、reservation/fence、readback 与 settlement rail；
- `P4_DETERMINISTIC_MATURE_COMPOSITION`：不依赖模型推理，只用规则、workflow、IAM、
  reservation/fence、readback、settlement rail 的可执行组合；
- `P5_HUMAN_INSTITUTION`：有界人工规则、审批、拒绝与恢复；
- `P6_RESIDUAL_CANDIDATE`：只有前六臂在同一有界 residual 上失败后才实例化。

不预设 P6 必须存在，也不因前六臂中的任意一臂获胜而降低研究价值。所有 arm 必须使用真正
独立的 decision implementation；共享 evaluator 可以评分，不能再共享 `_common_candidate`
或 `choose(packet)`。

### 4.4 冻结输入与干预

每个 episode 同时冻结：

- `IntentAtCoordinationInterface`，不把 vague goal→Intent 偷放进 G1；
- exact task、object、version、necessary Principals 和 Acceptance criterion；
- owner services、Authority topology、允许的 disclosure/action envelope；
- cold start 与 repeat start；
- commit point、target-native outcome、effect readback 与 obligation scheme；
- source/target runtime、migration capsule contract 与 old-runtime epoch。

最小干预集：

- owner refusal / deferred answer / stale head / post-check revoke；
- same-source alias / wrong Authority / wrong object；
- response lost before与after Effect；
- target ignore/restart-loss/cross-region fence；
- hidden dependency valid/revoked；
- material goal change / low-coupling leaf change；
- planned migration / crash takeover / capsule field loss。

### 4.5 首要指标

不先报一个混合“90%”。逐项报告：

- 完整任务 success；
- resolution；
- achievable-case success coverage 与 all-case resolution coverage；
- factual unsafe continuation；
- false closure / unjustified continuation；
- revocation 后 recovery-to-value；
- owner refusal、Unknown 与 opposition 是否保真；
- Effect、Acceptance、Settlement 是否 exact-object/version bound；
- duplicate Effect、unreconciled Effect、missed/over reopen；
- candidate-exclusive success；
- cold-vs-repeat 净成本；
- disclosure、等待、HITL、compute、recovery 和 governance 原生成本。

只有在同一分母和同一承诺强度下，才比较组合覆盖。

### 4.6 何时收敛，何时创新

如果平台直达、合法强中心、成熟组合、人工制度或通用模型组合中的任一路径：

- 七个可达 case `7/7` exact-task success，八个 case `8/8` correct resolution；
- 没有越权、错对象、false closure 或未对账 Effect；
- E4 恢复到任务价值，E5 不越权，E6 完成迁移、Acceptance 与 Settlement 谱系；
- 在 remove/reverse/migrate 后仍能复现；
- candidate-exclusive success 为 0，blind holdout 与第二实现仍复现；
- 成本没有吞噬任务价值；

则该路径就是当前完整解，下一步转向复现、迁移和简化，不新增平行机制。

只有当：

1. residual 在 E-U 与 E-P 中有精确作用域；
2. 至少两个异质任务 family、两个实现和未见 holdout 重复；
3. 强中心、成熟组合、人工制度、平台直达、通用模型与合理 adapter 均在同一合法 envelope
   中失败；
4. 失败不能由增加合法 observation、commitment、fence、delegation 或降低承诺强度消除；
5. residual 对完整任务结果而非 schema 美观产生可观测损失；

才创建最小的新机制候选。若创建，就必须完整覆盖该 residual 的失败、恢复、迁移和验证，
不能以“最小创新”名义留下同一个问题。

## 五、研究调度变化

七条线继续保留，但不再平均消耗资源：

- G2/G3/G5/G6：保留语义模型、攻击器与回归例，但重写独立 executors；当前不能视为已通过
  的方法比较；
- G1：重点放在合法 evidence path、Authority/source alias 与恶意 worker 隔离；
- G4：重点放在 success/resolution、commit-time reliance 与 blind holdout；
- G7：重点放在 hidden-edge observation、cold-vs-repeat、delayed readback 和第二 runtime；
- 根研究：优先运行一个能够同时触发 G1–G7 的完整 episode。

这不是宣布任何一线完成，而是把研究注意力从重复同源 conformance 转向会改变完整解的
组合断点。

## 六、证据与状态边界

本轮共有七个独立 CLI 主会话和线内 A/B/C 职责分工，但它们共享模型家族、仓库、研究传统与
大量输入。它们增加了执行隔离和失败路径，不构成七个独立实验室的外部复现。

所有结果仍是本地合成：

- 没有真实成熟产品端到端运行；
- 没有真人 Principal 理解、认领或 Acceptance；
- 没有现实生产 Effect、付款或跨组织 Authority；
- 没有完整 V1/V2 episode；
- 没有任何 Problem、LineContract、MechanismProfile 或正式 claim 状态变化。

当前产物的用途是：淘汰无区分力 evaluator，保留现有技术的正向能力，定位剩余有界断点，
并为下一次完整组合运行提供可复算条件。
