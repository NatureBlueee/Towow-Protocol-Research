# ChatGPT Pro cohort 001：七线独立审计综合

日期：2026-07-29  
状态：`SEVEN RETURNS / SEVEN AUDITS / NO FORMAL PROMOTION / NO COVERAGE CLAIM`

## 一、结论

七条 ChatGPT Pro 会话都产生了有价值的候选理论、成熟组合、强反例和实验设计；七份独立审计
也都给出同一处置等级：

```text
REVISE_BEFORE_EXPERIMENT
```

这不表示 Pro “答错了”，也不表示七条线没有进展。真正发生的进展是：

- 成熟组件、强中心、人工制度和通用模型重新成为可以获胜的正基线；
- 多个旧 evaluator 中的免费 oracle、同源 alias、post-treatment evidence、目标偷换和
  规模幻觉被具体定位；
- 七条线分别得到一组更小、更有区分力的下一实验；
- 当前没有证据要求发明七个新机制，也没有证据证明一个成熟组件清单已经端到端闭合。

当前最窄判断：

```text
MATURE_COMPONENT_CAPABILITIES = POSITIVE_SCOPED
MATURE_END_TO_END_COMPOSITION = UNRESOLVED_NOT_RUN
LAWFUL_STRONG_CENTER = POSITIVE_BASELINE_AND_MAY_WIN
GENERAL_MODEL = USEFUL_CANDIDATE_PLANNER_OR_INTERPRETER
HUMAN_INSTITUTION = POSITIVE_BASELINE_AND_MAY_WIN
NOVEL_PROTOCOL_NECESSITY = NOT_DEMONSTRATED
FULL_V1_V2_SOLUTION = NOT_MEASURED
NEXT_ACTION = SMALL_ORACLE-SEPARATED_DISCRIMINATORS
```

## 二、七条线分别留下了什么

| 线 | 可保留的核心 | 审计否定或收窄的部分 | 下一项高区分实验 |
|---|---|---|---|
| G1 | 候选生成、资格化、主体认领、授权与执行必须分段；KPD 等封闭制度说明中心匹配+本地 Authority+人工制度可以形成真实正例 | 互斥五标签、先判正例后判 invalid、最终方案/最终证据注入 \(t_0\)、全信息单分母、把 vague goal→Intent 偷混入 V2 | 8–12 world provenance discriminator：合法 \(t_0\) evidence path、operator removal、事件向量、`L_benchmark/D_actual` 双分母 |
| G2 | 关系不是一份文本；逐条款构成规则、精确版本、独立 owner act、撤销与依赖是有效表示；有共同制度时成熟平台可能完整解决 | 逐条款规则不等于完整 G2；本地 `24/24` 由单 broker 持有 owner key，只证明签名证据验算；2×2 把 Authority topology 与 state placement 混在一起 | 12 world owner-evidence/open-schema discriminator，分别测 constituted/understood/claimed/authorized/activated |
| G3 | “当前合格执行路径”与“改变条件的形成轨迹”应分层；封闭动作模型下成熟 planner/workflow/IAM 可能完整解决 | “无直接路径”不等于完整 policy closure UNSAT；`C=SAT,N=NEW_TOKEN,E=SAME` 说明现实条件可新形成而旧 policy 已可达；开放 inventory 不能被判 bounded-unreachable；causal witness 可能读取 post-treatment oracle | 6 world 量词 discriminator，严格区分 direct path、旧 closure UNSAT、新 token、actual-policy miss、open-inventory Unknown、new episode/substitution |
| G4 | capability/history/readiness/IAM/reservation/attestation/Authority/recovery 彼此不蕴含；可依赖性可能通过 current query、commitment、fence 和 readback 被构造 | 把“首次成功兑现”换成“有界权威终态”；成熟组合调用被写成免费 primitive；初始 packet 相同不足以证明交互系统不可区分；`2160/17280` 没有信息增益论证 | 12–20 world 双结果实验：`Y_success/Y_resolution`、`P0/I/P1`、passive/active/hard pairs、真实 recovery/readback |
| G5 | identity、Mandate、Authority、permission、stance、reservation、commitment、Standing 不应互相升级；exact binding、native outcome、current head、target fence、migration loss 都是重要检查面 | typed evidence 与四值不是 Authority truth；registry 不能免费拥有 current state；commit-time read set 不产生跨 Authority 原子快照；统一 IR/迁移成功不证明语义等价 | 五类小实验：Authority crossed pair、native outcome translation、cross-owner race、fence-to-Effect、migration+Standing holdout |
| G6 | Attempt/Effect/Adoption/Acceptance/Settlement 不是固定五级 ladder，而是 episode-relative roles；workflow/event/receipt 不蕴含现实 Effect | 单一 role+单 typed DAG 又压平 raw occurrence、权威资格、控制与义务；`QualifiedEffect=false` 不能隐藏未经授权但真实发生且需恢复的 Effect；owner ledger 不是 truth API；readback 不自动证明 transition/causality；Settlement 不是 bool | 12 paired worlds，分别评分 raw occurrence、qualification、Authority、causal edge、wrong object、Adoption、Acceptance disagreement、settlement phase/finality、read skew |
| G7 | durable execution 不蕴含 durable legitimacy；局部重开应沿失效 justification 的因果锥；私有撤销不可观察时存在安全—liveness 边界 | 五态只能作为 Authority observation，不能承担完整 recovery/migration 控制；readback/fence/Acceptance/capsule 都是有界组件或待检验提案；migration capsule 字段齐全不等于 runtime 语义可移植 | 12–20 world T6 orthogonal replay：Effect phase、epoch、split-brain、hidden edge、planned/crash migration、reconciliation、Context portability |

