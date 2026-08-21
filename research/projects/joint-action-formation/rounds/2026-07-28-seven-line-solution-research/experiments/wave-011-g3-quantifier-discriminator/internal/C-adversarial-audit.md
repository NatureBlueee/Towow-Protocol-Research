# C：6-world G3 候选鉴别器敌对审计

状态：`INTERNAL ADVERSARIAL PLAN / IMPLEMENTATION MUST FAIL CLOSED`  
职责边界：只攻击量词、oracle、inventory、Authority 与 baseline 公平性；不实现 worker，
不定义 expected label，不改正式研究状态。

## 1. 总判断

这个鉴别器最严重的风险不是少一个 `C/N/E/T/V` 字段，而是**在看到 treatment 结果后，
由同一 runner 用 hidden truth 生成这些字段和 counterfactual**。即使 JSON 完整、哈希一致、
六个 world 的 expected 全部命中，它仍可能只是在复述 private oracle。

因此评分对象必须是以下四个彼此可区分的运行事实，而不是一份自洽 verdict：

1. 运行前冻结的 Episode、inventory、response family、operator/equivalence 和删除语义；
2. actual policy 只由合法 observation history 产生的 transcript；
3. 与 actual policy 分权的 physical/measurable closure 结果；
4. 在 reset 后、冻结 trace/response schedule 上真实执行的 remove/reverse/block 结果。

任何一项只能由 world/arm 名称、expected label、owner 文本或事后选择补出时，应返回
`INVALID_EVALUATION` 或 `UNKNOWN`，不得猜测最接近的成功类别。

## 2. Mutation plan

| ID | 注入 mutation | 它会制造的伪成功 | 必须的 fail-closed 结果 |
|---|---|---|---|
| C-M01 | 把 public fixture 的 `expected_outcome`、label、world mnemonic，或 `W2-CLOSED-EXTENSION` 之类语义 ID 传给 worker | worker 按题号返回正确 `C/N/E/T/V`，没有求解 | actual worker 只能收到 opaque episode ID 与 method-visible packet；发现 forbidden key、语义文件名或 expected bytes 即 run invalid |
| C-M02 | arm 名称为 `bounded_unreachable`、`actual_miss`、`human_oracle`，runner/scorer 按 arm 名分支 | 换函数不换标签仍“正确” | 改名与 arm 顺序置换后 transcript/verdict 不变；scorer 不得读取 arm 名决定 truth |
| C-M03 | 运行后把 response family 缩成实际发生的 `approve` 单分支 | `R_effect_robust` 被伪造为 TRUE，拒绝/超时分支消失 | pre-run response-family hash 必须与 robust evaluator 输入相同；少一个未实现分支即 invalid，不得重算较小分母 |
| C-M04 | physical/measurable worker 或 actual policy 读取 hidden willingness、final receipt、realized branch、private oracle 文件 | 静态不可区分的两 world 被“正确”区分；actual policy 获得全知计划 | 对 method-visible packet 完全相同的 private-truth pair，actual transcript 必须相同直到合法 query 返回不同 observation；读取 forbidden path/key 即 invalid |
| C-M05 | counterfactual 删除 token/operator，但保留由它产生的 permission、knowledge、reservation、deployment、receipt 或 target state | operator 看似“不必要” | reset 到同一 S0；按预冻结 dependency graph 删除全部内生后果，再在冻结 trace/response schedule 上执行；graph 不闭包或删后残留即 invalid |
| C-M06 | counterfactual 删除 operator 及全部后果，同时错误删除共同外生状态或给 removal arm 新的 hidden facts | operator 看似“必要” | exogenous-state hash 必须与 actual run 相同；只允许预注册 intervention mask 改变 |
| C-M07 | 成功后才从 trace 中挑 operator IDs，或看到 token 后才制定 equivalence class | 任意成功都能被包装成 `NEW_TOKEN` 或最小充分集 | intervention candidate set、operator IDs、token-equivalence verifier 与 derived-effect graph 必须在 actual run 前冻结；post-run新增/换 verifier 即 invalid |
| C-M08 | tool/partner/representation/response/transition 任一 open，有限 frontier exhausted 后仍输出 `C=UNSAT` | open-world 搜索失败冒充 bounded-unreachable | 任何必要 inventory 非 `COMPLETE`、`unresolved_items` 非空或 bound 未冻结，`C` 只能 `UNKNOWN`；不允许 private oracle 用 expected label覆盖 |
| C-M09 | measurable worker 给出合法 policy，但 actual arm 走 stale branch/错误动作失败，scorer输出 bounded-unreachable | implementation/policy miss 被写成世界不可达 | 同一冻结 envelope 下 `C=SAT, R_physical=TRUE, R_measurable=TRUE, R_actual=FALSE` 必须唯一进入 `ACTUAL_POLICY_MISS` |
| C-M10 | 用 owner receipt 的存在掩盖 controller claim，或 controller receipt 被放进 owner list；同一 diff 同时携带两者 | 无权 task substitution 被登记为授权新 Episode | owner receipt 必须由 authority map 中该 material path 的 owner key 对 exact before/after hash 与 ordered diff 签名；owner/controller 两类非空或 key/locus 不匹配时 invalid |
| C-M11 | equal-envelope center 直接读取 private truth、代 holder 签名、绕过公共 Authority endpoint | center 依靠额外权力“胜出” | 所有 Authority/holder/private-state 访问必须留下同一 endpoint receipt；center 的额外读取/签名立即 `V=INVALID`，不是较高 coverage |
| C-M12 | 把 legitimately-centralized world 的结果与独立 Authority world 当作同环境算法比较 | 环境变化被伪装成 center 算法优越 | legal-control center 必须是独立 environment/episode，明确 Authority topology diff；只支持“集中控制条件下成熟方案解决”，不得进入 equal-envelope superiority |
| C-M13 | human baseline 可看 private oracle/expected，免费询问、无限等待，或把专家直觉当 binding approval | human 变成万能 oracle，所有闭包都 SAT | human 只通过相同 query/Authority API 行动；问题数、时间、披露、拒绝、advisory/binding level 全计账；越界知识或无 receipt 的判断无效 |
| C-M14 | receipt/manifest 只保存自报的 inventory completeness 和任意 `evidence_sha256`，不核对实际对象 | 任意 arm 自称 complete 后可报 UNSAT | completeness 必须由独立 evaluator从冻结对象逐项重建；self-claim 只能是 candidate output，不能成为 oracle |
| C-M15 | actual transcript 删除失败询问、改写顺序，或只返回终态摘要 | policy 是否只依赖合法 observation history无法检查 | 保存逐步 action、可见 observation、Authority endpoint、response status、cost、state hash；摘要不能替代 transcript |

