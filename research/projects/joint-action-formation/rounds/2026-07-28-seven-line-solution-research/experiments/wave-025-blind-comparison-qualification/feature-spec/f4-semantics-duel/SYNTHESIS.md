# Wave025 C01/F4 semantic duel 综合

> 日期：2026-08-01  
> 状态：`LOCAL_SYNTHETIC_SEMANTIC_DISCRIMINATOR_COMPLETE / F4 CANON UNDECIDED / NO CURRENT F4 MODIFIED`  
> 作用域：只比较 C01/F4 的候选语义与职责边界；不是 `MODEL-INPUT` canon，不是 actual D0/D1、G、T 或 3200 结果。

安全边界：本轮没有访问网络、容器、真实权限，也没有测试隔离绕过或安全攻击面。任何 actual isolation、
zero-ingress、capability 或 attack-surface 结论均标为 `SECURITY_REVIEW_REQUIRED`，由安全人员另行验证。

## 1. 结论先行

这轮没有得到一个可以无条件晋升为 F4 canon 的赢家。

三个候选各自解决了不同问题：

- `STRICT_POSITIVE_AND` 只稳定恢复普通 `A AND B`；
- `SIGNED_LITERAL_SINGLE_PATTERN` 还可恢复 `A AND NOT B` 这类“一个二位状态对其余三个状态”的模式；
- `FULL_2BIT_OBSERVED_MAPPING_R_FALLBACK` 是三者中唯一恢复 XOR 的候选，在本套合成任务上覆盖最高。

但“合成覆盖最高”没有解决选择风险。三者都在 calibration 完美相关的 spurious pair 与真实 pair
之间冻结了错误 pair，calibration BA=`1`、holdout BA=`0.5`；都在每个预测类 support 恰好为 `5`
时接纳了一个 holdout 消失的关系；也都无法从同一份 calibration 判断未见 `01` 状态在新世界里
应是 R 还是 S。full mapping 的更大表达能力因此既是能力，也是更大的候选/过拟合面。

第四个竞争项 `NO_F4_IN_C01 + C04 owns interactions` 仍然成立，而且不应因 F4 名字已经存在就被排除。
在本 fixture 上它把 C01 的 F4 候选与 pair labeling 空间降为 `0`。AND、signed pattern 与 XOR 的真值表
都可由深度 `2` 的二叉树表示，落在已登记 C04 `maximum_depth=3` 的表达能力上界内；但这只是表示
上界，**不是**当前 C04 已学到、已冻结或已通过 holdout。C04 的 machine semantics、输入字节、tie、
OOV、failure 与真实运行没有在本轮闭合，所以不能用这个上界冒充现成替代。

当前最稳妥的研究状态是：

```text
KEEP_CURRENT_V3_F4_UNAVAILABLE
DO_NOT_REINSTATE_V1_BOOLEAN_LOOKUP_UNDER_OLD_NAME
DO_NOT_FORCE_F4_TO_REMAIN_IN_C01
DECIDE_AFTER_ACTUAL_D0_D1_AND_C04_RESPONSIBILITY_EVIDENCE
```

这不是 canon 删除决定。它是“现有证据不足以补义，而无 F4 的职责分配仍是活候选”。

## 2. 历史上 F4 实际承诺了什么

### 2.1 最初登记的问题

当前 `FEATURE-SPEC.json` 把 C01 定义为 deterministic rule scan，F4 只给了名字：

```text
two_token_conjunction_from_TOP256_CALIBRATION_SUPPORT_TOKENS
```

共同合同还写了：

- calibration row-presence support 排前 `256` 个 token，再形成 pair；
- minimum total calibration support=`10`；
- minimum per predicted class support=`5`；
- 先最大 calibration balanced accuracy，再最小 rule complexity，再最小 UTF-8 rule bytes；
- 同一冻结 rule 必须在 calibration 与 holdout 两阶段、R/S 两类 recall 都为 `1` 才算 stable；
- holdout 不重选。

名字没有唯一决定：literal 是否允许否定、match 哪一类、nonmatch/fallback 是什么、一个 predicate 还是
rule set，以及完整 `00/01/10/11` lookup 是否属于“conjunction”。因此当时不是“实现细节没写完”，
而是同一个 family name 对应多个不同假说空间。

### 2.2 漂移和失败