逐线证据：

- [G1 返回](./G1-return.md) / [G1 审计](./G1-AUDIT.md)
- [G2 返回](./G2-return.md) / [G2 审计](./G2-AUDIT.md)
- [G3 返回](./G3-return.md) / [G3 审计](./G3-AUDIT.md)
- [G4 返回](./G4-return.md) / [G4 审计](./G4-AUDIT.md)
- [G5 返回](./G5-return.md) / [G5 审计](./G5-AUDIT.md)
- [G6 返回](./G6-return.md) / [G6 审计](./G6-AUDIT.md)
- [G7 返回](./G7-return.md) / [G7 审计](./G7-AUDIT.md)

## 三、为什么“这些技术大家都有”，问题仍然没有被证明解决

最重要的答案不是“别人缺少通爻”，而是下面四种情况长期被混在一起。

### 1. 局部 primitive 已经很强，跨 primitive 的箭头尚未成立

现有系统分别能做：

- catalog/search；
- planning/constraint solving；
- IAM/policy；
- signature/credential；
- transaction/outbox/workflow；
- reservation/lease/fence；
- event/audit；
- target readback；
- CLM/人工审批；
- payment/settlement rail。

但完整任务要求的是：

```text
未表达需求或局部事实
→ 合法发现/澄清
→ 主体分别理解并认领同一精确版本
→ Authority/permission/resource 在使用点仍成立
→ exact operation 被目标端执行
→ Effect 由目标域重建
→ Adoption/Acceptance/Settlement 由各自 owner 判断
→ 漂移后只重开失效部分并可迁移
```

每个箭头都可能跨越不同 owner、状态源、时间窗口和失败域。组件存在不能证明这些箭头已经
无损闭合；反过来，若一个成熟平台或强中心已经把这些箭头真实闭合，它就是完整正解，不需要
另造协议。

### 2. 很多“解决方案”把最难条件放进了输入

常见伪闭合是：

- 先给 query、Agent Card、完整 dependency graph，再证明搜索成功；
- 先给 `relation_valid/material_change`，再证明关系构成；
- 先给 complete inventory，再证明 bounded-unreachable；
- 先给 `head_current/fenced/authoritative`，再证明可靠依赖；
- 先给 owner truth/readback，之后证明 Effect 和重开正确；
- 让 source runtime 的私有状态被 grader 完美翻译成 migration capsule。