## 3. 最小 fail-closed rules

### F1 — 输入隔离

- public fixtures 不含 expected category、expected coordinates、world mnemonic 或 truth-correlated
  branch 名；
- worker 只得到 opaque episode ID、method-visible state 和允许的 API；
- private oracle、expected table、Authority signing material 与 scorer 进程不在 worker
  可读路径/参数中；
- rename、arm permutation、world permutation 必须是必跑 metamorphic test。

仅把 expected 文件放到 `private/` 不足以证明隔离；runner 仍可能先读 private oracle，再调用
worker。测试必须验证实际传给 worker 的序列化 bytes 和允许读取的资源。

### F2 — response family 与 actual transcript 双冻结

`response_family_hash`、observation kernel、transition semantics、budget 和 horizon 必须在
actual run 前绑定。actual policy 每一步只能消费 transcript 中已经返回的 observation。
robust worker 必须遍历冻结 response family，而不是 actual branch 的投影。运行后任何 shrink
都使 robust 坐标无效。

### F3 — bounded unreachable 的硬门

只有同时满足下列条件才允许：

```text
C=UNSAT
R_physical_exists=FALSE
R_measurable_exists=FALSE
R_actual=FALSE
search_bound_frozen=TRUE
action/meta-action + observation + response + transition inventory = COMPLETE
tool + partner + representation + exit/human/program inventory = COMPLETE
unresolved_items=[]
```

其中 completeness 必须由独立 worker 对实际冻结对象验证，不能由 fixture 的 expected
或 candidate 自报。任一开放项优先输出 `UNKNOWN/UNRESOLVED_MODEL`，即使搜索 frontier
已经耗尽。

### F4 — actual-policy miss 的硬门

`ACTUAL_POLICY_MISS` 必须由独立 measurable worker 的 SAT witness 和 actual worker 的失败
trace 在同一 envelope 下相交得到。不能因为 world author 写了 `measurable=true`，也不能因
actual arm 未找到 plan 反推 UNSAT。

### F5 — counterfactual 先注册、后执行

运行前冻结：

- operator candidate set 和 IDs；
- operative-token equivalence verifier；
- intervention mask；
- transition/derived-effect dependency graph；
- reset semantics、共同 exogenous state；
- remove/reverse/block 的执行规则与允许的 minimal-set 枚举边界。

