# 任务真值校正 001

状态：`ACTIVE_CORRECTION`  
校正对象：`PROGRAM.md` 中 T1–T6 的可运行性与证据级别  
依据：第一波独立问题重建、原始任务来源逐字复核

本文件不改写已由用户决定绑定的 `PROGRAM.md`。它纠正启动后发现的任务真值错误；在本轮
产生任何覆盖率前，研究者必须同时读取本文件。

## 一、立即生效的校正

### T3 不能作为当前评分分母

`R7_RESOURCE_REQUEST.md` 的标题和正文是“R7 执行资源清单”。它列出真实实验未来需要的
案例数、Principal、adjudicator、追踪期、保密和 Owner 决策，但没有给出一个非标准资源
请求的 S0、角色、资源、动作或权威后置状态。

因此：

- T3 原状态 `ARCHIVAL_REAL_WORLD_TASK_DESIGN` 作废；
- 当前状态改为 `EXECUTION_RESOURCE_REQUIREMENT_ONLY`；
- PROGRAM 中 T3.R1–R8 只能作为未来任务设计要求，不能计算 coverage；
- 后续必须另找带完整前态的原始任务，或明确建立 `SYNTHETIC_TASK_SPEC`，不得借该来源
  冒充现实任务。

### T2 是答案泄漏型 replay，不能直接冷启动评分

“企业 AI 只读试点”确实是完整设计案例，但原文已经公开：

- v1；
- 数据方 counterconditions；
- sandbox probe；
- v2；
- Effect、Adoption、Acceptance；
- formation 判定问题。

它适合做机制解释和回归，不适合直接给求解方法后再评分。当前需从原始材料派生两个隔离面：

1. `T2-BLIND-INPUT`：只给各 Authority 的局部前态、允许披露和初始 v1，不给 counter、
   probe、v2 或裁决；
2. `T2-ORACLE`：由独立 evaluator 持有完整可行路径、权限、目标域和失败分支。

在盲化、哈希冻结和答案隔离完成前，T2 状态为 `ARCHIVAL_ANSWER_LEAKAGE_REPLAY`，不得产生
冷启动解题覆盖率。

### T1、T4、T6 的证据级别降级

- T1：`SYNTHETIC_TASK_SPEC`，尚无私有事件实例、latent opportunity truth 或在线 evaluator；
- T4：`SYNTHETIC_TASK_SPEC`，尚无各主体 hidden local spec、真实 feasible set 或错误无解真值；
- T6：`MUTATION_REPLAY_SPEC`，尚无独立 base-run 和 oracle dependency graph；
- T5：仍是 `NEGATIVE_CONTROL_SPEC`，但需先实例化平台基线和真实成本字段。

“高保真”“可 replay”只有在相应 world、truth、evaluator 和隔离运行形成后才能升级。

## 二、百分比的启动门

任何方法或组合不得报告 90%、95% 或其他 coverage，除非任务已经冻结：

- `S0`：干预前世界状态；
- `V0`：公平基线可见和可做的路径；
- `Q`：不可事后改写的合格结果谓词；
- 必要 Principal、AuthorityLocus、权限和拒绝；
- witness、authoritative readback 与接受来源；
- method 可见输入和 oracle 私有真值的隔离；
- 每个 requirement 的 `PASS/PARTIAL/FAIL/UNKNOWN` 判定语义；
- 至少一个用于揭露伪成功的 mutation；
- 输入、真值、方法返回和评分的哈希或等价不可混淆凭据。

统一 `PARTIAL=0.5` 只是计算约定，不代替“哪一半未解决”的逐项语义。关键底线失败仍然阻断
`SOLVED`，不能由平均分抵消。

## 三、七条母线的第一真值/evaluator

### E1 `HIDDEN-WORLD-DISCOVERY-ORACLE`

冻结私有事件时间线、latent complementary opportunities、Q 和逐方 disclosure policy。
离线 oracle 区分：