这不是这些技术没价值，而是评测只验证了“答案接线正确”，没有验证答案怎样在合法信息、
Authority、成本和故障条件下被取得。

### 3. 有些 residual 不是计算问题，而是信息、权威或制度条件缺失

若两个世界在完整允许交互中都产生相同合法 observation，但私有 Authority 真值相反，任何
模型、中心或多 Agent 共识都无法同时获得零误继续与满召回。能改变结果的只有：

- 新的合法观察；
- 新的披露；
- owner 作出的新 commitment；
- target 执行的 fence/conditional write；
- 新的制度委托；
- 降低承诺强度；
- 接受 `Unknown/Refused/Exit`。

这类边界不会因为再加一个消息格式消失。若成熟人工制度、保险/赔偿、保守退出或合法委托
已经最好地解决它，也应直接采用。

### 4. “可闭合”与“已经闭合”之间缺少同任务运行

Pro 七线都能给出一个在强前提下看似完整的成熟组合；审计一致指出：

```text
component-complete design
≠ executable composition
≠ same-task held-out pass
≠ real owner acceptance
```

当前工作最需要补的不是更多概念，而是让强中心、成熟组合、人工制度和候选方案在同一 frozen
task、同一 lawful access、同一 Authority 与成本分母下实际运行。

## 四、跨线可共享的实验纪律，不是统一理论

七条线仍保持独立对象，但可以共享以下防伪纪律：

1. **三个强中心 strata**
   - `RAW/FULL-INFORMATION UPPER`：技术上界，不作公平算法比较；
   - `EQUAL-PERMISSION CENTER`：与其他臂同 API、Authority、预算、时延；
   - `LEGITIMATELY DELEGATED CENTER`：主体确实委托的场景，可完整获胜。
2. **owner truth 不由 controller 生成**
   - owner service、method、grader 使用不同 store/key/implementation；
   - controller 只能查询、验证、传输或派生。
3. **初始 packet 相同不等于完整不可区分**
   - passive、active、full-interaction-equivalent paired worlds 分开。
4. **观察与改变世界分开**
   - 查询、解释、形成 commitment、reservation/fence、执行和 readback 分段记账。
5. **原始发生与规范资格分开**
   - 未授权 Effect 仍是真实 occurrence，也可能需要恢复；
   - Authority/CountsTowardQ/Acceptance 不能删除历史发生。
6. **状态不要压成单枚举**
   - normative stance、knowledge、refusal、freshness、channel outcome、Effect phase、
     migration phase 和 conflict/equivocation 正交保存。
7. **小型高区分运行先于规模**
   - 先过 truth-copy、alias、wrong-object、stale-head、post-treatment、field-drop 等 mutation；
   - evaluator 无分辨力时，扩大样本只会扩大假证据。
8. **现实取材不等于现实证据**
   - 支付、临床、制造、部署等当前是 synthetic task skins；
   - 只证明理论/模拟边界，不冒充真人、生产或长期净值。

这些只是共同实验纪律。它们不能被包装成一个新的万能协议或统一事实对象。

## 五、当前第二批执行

第二批 Codex CLI 已根据七份审计分别启动独立主会话，并要求每个主会话实际使用 A/B/C
内部子研究者承担问题重建、实现与攻击：

- G1：`wave-011-g1-provenance-discriminator`
- G2：`wave-011-g2-owner-evidence-open-schema`
- G3：`wave-011-g3-quantifier-discriminator`
- G4：`wave-011-g4-dual-outcome-discriminator`
- G5：`wave-011-g5-authority-conformance`
- G6：`wave-011-g6-role-causality-discriminator`
- G7：`wave-011-g7-orthogonal-replay`

每条线只在自己的目录写入，禁止修改 `NOW.md`、`PROGRAM.md`、LineContract 或正式机制状态。
产物只有通过各自独立 oracle/alias/mutation 门后，才进入下一次跨线综合。