actual run 后只能填入真实 trace 引用。counterfactual 必须从同一 `S0` clone 执行，使用同一
policy commit、冻结 response schedule/合法 observations，并把被移除 operator 的所有内生
后果做传递闭包删除。禁止拿 final truth 重规划，禁止用 expected label直接填写
`removal_result`。

### F6 — task diff 与 Authority 分权

material `Q/V0/Principal/Authority` diff 必须逐 path 保存 before/after 值并绑定 original/result
task hash。授权新 Episode 需要相应 path 的 owner Authority key 对 exact diff 的签名；普通
controller claim 永远不能升级它。若 owner receipt 与 controller claim 同时解释同一 material
diff，或 owner key 不在冻结 authority map 中，直接 `INVALID_SUBSTITUTION/INVALID`。

### F7 — baseline envelope 不可偷换

- `equal-envelope center` 与其他 arm 共用 observation/query/Authority/human API、预算、
  horizon、response family 和 verifier；计算集中不等于 Authority 集中；
- `legal-control center` 只在确实合法集中控制的独立 world 中运行，必须报告 environment
  与 Authority topology diff，不能与 equal-envelope arm 合成算法排名；
- human baseline 的每次询问、解释、审批、等待与披露都是 trace action；没有 Authority
  receipt 的专家判断只是 advisory。

强中心、成熟 workflow/planner 或人类制度通过是正向解；本规则只禁止它们通过额外 oracle
或额外 Authority 获胜。

## 4. root 必须补的独立测试

以下测试应由 root/独立 tester 实现，不由 fixture author 自证：

1. **label/rename leakage**：删除全部 expected 字段，opaque 重命名 world/arm，随机置换顺序；
   所有 truth coordinates 与 transcript 保持不变。
2. **forbidden-byte canary**：只在 private oracle 放随机 canary；worker 输出、日志、输入 hash
   均不得出现。把 canary 放入 expected label 后结果也不得改变。
3. **response-shrink mutation**：在 actual 成功后删掉 `REFUSE` 或 `TIMEOUT` branch；
   scorer 必须拒绝 robust verdict，而不是继续 PASS。
4. **private-truth indistinguishability pair**：method-visible bytes 相同、hidden willingness
   相反；未 query 前 actual action/transcript 必须相同，query 后才允许分叉。
5. **derived-effect residue mutation**：remove token 后故意保留 reservation/permission/receipt/
   target effect 各一种；四个变体全部 invalid。
6. **exogenous over-delete mutation**：remove 时删除一个共同外生资源，使结果变 UNSAT；
   必须因 exogenous hash 改变被拒绝。
7. **post-hoc operator/equivalence mutation**：actual 后新增 operator ID、替换 equivalence
   verifier 或只把成功 token定义成“新”；必须因 pre-run hash 不符被拒绝。
8. **open-inventory exhaustion**：把 tool/partner/representation 任一改成 `INCOMPLETE`，
   同时维持 exhaustive frontier；唯一允许 `UNKNOWN`，`BOUNDED_UNREACHABLE` 必须失败。
9. **actual-miss cross-worker**：measurable worker 返回 SAT witness，actual worker 走 stale
   branch；期待 actual-policy miss。再删除 SAT witness，应变 `UNKNOWN`，不能凭 expected
   保留原标签。
10. **owner/controller mix matrix**：合法 owner only、controller only、两者同时、伪 owner
    key、receipt 签了不同 diff、authority locus 错六种；只有 exact owner-only 为
    `AUTHORIZED_NEW_EPISODE`。
11. **center Authority theft**：给 center 注入 holder private read 或 controller-signed token；
    即使 Effect 成功也必须 `V=INVALID`。通过相同 endpoint 获得 holder receipt才有效。
12. **centralized-environment transplant**：把 legal-control center trace 移植到独立
    Authority world；因 environment/Authority hash 不同拒绝，不得报告 center superiority。
13. **human-oracle budget**：给 human 第 `budget+1` 次免费 query、无限等待或 private answer；
    结果必须 invalid/over-budget。把专家文本从 “advisory” 改成 “binding” 但无 holder
    receipt也必须失败。
14. **actual transcript deletion/reorder**：删失败 query、交换 observation/action 顺序、只留
    final state；三种都不能验证 `R_actual`。
15. **worker disagreement**：两个独立 closure worker 对同一 frozen input分歧时输出
    `UNKNOWN/CONFLICT` 并保留两份原始结果，不允许 runner 按 expected label选一个。

## 5. 六类 world 的最低验收重点

- direct qualified path：必须证明是 `S0` 中直接存在，不是 scorer 从 world 名推断；
- closed extension：old closure 的 UNSAT receipt 与 new operator 的授权/语义 diff 都要独立，
  且新模型保持原 `Q/V0/Principals/Authority`；
