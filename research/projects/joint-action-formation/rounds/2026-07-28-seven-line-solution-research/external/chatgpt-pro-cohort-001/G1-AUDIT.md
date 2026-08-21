# ChatGPT Pro G1 独立审计

日期：2026-07-29  
状态：`INDEPENDENT AUDIT / CANDIDATE EVIDENCE ONLY / NO FORMAL STATUS CHANGE`

## 审计对象与结论

本审计只检查：

- [`G1-return.md`](./G1-return.md)；
- [`G1-sources.md`](./G1-sources.md)；
- 它们与 Problem v1/v2、当前 G1 设计及统一任务分母之间的关系。

总判断：`REVISE_BEFORE_EXPERIMENT`。

Pro 返回包含值得吸收的材料，但当前不能直接冻结为 G1 evaluator：

1. 一手来源足以支持“封闭、已加入、已表达的任务中，中心化制度或成熟组合可以形成真实
   正例”，尤其是肾脏配对捐献；不支持“纯全信息中心已经一般性解决 G1”。
2. `INDEX_HIT / MODEL_HIT / ACTIVE_REVELATION / JOINT_ACTIONABILITY_INCREASED /
   INVALID_SUCCESS` 是有用的研究区分，但当前单标签、判定顺序和 \(t_0\) 回放会发生
   post-treatment evidence 注入、oracle 自证和 Authority 失效被正标签抢先覆盖。
3. 30 个 episode 可作为分层机制 pilot，不能估计现实频率。VPDR 的全信息分母与当前 G1
   的 actual-policy 分母不同；强中心上界与同访问公平基线也被混成了一组。
4. Pro 把“模糊目标到 Intent 生成”纳入 G1，而 ACTIVE V2 明确把上游 Intent 生成排除在
   当前研究对象外。若不拆分，实验将静默改变问题。

## 一、来源主张审计

### Verified：一手来源直接支持