`MODEL-INPUT-V2S-PROPOSAL-A-REDTEAM.md` 首先用 AND、XOR、support 与 OOV 反例指出 C01 只有矩阵，
没有 detector 语义。随后 minisuite V1 为每对 token 学习完整 `00/01/10/11 -> class` mapping，P6 XOR
因此恢复；独立红队证明这不是已登记 two-token conjunction 的机械实现，而是语义替换。把 F4 限成
普通 positive AND 后，P6 只能达到 BA=`0.75`。

V2/V3 没有继续为旧名字辩护：它删除 Boolean lookup，把 F4 改成
`REJECTED_UNDERDETERMINED_NOT_EXECUTED`。当前 V3 contract 明列四项未决：positive/negated literal、
class orientation/fallback、单 predicate/rule set、full lookup 是否禁止；当前 V3 results 中 F4 对所有
case 的 generated/eligible count 都是 `0`。

因此历史链是：

```text
含糊登记
  -> V1 自行补成 full 2-bit lookup，XOR 假装成既有 F4 胜出
  -> 红队拒绝语义替换
  -> V2/V3 删除补义并保持 F4 unavailable
```

本 duel 不把这条负结果抹掉，也没有修改旧 F4。

## 3. 本轮冻结的四个竞争对象

### 3.1 三种可执行 F4

| 候选 | 一个 pair 的语义 | 每 pair 规则/容量 | 未见 pair state |
|---|---|---:|---|
| strict positive AND | 只测 `11`；match 一类，其余状态另一类 | 2 rules | 没有专门 fallback，统一走 nonmatch |
| signed-literal single pattern | 任选 `00/01/10/11` 一个状态；该状态一类，其余三状态另一类 | 8 rules | 没有专门 fallback，统一走 pattern/nonpattern |
| full 2-bit observed mapping | 每个已见状态取 calibration 多数类，tie=R | 最多 16 labelings；实现每 pair 生成 1 个 learned mapping | 固定 R，不重选 |

所有 family 使用同一 calibration/holdout rows、同一个 label-free top-token universe、同一 support 下限和
同一 BA→complexity→semantic rule bytes 排序。tie 使用不含派生 hash/length 的语义 rule bytes，避免
hash 元数据反过来决定选择。

注意 historical support 的精确含义：这里忠实使用“每个**预测类**至少 5 rows”。因为三种规则都不
abstain，total support 永远等于 40，`>=10` 在本任务里不筛任何候选；它不是 pair 共现 support、目标
state support，也不是正确预测数。这是一个重要语义缺口，而不是无关命名问题。

### 3.2 无 F4 的职责分配

`NO_F4_IN_C01 + C04 owns interactions` 不产生一份假 C04 分数。它只冻结两项可检查判断：

1. C01 pair candidates 与 F4 rule space 都是 `0`；
2. AND、signed pattern、XOR 三个完整二位 truth table 的最小二叉树深度均为 `2`，所以在 C04
   `maximum_depth=3` 的**表示上限**内。

这一路径可能漏掉所有 F1/F2/F3 不能表达、而 C04 又尚未闭合或未被注册负责的 interaction。它只有在
C04 machine semantics 完整冻结、相关攻击预先登记到 C04、并且 secondary detector 不被用来事后救
失败 primary 时，才是完整职责迁移。

## 4. 机器结果

完整逐 case 结果在 `RESULTS.json`。摘要如下：

| 候选 | stable cases / 10 | mean holdout BA | 本 fixture conceptual rule space | 实际 generated | selected rule bytes |
|---|---:|---:|---:|---:|---:|
| strict positive AND | 2 | 0.640 | 30 | 30 | 243–249 |
| signed-literal single pattern | 3 | 0.675 | 120 | 120 | 253–259 |
| full 2-bit mapping | 4 | 0.700 | 240 | 15 learned mappings | 254–270 |
| no F4 in C01 | 当前不评分 | 不适用 | 0 | 0 | 0 |

full mapping 的 `15 generated` 与 `240 conceptual` 不矛盾：实现对每个 pair 从 calibration 生成一个
多数类 mapping，但当四个 state 都可能出现时，其假说容量上界仍为每 pair 16 种 labeling。

若 top-token 数真的达到 `256`，pair 数是 `32,640`：

| 候选 | C01 pair candidate / labeling 上界 |
|---|---:|
| strict positive AND | 65,280 |
| signed-literal single pattern | 261,120 |
| full 2-bit mapping | 32,640 learned mappings；522,240 conceptual labelings |
| no F4 | 0 |

这些是规则空间，不是 wall time、内存或实际 eligible 数；actual-shape 成本仍未测。

## 5. 反例真正区分了什么

### 5.1 AND、negated pattern、XOR