- prefix-SAT/new-token：`request/sign` 已在 old closure，故 `C=SAT,E=SAME`；token 新形成只改变
  `N`，不能回写 old closure；
- actual-policy miss：保存 measurable witness 与 actual transcript，禁止降成 bounded-unreachable；
- open inventory：任何 search exhaustion 都保持 Unknown；
- material task change：owner-authorized fork 与 controller substitution分别验证 exact diff，
  不能用“有 receipt”统一处理。

## 6. 审计结论边界

本计划不会证明新 planner 必要。若 equal-envelope center、成熟 planner/workflow/IAM 组合或
有界人工制度在上述攻击下完整通过，应登记为当前 6-world 的正向解决。若合法集中 Authority
的环境由成熟方案解决，也应登记为环境条件化正结果；只是不能把它移植成独立 Authority
环境中的同条件算法优越。

在 C-M01 至 C-M15 和第 4 节独立测试未关闭前，`6/6 expected labels`、字段哈希一致或测试
全绿都不足以支持量词分辨力。

## 7. 对当前实现的只读交叉检查

以下是文件开始落盘后的具体观察；它们不是推测，也不是要求 B 在本文件之外接受某种新架构。

### 7.1 已确认的 leakage

- `fixtures/public-worlds.json` 的 `world_id` 逐字包含
  `DIRECT-QUALIFIED / CLOSED-LEGAL-EXTENSION / PREFIX-SAT-NEW-TOKEN /
  MEASURABLE-ACTUAL-MISS / OPEN-INVENTORY / MATERIAL-TASK-CHANGE`。这是完整 answer class，
  不能称为 opaque method-visible ID。
- 同一 public fixture 的 W4 提供 `policy_hint="stale_direct_execute"`，W5 提供
  `policy_hint="safe_unknown_exit"`；两者分别把 actual miss 和 Unknown 的预期策略写入
  候选输入。
- `actual_policy_worker.py` 明确按 arm 名分支：`C-FORMATION` 在 W4 故意直接
  `execute_with_token`，在 W6 选择 `controller_rewrite`；其他 arm 选择合法路径。
  这不是策略性能差异，而是 arm-label scripted outcome。

因此，当前实现即使产生预期分类，也不能支持“候选未读取 scorer truth”或 baseline 公平
比较。最低修复是 opaque ID、删除 truth-correlated hint，并使方法只按可观察状态/统一策略
工作；需要失败 arm 时，应用相同策略面对不同合法 observation，而不是在代码中写 arm 名。

### 7.2 closure/measurable 实际读取 realized branch

`closure_oracle_worker.py` 和 `measurable_oracle_worker.py` 都把
`oracle["actual_response"]` 作为单一 `response` 交给 `search()`。该 search 不是 contingent
policy/response-tree 搜索，只是在已知 realized response 下找线性序列。因此当前的
`C` 与 `R_measurable_exists` 可能是 hindsight-branch SAT，而不是“存在只依赖合法
observation history 的 policy”。

此外，W3/W4 的 private `response_branches` 都只有 `["APPROVE"]`。它们不能检验
approve/refuse/defer/stale 的 robust 坐标，也构成 realized-response shrink。至少应有一个
相同 public packet、冻结多分支 response family 的 paired test，由 policy 在收到 observation
后条件分支；closure worker 不得提前知道哪条 branch 会实现。

### 7.3 robust checker 把非法 trace 当 safe terminal

`robust_worker.py` 的 `terminal_robust` 条件包含 `or not item["valid"]`。这会把
“固定 approve trace 在 REFUSE 分支上因 response 不允许而执行失败”直接计作 terminal
robust，即使 trace 没有执行 `safe_exit/defer/refuse`，也没有形成任何合法终止状态。

正确语义应要求每个分支通过明确 terminal action/state 结束；invalid replay 是 policy 对该
observation 未定义，应使 terminal robustness 失败，而不是自动通过。

### 7.4 inventory completeness 仍是窄字段自报

`measurable_oracle_worker.py` 只检查 action、response、observation、transition 四个字符串，
未检查：

- `search_bound_frozen`；
- `unresolved_items=[]`；
- tool、partner、task representation、exit/human/program inventory；
- inventory 对应的 executable object/hash 是否真的存在。

`closure_oracle_worker.py` 完全不消费 inventory，故对 open world 仍可输出线性搜索
`UNSAT`。若 runner 最后依据 expected/world ID 覆盖为 Unknown，结果仍不是量词鉴别。