- `EXISTING_BUT_UNEXPRESSED`；
- `EXPRESSIBLE_WITHHELD`；
- `DISCLOSED`；
- `IMPOSSIBLE_UNDER_POLICY`。

在线方法只能看到被允许的事件和披露。测机会 recall、结构性漏检、误唤醒、发现时延、多轮/
多接收方累计泄露和 honest-undiscoverable 校准。

### E2 `PRIVATE-SPEC-RELATION-SEMANTICS`

方法只经 local oracle 访问各方 hidden spec/action set；独立 truth 持有全部私有约束、
authority scope、可行 relation equivalence classes 和冲突。测可执行满足、provenance、
局部异议、material mutation、一致性、错误无解和 disclosed bits；表示格式不进入真值。

### E3 `CAUSAL-REACHABILITY-GRAPH`

冻结 transition system、S0、Q、V0、authority 和隐藏 operator；oracle 检查 intervention
前后是否存在 Q-path，并运行 remove/reverse/block 消融。成对覆盖 discovery-only、
condition-created、problem-rewritten 和 impossible。

### E4 `PROSPECTIVE-HOLDOUT-RECEIPT`

行动前冻结 capability claim、confidence、expiry 和 prediction horizon。隐藏 holdout 注入
版本、权限、资源、并发、随机失败和恢复。测 selective risk、calibration、false commit、
false reject、abstention coverage 和 same-identity recovery；全部 UNKNOWN 不能获胜。

### E5 `AUTHORITY-TRANSITION-MODEL`

独立 oracle 持有 Principal/locus/delegation/mandate/versioned stance/reservation/standing
状态机与禁止蕴含。模型检查最小 trace，测 false allow/deny、stale execution、illegal
inference、double reservation、challenge preservation 和 execution-time TOCTOU。

### E6 `AUTHORITATIVE-POSTCONDITION-SIMULATOR`

event-sourced target world 保存 operation、actor 和 causal id；注入预存在状态、他者并发、
延迟/乱序/重复、partial adoption、dispute/retract。oracle 独立给出 Attempt、Effect、
Adoption、Acceptance、Settlement 五层真值；候选只获得配置允许的 authoritative readback。

### E7 `DEFEATER-CLOSURE-MUTATION`

oracle 持有独立依赖图，包括 cycle、隐藏边和不可逆 in-flight action；逐个及组合注入模型、
Mandate、证据、账号、目标和依赖变化，给出 ground-truth affected closure 与 safe action。
测 unsafe continuation、漏/多重开、恢复时延、重复成本、source coverage 和跨 runtime replay；
加入 liveness/cost floor，防止 global-stop 或 never-compile 伪成功。

## 四、NAC 对 G1 的准确位置

NAC 七件档案从已经提取的画像或 Intent 面束开始。M1 的“采访适配器”说明它需要上游显化；
E-H1′只检验有向 Intent—画像标注对上的跨模型表示判别，不检验未表达机会怎样产生。因此：

- NAC 可以在“已有投影怎样编码、比较、渐进披露和迁移”切片中成立；
- 它不能用 H1 结果支持 search-before-query 或未表达机会形成；
- M3 的零漏检只能相对其输入/阈值真集解释，不能把 M1/锚点已漏掉的现实机会从分母删除；
- H1 的相对门槛还需同时报告绝对 recall，防止同厂商基线很低时仍相对通过；
- 单次 disclosure depth 的对等不等于多轮、多接收方累计泄露安全。

这是作用域澄清，不是对 NAC 的降级。

## 五、下一行动

第一波现成方案与反例扫描可以继续，但只能形成候选 A/B/A+B 和实验设计，不得产生任务
coverage。下一波优先级为：

1. 构造 T2 blind input/oracle；
2. 为 T1 或 T4 选择一个最小实例并实现对应 E1/E2；
3. 用 T2 base-run 建立 E3–E7 的共享事件世界；
4. 另行找到或构造 T3 的真正任务前态；
5. truth/evaluator 与求解方案由不同 Agent 生成和复核。