| 主张 | 审计结果 | 能支持什么 | 不能支持什么 |
|---|---|---|---|
| OPTN 肾脏配对捐献由全国数据库匹配，医院参与规划，捐献者需意愿、医学和心理评估 | `VERIFIED`。HRSA 说明移植团队向 OPTN 管理的全国数据库录入信息，OPTN 每周两次匹配并与医院规划移植；参与者须自愿，捐献者须完成医学和心理测试。[HRSA KPDPP](https://www.hrsa.gov/optn/patients/organ-donation/living-donation/kidney-paired-donation-pilot-program-kpdpp) | 支持“中心匹配 + 本地专业验证 + 人类/机构协调”在封闭登记池内产生真实可执行路径 | 不证明中心掌握所有 raw truth，不证明所有可行交换均被发现，也不证明相对联邦/人类方案的因果优势 |
| KPD 有额外知情同意要求 | `VERIFIED`。HRSA 记录该政策已实施，要求移植机构解释风险、收益和匹配物流。[HRSA informed consent](https://www.hrsa.gov/optn/policies-bylaws/public-comment/proposal-for-informed-consent-for-kidney-paired-donation) | 支持优化者、验证者和主体同意不能折叠；KPD 是成熟社会技术组合正例 | 不证明“签署即理解”、不存在诱导，或所有撤回/失败分支被完美处理 |
| TrialGPT 的检索、资格判断和筛选效率数字 | `VERIFIED`。NLM/NIH 报告 183 个合成患者、75,000+ 标注、少于 6% 候选召回 90%+、1,015 个患者—标准对 87.3% 准确率，以及用户实验筛选时间降低 42.6%。[NLM TrialGPT](https://www.ncbi.nlm.nih.gov/research/trialgpt/about/) | 支持通用模型已能显著改善候选检索与资格预筛 | 不支持患者认领、现场名额、PI 接受、知情同意或真实入组闭合 |
| PSI 能在不披露非交集元素的情况下计算交集 | `VERIFIED`。[NIST PSI](https://csrc.nist.gov/Projects/pec/psi) 明确把 PSI 定义为 MPC 的特殊情形 | 支持“已有共享集合语义时降低原值披露”的组件能力 | 不会生成 query、共享谓词、价值函数、授权或关系语义 |
| Matching with Contracts 在明确条件下提供理论保证 | `VERIFIED`。原论文摘要只在工人可替代并满足 aggregate-demand law 等条件下给出相关性质。[AEA original paper](https://www.aeaweb.org/articles?id=10.1257%2F0002828054825466) | 支持已知合同语言、特定偏好结构下的成熟匹配机制 | 不支持开放角色、未知合同字段、互补偏好或动态 Authority 的一般解 |
| SharedPlans 区分局部知识、共同承诺与外包行动 | `VERIFIED_AT_ABSTRACT_LEVEL`。原论文摘要明确讨论部分知识、共同活动承诺和 contracting out。[paper record](https://jmvidal.cse.sc.edu/lib/grosz96a.html) | 支持“知道对方可能做什么不等于形成共同计划” | 不是当前 G1 状态机或现实效果的验证 |
| ANAC/GENIUS 处理已定义协议、域和偏好，并承认偏好的构造性 | `VERIFIED`。TU Delft 页面说明固定协议、deadline、域复杂度和偏好可在协商中变化。[ANAC](https://ii.tudelft.nl/nego/node/7) | 支持固定议题协商成熟，以及不能把所有意愿变化当作读取隐藏状态 | 不证明其能发现未知主体、未知角色或未知议题 |
| EDC 提供 Connector、Federated Catalog、Identity Hub、Registration Service | `VERIFIED`。[Eclipse EDC project](https://projects.eclipse.org/projects/technology.edc) | 支持已知数据资产的发现、受控交换和数据空间实现已有成熟组件 | 不证明具体部署闭合 G1/G2/G5/G6，也不证明合同执行、主体认领或 Acceptance |
| Catena-X 质量场景连接 OEM 现场数据与供应商生产数据 | `VERIFIED_AS_FIRST_PARTY_PRODUCT_CLAIM`。[Catena-X quality](https://catena-x.net/use-case-cluster/quality/) | 支持跨企业安全、及时数据交换已有现实产品/实现方向 | 页面是运营方说明，不是独立效果评估；不能据此宣称根因、整改权威和最终验收端到端闭合 |
| 私有估值下中心机制仍有结构性限制 | `VERIFIED_WITH_NARROW_SCOPE`。Myerson–Satterthwaite 原论文只针对一买一卖、独立私有估值等假设，证明无外部补贴下 ex-post 效率的一般不可能性。[original abstract](https://www.sciencedirect.com/science/article/pii/0022053183900480) | 反驳“聪明中心自动消除自愿参与与私有信息矛盾” | 不能外推为所有多主体形成任务都不可能 |
| 五家中介机构大量依赖人工，并同时遇到社会与技术冲突 | `VERIFIED_AS_SMALL QUALITATIVE STUDY`。论文采用五家机构访谈/材料分析，并对其中一家做一周田野观察。[original article](https://link.springer.com/article/10.1007/s10606-025-09534-0) | 支持人工中介是实质性机制基线，而非只做 matcher | 不能估计中介效果规模、一般成功率或相对成本 |

### Plausible：合理，但来源不足以完成因果或覆盖主张

- **KPD 是 strong-center positive**：若“strong center”指中心注册/匹配与本地医院、
  捐献者权威共同组成的制度，成立；若指全信息中心独自持有 truth、授权和接受，则不成立。
- **成熟组合可以解决大量闭合任务**：上述组件共同说明这很可信，但仍需在同一冻结任务上
  运行组合，而不是由组件清单推出端到端闭合。
- **全信息中心在合法集中时可能更简单、更强**：可作为待运行强基线和上界；“通常支配”
  仍是待检验命题，来源没有给出跨任务比较。
- **EDC/Catena-X 很接近已知资产的安全执行**：可作为工程假说；不能从项目能力页面直接
  推出 Authority、Effect、Adoption、Acceptance 和恢复闭合。

### Overstrong：当前来源不能支撑

- “对已知数据资产、已知参与者、已知用例、已知合同条款，不存在明显的新协议空缺”：
  组件存在不等于端到端语义、实施质量、互操作性、撤回和恢复已经闭合。
- “肾脏配对捐献把原本不存在的路径形成出来”：官方来源证明交换机制确实运行，但
  “路径在 \(S_0\) 是否不存在”取决于冻结的 \(Q\)、证据和语义等价定义，不能从案例叙述
  直接得出。
- “现有组合已是 G1 最强端到端解”：这是设计候选，尚无同任务、同 access、同 Authority、
  同成本的本地运行。
- “全信息强中心全面更好时就应直接采用”作为决策原则合理；“它会全面更好”不是来源事实。

### Unresolved：需要重建 claim-source 绑定

`G1-return.md` 是格式化转录，网页来源徽标已移除；`G1-sources.md` 只保存 URL，未保存
逐主张映射、引用文本或返回哈希。因此以下内容不能从当前 bundle 独立重建：

- τ-bench 的动态榜单数字与时间点；
- NKR 2025 年 `1,815 / 28%` 数字（当前来源表没有 NKR 链接）；
- “HRSA 每年数百例”的精确来源位置；
- 每个来源到底支持 Pro 正文中的哪一句强主张。

这些不一定错误，但在补回一对一 claim-source mapping 前只能是 `UNRESOLVED`。

## 二、五类标签与 \(t_0\) 回放审计

### 1. 单标签分类会丢失一条路径内的多次状态变化

同一 episode 可以同时发生：

```text
INDEX_CANDIDATE
→ MODEL_REFRAMING
→ ACTIVE_REVELATION
→ TERM_CHANGE
→ AUTHORITY_GRANT
→ CAPABILITY_CREATION
→ CLAIM / AUTHORIZATION / EFFECT
```

例如模型从索引生成候选，查询获得 owner witness，再通过新条款变得可认领。把整个 episode
压成 `INDEX_HIT` 或 `JOINT_ACTIONABILITY_INCREASED` 都会丢失组件责任。应按
`candidate generation / qualification / claimability / authorization / execution` 分段、
多标签记录，而不是互斥单标签。

### 2. `INVALID_SUCCESS` 的判定顺序错误

Pro 伪代码先判断 `INDEX_HIT` 与 pre-existing path，再判断 `INVALID_SUCCESS`。因此：

> 公共索引存在正确方案，但协调器冒充安全 Authority、越权披露或删除必要主体。

当前顺序可能先返回 `INDEX_HIT`，使一个无效世界获得正标签。所有 positive label 之前必须
先跑独立 hard gate：

```text
same target / same Q / all necessary principals / valid evidence
/ no authority substitution / no prohibited disclosure / no forged acceptance
```

未通过即只能是 `INVALID_SUCCESS` 或更精确的 invalid subtype。

### 3. `INDEX_HIT` 的“可直接推出”存在事后 oracle

若 evaluator 看见最终方案 \(p\) 后才判断“索引是否足以推出 \(p\)”，它实际上在问一个
未冻结求解器类别和计算预算的存在性问题。任何新组合都可能在事后被说成“索引里本来都有”。

可操作定义必须改成：

> 在运行前冻结的 index snapshot、语义等价、index-only baseline、预算和 deadline 下，
> baseline 是否实际输出并资格化了该 path class。

不能让 evaluator 用最终答案反向证明 index arm 理应找到答案。

### 4. `MODEL_HIT` 与 `ACTIVE_REVELATION` 不是互斥事件

模型可以先猜中候选，再由查询揭示承重事实。前者是 hypothesis provenance，后者是
qualification evidence provenance。只选一个标签会把“猜中但尚不可交付”提升为完成，或把
模型的真实候选贡献抹掉。

### 5. \(t_0\) 回放把 treatment 产物注入了 counterfactual

Pro 提议把“最终方案和最终允许使用的证据”注入克隆的 \(t_0\) 世界。这至少有三种泄漏：

1. 最终签名 witness、批准或 adapter 可能在 \(t_0\) 尚不存在，是实际 operator 的产物；
2. 该证据在 \(t_0\) 可能没有合法披露路径，回放绕过了当时的 policy/refusal；
3. 最终方案本身由实际交互生成，是 post-treatment variable。

于是同一例可以被双向误判：

- 把 \(t_1\) 新签署证据注入 \(t_0\)，本应是条件/资格形成的例子被归为
  `PREEXISTING_PATH_DISCOVERED`；
- 不重放渐进解释和信任建立，只给一次完整方案，主体因呈现方式拒绝，本来只是 clarification
  或交互协议差异的例子被归为 `JOINT_ACTIONABILITY_INCREASED`。

对于真人，记忆、顺序、信任和偏好构造还使“克隆同一主体”不可实现；同一人第二次回答不是
独立 \(t_0\)。

### 6. `JOINT_ACTIONABILITY_INCREASED` 当前仍是 oracle 标签

“变化来自可审计的理解、条款、关系、权限或新能力”只是类型清单。若相同 simulator 同时：

- 生成主体初始偏好；
- 定义交互后的偏好；
- 判断最终是否认领；
- 再给自己标注发生了哪种形成；

结果只是 fixture 作者的自洽，不是独立因果证据。至少需要：

- owner/world author 与方法实现者分离；
- evaluator 在 method 冻结前冻结；
- response function、allowed policy、语义等价和 \(Q\) 独立审计；
- operator removal、reversal 或 blocking；
- 随机顺序和 held-out worlds；
- 真人阶段使用平行受试者/随机化呈现，而不是同一主体事后回放。

### 7. `FAILED_OR_UNIDENTIFIED` 违反 V2 的保护性结果边界

它把合法 `Reject / Defer / Unknown / Protective Contraction / Clarification-only` 重新
压成失败。V2 明确要求这些状态保留独立价值；G1 还必须区分：

```text
UNEXPRESSED / UNKNOWN / UNWILLING_TO_DISCLOSE
/ CLOSED_SCOPE_ABSENT / POLICY_UNFINDABLE / EXPIRED
```

## 三、可执行的反事实修订

不要用一次“最终答案注入 \(t_0\)”决定全部因果归属。对每个 path class 分别运行：

1. `PUBLIC_BASELINE`：只给 \(t_0\) 公共材料；
2. `T0_LEGAL-EVIDENCE-PATH`：允许走 \(t_0\) 已存在的合法查询/验证路径，不注入未来 receipt；
3. `FINAL-PROPOSAL-ONLY`：只给最终提案，证据限于 \(t_0\) 当时合法可用版本；
4. `REMOVE_OPERATOR_k`：逐项移除、反转或阻断解释、条款、权限、adapter、资源、关系等
   operator；
5. `FULL_ACTUAL_TRACE`：实际完整过程；
6. `INVALIDITY_GATE`：独立检查目标、必要主体、Authority、披露、证据、Acceptance。

返回事件向量而非一个标签：

```text
candidate_source
fact_existed_at_t0
legal_evidence_path_existed_at_t0
qualification_created
understanding_changed
terms_changed
authority_changed
capability_changed
claimability_changed
validity
```

这既能吸收 Pro 的洞见，也不会覆盖 V1 的 `S0 / Q / operator necessity`。

## 四、30-episode、VPDR 与公平性

### Verified / useful

- 每类 5 个、共 30 个 episode 足以做分层机制 pilot；
- 相同目标、必要主体、截止时间、资格规则和 Acceptance 是必要条件；
- 披露不能只数 bytes，误唤醒不能把合法拒绝算作算法失败；
- human broker、成熟组合和 strong center 都应是正基线；
- `CANDIDATE → claim → authorization → effect → acceptance` 不应合并。

### Overstrong / biased

#### 1. VPDR 的分母对开放世界并不可完整观察

Pro 提议：

```text
full-information solver
+ all systems' candidate union
+ hidden planted paths
```

作为近似真值。这会导致：

- 新增更强 arm 会改变所有旧 arm 的分母；
- 某 arm 贡献的新路径反而降低自己的 recall；
- 全信息 oracle 仍受冻结 schema 限制，不是真正开放世界真值；
- 合法拒绝下不可发现的 \(L_t\) 路径被计为方法漏检。

应先做独立 discovery/build 阶段，去重、资格化并冻结 benchmark，再对 held-out methods
评分；同时报告两个分母：

```text
structural recall = discovered / L_benchmark
actual-policy recall = discovered / D_actual
```

其中 \(D_{actual}\) 是在实际 policy、allowed actions、budget 和 horizon 下存在合法 evidence
path 的机会。`L-D_actual` 单列 policy-unfindable / indistinguishable / refused，不奖励越权。

#### 2. 全信息中心不是公平 arm，只是技术上界

Pro 的 `C` 获得全部真实状态，而 B3/H 只有披露预算。这能回答信息上界，不能回答算法或组织
形式优劣。至少拆成：

- `C-RAW-UPPER`：合法全信息上界，支付完整 exposure/participation cost；
- `C-EQUAL-ACCESS`：与 B3/H 相同 observation、local oracle、预算和 deadline 的中心编排；
- `MATURE-COMPOSITION`；
- `H-EQUAL-ENVELOPE`：同任务、action API、deadline 和披露规则的人类中介。

中心“给定全员已加入的条件表现”与“加入、退出、持续更新后的生态表现”必须分表，不能让
合成 Agent 的固定参与率冒充现实信任/加入效果。

#### 3. 人类公平性不只等于披露预算

人类拥有常识、自由语言和隐性 schema 修订能力，也支付更多时间、注意和不可复现成本。
应冻结允许动作、可访问 owner、deadline 和敏感度预算，同时分别报告人类分钟、等待、
重复询问、治理和知识迁移；不能强迫人类只用机器的预制菜单，也不能让其无限追问。

#### 4. 5×6 类只支持分层结果，不支持现实总比例

每类固定 5 个会人为保证 5 个“认领形成”和 5 个“无效成功”。可报告每类通过/失败和
macro average，不能宣称真实任务中形成占比、总体成功率或普遍性能。类别生成者不得向 arms
暴露类型；episode 需要随机顺序、held-out skin 和 finalized-population receipt。

## 五、与本地 G1、Problem v1/v2 的关系

### 直接冲突

1. **G1 输入边界**：Pro 从“模糊价值目标”启动，并让系统生成 query；ACTIVE V2 明确说
   上游怎样感知、推断、编译或生成 Intent 不属于当前研究对象。当前本地 G1 也已把输入限定为
   `IntentAtCoordinationInterface`。应拆成：
   - G1：Intent 已进入接口后的未声明互补关系发现；
   - adjacent upstream experiment：模糊事件/目标怎样生成 Intent。
   若要合并，需显式修改问题，不得由 Pro 返回静默改写。
2. **成功层级**：Pro 的“可认领共同可行动性”只要求非绑定条件性意愿和合法后续授权入口；
   V1 的完整 formation 还要求 Authority、Commitment、Execution、Effect、Adoption、
   Acceptance、Settlement 等独立证据。该指标可作为 G1→G2 handoff 中间态，不能冒充
   Problem v1/v2 完成。
3. **分母**：Pro 主 VPDR 使用 full-information 路径；本地 G1 已要求
   \(L_t \supseteq D_t^{actual} \supseteq H_t\)，主 recall 对 \(D_t^{actual}\) 计算。应保留
   local 分层，而不是退回单一全信息分母。
4. **非成功状态**：Pro 的 `FAILED_OR_UNIDENTIFIED` 与 V2 保留 Clarification、
   Protective Contraction、Reject、Defer 的要求冲突。

### 可吸收

- 六类 Authority（事实、披露、协商、承诺、执行、接受）可进入 task instrument，但归属和
  精确语义仍应与 G5 对齐；
- KPD 可成为强中心/成熟制度的正例，但应标为“中心匹配 + 分布式权威 + 人类制度”；
- “候选生成—隐藏事实验证—条款形成—受控交换—人类制度”五闸门比按技术名堆栈更有判别力；
- structural indistinguishability 与本地 zero-disclosure paired world 完全一致；
- 三个真实任务适合做 task skin，但临床试验/KPD 涉及真人权利，只能先做历史数据或
  合成/回放设计，不能从本地 pilot 推出现实有效；
- \(t_0\) 反事实方向值得保留，但必须采用分段 operator ablation 和合法证据路径，不采用
  treatment-derived final evidence 一次性注入。

## 六、最强反例

设某主体只有在以下真实过程后才条件性认领：

1. 先获得低敏感度解释；
2. 验证对方履行了一个小型可撤销步骤；
3. 因该步骤形成新的可验证信任/补救条件；
4. 再由原 Authority 签署新条款。

把最终条款、最终 witness 和最终完整提案直接放回 \(t_0\)：

- 若允许使用 \(t_1\) witness，回放窃取了 operator 产物，可能误判为 pre-existing；
- 若不重放渐进过程，主体可能因信任尚未形成而拒绝，分类器又可能把呈现顺序误判为形成；
- 若最终提案在 \(t_0\) 根本不允许向该主体披露，回放违反 disclosure Authority。

因此当前回放不能唯一地区分“发现”“解释”“验证”“关系/条款形成”和“能力创建”。这不是
模型性能问题，而是 counterfactual treatment 定义不闭合。

## 七、进入实验前的最小修订门

1. 冻结 G1 输入为 `IntentAtCoordinationInterface`；上游 vague-goal 另立相邻 slice。
2. positive label 前先执行独立 `INVALIDITY_GATE`。
3. 单标签改为分阶段事件向量；`MODEL_HIT` 与 `ACTIVE_REVELATION` 可同时成立。
4. 冻结 index-only baseline、语义等价、计算预算和 deadline，禁止事后“可推出”。
5. \(t_0\) 回放只允许当时合法可获得的 evidence path；新增 operator removal/reversal。
6. world/evaluator author、arm implementer 和 scorer 分离，使用 held-out、随机顺序和独立审计。
7. 同时报告 `L_benchmark` 与 `D_actual`；不可区分/拒绝不计 actual-policy 漏检。
8. 拆分 `C-RAW-UPPER` 与 `C-EQUAL-ACCESS`，给 human 相同 action envelope 而非只给相同
   bytes。
9. 30 个 episode 只做 category-stratified pilot；不生成现实频率或跨域结论。
10. 补回逐主张来源位置和 raw-return receipt；在此之前来源只能支撑本审计列出的窄主张。

在这些修订完成前，本报告不建议把 Pro 的“最强现有解”“一般未解决”或 30-episode
evaluator 写入任何正式机制状态。它们是高价值候选和实验输入，不是运行结果。