| case | strict AND | signed pattern | full mapping |
|---|---:|---:|---:|
| AND | 1.00 | 1.00 | 1.00 |
| `A AND NOT B` | 0.65 | 1.00 | 1.00 |
| XOR | 0.75 | 0.75 | 1.00 |

这证明三者不是同一算法的不同写法。strict AND 的现实主张最窄；signed pattern增加 absence；full
mapping才增加“两个不相邻 state 同类”的能力。

它没有证明真实 D0/D1 需要后两种能力。当前 D0 design candidate 明写 primary candidate rule 是
`SINGLE_EXACT_CATEGORICAL_TOKEN_PRESENCE`；D1 若正式绑定 one atom per role 且 cross-phase stable，
同样由 F1 足够。D1 的这个稳定前提目前没有被 bound public registration 证明，actual D0/D1 也都未跑。

### 5.2 spurious pair 与 tie

`D04_SPURIOUS_PAIR_TIE` 同时放入持续 pair `z-true-*` 与只在 calibration 相关的 `a-spur-*`。三者均有
多个 calibration BA=`1` 且 complexity 相同的候选，semantic bytes tie 最终冻结了字节更小的
`a-spur-a + a-spur-b`：

| family | BA/complexity tie 数 | calibration BA | holdout BA | pair |
|---|---:|---:|---:|---|
| strict | 6 | 1.00 | 0.50 | wrong |
| signed | 12 | 1.00 | 0.50 | wrong |
| full | 6 | 1.00 | 0.50 | wrong |

确定性 tie 只保证重放一致，不能区分 causal/persistent 与偶然相关。扩大 F4 不能修复这个选择问题；
需要来源登记、ablation 或新的独立 holdout。

### 5.3 support 4/5 边界

- 预测少数类 support=`4` 时，三者都没有 eligible rule，统一 fallback R，BA=`0.5`；
- support=`5` 时，三者都接纳 calibration-only pair，calibration BA=`0.625`，holdout BA=`0.5`。

因此当前 support 下限能挡住 4，但不证明 5 是稳定关系，也不约束 pair/state 本身的支持。若 F4 被保留，
应明确 minimum matched-state support、每 truth-table cell support、multiplicity correction 或 registered-pair
优先级中的哪一种才对应真实风险。

### 5.4 未见 state 不是可由 calibration 决定的事实

`D07` 与 `D08` 的 calibration bytes 完全相同，只改变 holdout 新 `01` state 的真实 class：一个世界
是 R，另一个是 S。

- strict AND 与 full mapping 对未见 state 走 R，所以 D07 BA=`1`、D08 BA=`0.5`；
- signed pattern 的 calibration 有两个观察上等价的写法，canonical tie 选择了对未见 state 走 S 的
  写法，所以 D07 BA=`0.5`、D08 BA=`1`。

没有哪个结果更“正确”。它说明 rule serialization 或固定 fallback 会替未观察世界作出政策选择。
选择 R、S、abstain、fail closed 或交给其他 detector，必须来自作用域/损失约束或新证据，不能从这份
calibration 推出来。

### 5.5 OOV 与未见 pair state 是两个问题

`D09` 的 40 个 holdout rows 都含 fresh OOV token，但冻结 pair 在这些 row 上呈现 `00`，而 `00` 在
calibration 已见。因此记录为：OOV rows=`40`、unseen pair-state rows=`0`、三者 BA=`0.5`。

这说明“token OOV”不能和“pair state 未见”共用一个含糊 fallback。unknown token被忽略以后仍会落入
一个已见 Boolean state；反过来，所有 token已知也可能组合出 calibration 未见 state。

### 5.6 role-null

`D10` calibration 对三者都为 BA=`1`，holdout 把相同 state 均匀分给 R/S 后三者均为 BA=`0.5`，没有
触发 `BA>=0.90` false recovery。这只是一个合成 placebo，说明 evaluator 能记录“正控 calibration +
role-null holdout”失败；它不是实际 T zero-ingress 或 role-null receipt。

## 6. 什么时候哪个现有语义是合理选择

| 任务条件 | 当前最简单有能力的候选 | 代价/漏项 |
|---|---|---|
| 威胁明确就是两个正向 atom 同时存在 | strict AND | 漏掉 absence 与 XOR；仍受 pair tie/低 support 影响 |
| 威胁明确是一个二位状态 vs 其余状态 | signed single pattern | 规则空间是 strict 的 4 倍；不能表达 XOR |
| 注册攻击允许任意二位 truth table，且四个 state 的 coverage/fallback 已冻结 | full mapping | 最大表达/过拟合面；未见 state 与 spurious pair 仍未解决 |
| C01 只负责 stable exact/count/numeric primary，interaction 统一由 tree 负责 | no F4 + C04 | 可去重并降到 0 pair rules；C04 未闭合时会留下真实能力缺口 |