### 7.5 counterfactual 没有验证 derived-effect deletion

`counterfactual_worker.py` 声明
`RESET_TO_PRIVATE_S0_AND_DISCARD_DERIVED_EFFECTS`，但 private oracle 的 `derived_effects`
字段没有被读取或核验；不存在 dependency graph closure 检查。`remove` 与 `block` 调用完全
相同，`reverse` 只是从 action list 删除 operator 再 replay。当前简单 fixture 从空 S0 replay
可能恰好得到预期 UNSAT，但 mutation 保留 permission/reservation/receipt/effect 时，worker
没有机制发现 inconsistent residue。

runner 应把预冻结 graph 和 frozen trace hash交给 worker，并测试删除内生后果闭包与外生
state hash；不能用一个 reset 字符串代替实际验证。

### 7.6 legal-control center 与 human baseline 尚不是公平实装

- `actual_policy_worker.py` 仅根据 arm 名把
  `B-CENTER-LEGAL-CONTROL` 标为 `LEGITIMATELY_CENTRALIZED`，并直接选择
  `central_issue_token`；public Episode 并没有对应的合法集中 Authority world。若 runner
  另行注入该 action，就是基于 arm 名增加 Authority，而不是独立环境构造。
- `B-HUMAN-RULE` 与其他非特殊 arm 共用同一个 hard-coded `choose()`；没有 human query、
  disclosure、等待、拒绝、advisory/binding、成本或 budget transcript。它不是实际 bounded
  human baseline。

legal-control positive 应有不同 environment/Authority contract；human baseline 若本轮不
实装，应诚实标 `NOT_IMPLEMENTED/NOT_RUN`，不能因共享 deterministic trace 宣称已比较。

### 7.7 当前最高优先级

在扩充分类或美化 receipt 前，root 最应先补：

1. opaque rename + 删除 `policy_hint` 的 metamorphic test；
2. actual worker 不按 arm 名分支的 invariant；
3. multi-response contingent closure 与 private-truth indistinguishability pair；
4. invalid trace 不得计作 safe/terminal robust；
5. open inventory 强制 Unknown 的独立 gate；
6. derived-effect residue counterfactual mutation；
7. legal-control environment transplant 与 human free-oracle test。

这七项若未关闭，当前运行只能作为**答案编码 fixture 的开发 smoke test**，不能称为独立量词
分辨力验证。

### 7.8 runner/report 又确认了三个 post-treatment oracle

`runner.py` 落盘后可直接确认：

1. `operator_ids` 是 actual policy 返回后，拿 private oracle 的 `extension_actions` 与
   hard-coded `{"holder_sign"}` 和 actual action IDs 求交得到。这正是 C-M07 的事后
   treatment 选择；不是运行前冻结的 intervention set。
2. `N` 由 actual branch 的 final facts 是否含 `purpose_token/adapter_ready` 决定，没有
   operative-token equivalence verifier，更没有 S0 equivalence inventory。它只能说明该字符串
   在此 trace 末端出现，不能抵抗事后换名或等价旧 token。
3. `make_task_diff()` 在看到 private `actual_response=="APPROVE"` 和 policy action ID 后，由
   evaluator 自己调用 `receipt_ref()` 造出 owner receipt；没有 owner 签名、Authority key
   校验或 receipt body 绑定 exact diff。controller claim 同样由 evaluator 自造。因此 W6
   当前的 owner/controller 区分是按 action 名分类，不是 Authority receipt 验证。

另外，`inventory_receipt()` 只是把 public fixture 的自报 inventory 连同语义 world ID 再
hash 一次，不构成 completeness 证据。`CENTRAL_TOKEN_ACTION` 由 runner 按 legal-center arm
名注入，公开 Episode 的 Authority map 没有授予 center `issue_token`。

当前 `outputs/report.json` 的 30 个结果也表明 baseline 比较没有实际分辨力：

- W1、W2、W3、W5 的五个 arm 逐项相同；
- W4 只有代码中被 arm-name 特判的 `C-FORMATION` 发生 actual miss，其他 arm 都成功；
- W6 只有同样被 arm-name 特判的 `C-FORMATION` 走 controller substitution，其他 arm 都收到
  evaluator 自造的 owner receipt；
- human 与 mature workflow 没有独立行为或成本差异。

因此报告中的
`actual_policy_worker_received_private_oracle=false` 不能支持 blind：答案通过 public
world ID、policy hint 和 arm-specific code 已经进入 worker。进程分开也不等于两个独立
实现；closure/measurable/robust/counterfactual 都由同一 runner 提供同一 private oracle，
且共享 `_engine.py` 语义。