因此允许三种最终结论，而不是只允许“选一个 F4”：

1. 某个成熟布尔语义在已登记任务条件下最好；
2. 按任务/攻击 registration 分流不同语义；
3. 从 C01 删除 F4，把 interaction 单一归属到 C04；
4. 真实数据仍不足，继续保持 Unknown。

本轮支持第 4 项，并把第 3 项提升为必须正面比较的候选；不支持直接晋升 full mapping。

## 7. 决策所需的额外真实 D0/D1 证据

要从 synthetic duel 进入职责或 canon 决定，至少需要以下 exact、fresh、pre-registered 证据：

1. **actual D0 分类器证据**：由获准的数据流程提供 fresh、cross-phase stable atom 的 actual V2S F04
   feature rows、labels 与 provenance binding；本研究侧只复算 F1 frozen rule、两阶段 classwise recall/CI、
   source ablation和role-null统计。真实 marker surface、role mapping secrecy、T zero-ingress与隔离均为
   `SECURITY_REVIEW_REQUIRED`。
2. **actual D1**：先由 public structural binding 证明 one atom per role 与 cross-phase stability；若实际
   不是这个粒度，重新问“primary 需要什么语义”，不能让 F4事后救一个设计不匹配的 control。
3. **pair population truth**：在安全人员批准并交付的去敏 feature rows上，复算实际 top-256 token、pair
   数、每 state/calibration class support、eligible
   数、最高 BA tie 数、selected pair来源与 exact bytes；不能只报 winner。
4. **OOV/state coverage**：D0/D1 fresh holdout 分别报告 token OOV 与 pair-state unseen rate，并预先冻结
   R/S/abstain/fail-closed 的损失含义。
5. **spurious rejection**：对获准的 selected pair 做 registered source attribution、组成 atom逐项 ablation、
   至少一个未参与选择的 fresh holdout；若同分 pair很多，需要 multiplicity-aware 决策，而不是只靠
   canonical bytes。真实注入面与隔离边界仍为 `SECURITY_REVIEW_REQUIRED`。
6. **interaction necessity**：给出至少一个 actual D0/D1 合法 attack，其中 F1/F2/F3 primary确实失败、
   pair interaction在独立 holdout持续，并且不是 metadata/role泄漏；否则 F4复杂度没有现实任务依据。
7. **C04 head-to-head**：先冻结 C04 matrix、split/leaf tie、missing/OOV、minimum leaf/gain、failure与
   resource语义，再在相同 calibration/holdout 和相同 preregistered attack 上比较 `F4 vs no-F4+C04`。
8. **成本**：在 actual shape 测 pair generation、rule bytes、peak memory、wall time与 artifact size；
   256-token公式只是上界，不是资源证据。

只有 actual F4-specific interaction 为 D0/D1 primary 所必需，且它相对 C04 有可验证的净价值，才有理由
把 F4 留在 C01。若 D0/D1 actual primary 都由 F1稳定恢复，而 interaction可由闭合后的 C04统一负责，
删除 F4 会是更简单、职责更清楚的成熟方案，而不是能力退步。

## 8. 复现与边界

```bash
python3 f4_semantics_duel.py --check
PYTHONPYCACHEPREFIX=/tmp/wave025-f4-duel-pycache \
  python3 -m pytest -q tests --disable-warnings
```

当前结果：`8 passed`；`RESULTS.json` byte-exact check通过，SHA-256
`06dc09a4f61266070ee38851e0c0316dc2f6623b9bd7a993c947daf8101239df`。

`RESULTS.json` 绑定当前 FEATURE-SPEC、两份红队、V3 contract/results、public control registration、
D0 design、fixture、实现与 tests 的 exact bytes。该 binding 证明本地结果对应这些材料，不证明它们已
被采用、已独立实现或已在现实控制上有效。

本 duel 在一个 Python 进程内清楚分开 selection、holdout prediction 与 label scoring接口，但没有建立
或攻击任何真实隔离边界；它不以“同进程没有偷看”作为研究结论。它的价值是固定语义差异、构造反例
和产生可重放统计，不是 blindness/security receipt。相关验证统一为 `SECURITY_REVIEW_REQUIRED`。
