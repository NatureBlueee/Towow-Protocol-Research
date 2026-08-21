# Wave025 model-input：Pro B 与本地证据的第一次综合

状态：`ROOT SYNTHESIS / NOT MODEL-INPUT CANON / NOT G AUTHORIZATION`

对象：

- 外部独立返回：`RETURN.md`，SHA-256
  `c9669b4e68fb5b769bc9ca6310675787c7e8909b3f3785f193937fb75dcab962`；
- 本地 Proposal A 及其独立红队；
- 已通过范围限定独立验收、但尚未采用为 formal canon 的 V2S primitives 与 routing；
- 已被红队判退、正在修复的 C01 minisuite v0；
- 当前 F smoke 只作为形状/失败证据，不作为功效答案。

本文不以“Pro 是否同意本地方案”为评价目标。它只判断外部方案中的哪些机制改变了问题、哪些与
本地已知事实冲突，以及下一项什么实验能区分它们。

## 1. 外部方案真正增加的东西

Pro B 的主方案也是受限 hybrid，但它给出了四个有用且可机器化的分层：

1. `allowed universe`：routing/schema 允许的 identity 语言；
2. `active universe`：某一 challenge/family 的 calibration 在读 label 前实际激活的 numeric
   identity 与尺度；
3. `fixed compressed universe`：固定 categorical hash 与 direct ngram blocks；
4. `candidate universe`：C01 在 calibration predictor 上冻结、随后才允许用 calibration label
   选择的候选。

这个分层比单说“static 或 calibration-derived”更准确。它允许同时表达：

- calibration 出现 schema/routing 不允许的 identity：admission/schema failure；
- holdout 出现 allowed 但 calibration 未激活的 numeric identity：numeric drift，不能扩列或忽略；
- holdout 出现新的 categorical value：进入既有 hash block，并在 C01 中按冻结的 absence/OTHER
  语义处理；
- fixed ngram bucket 不需要从 holdout 扩列。

外部返回还增加了三项建设性简化：

- 两个 clean-room provider 只负责生成 C01 atom stream 与 C02--C05 canonical matrices；逐字节
  一致后只保留一个冻结 trainer。除非原问题要求 trainer 也跨实现 bitwise 一致，不复制两套完整
  logistic/tree/kNN 实现；
- 将 `EARLY_LABEL_ACCESS`、`HOLDOUT_RESELECTION` 与 failure-code precedence 作为机器失败，而
  不是由结果中的布尔字段自证；
- exact sparse dictionary 可以作为 signed-hash 的 shadow/differential oracle；如果它在同一任务
  与成本边界内完整胜出，signed hash 可以删除，而不是因为历史设计已有 hash 就保留。

这些都符合“成熟组合完整解题就是正向结果”，不是 Towow 独占增量。

## 2. 与本地独立证据相互支持的部分

以下判断由外部返回和本地 Proposal A/redteam 分别得到，值得进入下一版候选的输入，而不是因
模型共识直接升格：

- pure static 不能自动表达 open values，pure calibration-derived 又不能证明 identity 合法性；
  最有竞争力的是 static admission language + label-blind calibration activation；
- signed collision sum 与 presence OR 必须分开；`signed_sum != 0` 不能实现 C03/C04 presence；
- identical token/count 必须先以 exact integer aggregate、再 cap、再查冻结的 count table；
- numeric observed zero 与 missing 是不同状态，必须有独立 missing identity/column；
- holdout-only numeric identity 是 drift failure，而不是 all-zero、忽略或动态新列；
- row/column order、identity framing、rational→binary64、`+0`、CSR duplicate/order/endianness和
  binding preimage都必须成为字节合同；
- SHA-256 只能绑定已经唯一的 bytes，不能替代语义或 canonicalization；
- label、case identity、audit/path/provenance/debug/build metadata不得进入 classifier artifact；
- actual-shape、collision、资源和功效必须实测，不能从 schema、hash 或理论宽度推出。

## 3. 不能直接采用的 Pro B 决定

### 3.1 不能用一个 `T-calibration` universe替代分层 fit scope

当前正式输入仍要求：

`CALIBRATION_ONLY_SEPARATELY_PER_CHALLENGE_AND_PRIVATE_CONTROL_FAMILY`。

因此不能让一个 T calibration universe为 D0/D1 提供 exact candidates或 numeric scale，也不能让
D0/D1反向参与 T。D0、D1各自的 calibration正是其 C01 primary positive-control fit surface；若只
在 T 上冻结 C01，D0/D1 的 role-stable exact atom将没有合法学习入口。

下一版应把 Pro 的 P0/P1/P2 phase复制到每个冻结的 `(challenge, private_control_family)`，并明确
禁止跨组共享 open exact vocabulary、TOP256和scaler。可以共享 static admission language、固定 hash
算法和机器格式，但不能共享由数据拟合的 membership。

### 3.2 `S_N` 不是总能枚举成有限静态集合

当前 routing含 dynamic `KEY`、`ORDERED`、`BAG_ITEM`与derived context。对这类 identity，schema
提供的更像一个可判定语言/构造器，而不是预先穷举的有限 set。

因此更准确的机器形式是：

```text
AllowedNumeric(identity) := primitives + exact routing candidate 对 identity 的验证
ActiveNumeric(group)     := 该 group calibration 中所有通过 AllowedNumeric 的 identity
```

calibration中出现 `AllowedNumeric=false` 必须失败；holdout中出现 allowed但不在 active set仍必须
以 drift失败。不能为了套用集合公式而无限展开 dynamic context。

### 3.3 route-aware ngram 的“缺失”在本地候选中已有答案

Pro只看到 `(family,bucket,count)` predictor tuple，因此诚实地把 route namespace列为缺失材料。
当前 V2S primitives candidate 已明确：ngram preimage包含
`family + raw_lexical_route_CTX2 + channel_identity + n + gram_bytes`，随后才按 `family+bucket`
聚合。这表示 route awareness在 bucket形成前已经进入 hash preimage，输出列按 family+bucket共享是
有意的 compressed identity，不需要 classifier重新读取 path、route或audit。

这个缺口对当前 exact candidate已被回答，但 primitives仍是 candidate而非 formal canon；release
manifest必须绑定它的 exact bytes，不能只写“route-aware”。

### 3.4 quantile不能无证据改成 `averaged_inverted_cdf`

本地 primitives candidate 已冻结 exact-rational `quantile_type7`；Pro建议另一种成熟 quantile方法。
两者对小样本和极端值会给出不同 Q25/Q50/Q75，因此这是竞争方案，不是文案差异。

在 E4 fixture 与 actual-shape rehearsal比较之前，既不能沿用 type-7只因为它已经存在，也不能改用
Pro建议只因为它更容易描述。比较标准是 D0/D1/T检测、资源、跨实现位一致和 removal counterexample。

### 3.5 C05 norm仍未由 Pro解决

Pro建议 C02追加 `log1p(norm)`、C05追加 raw norm；历史 V1为两者保留
`LOG1P_PRENORMALIZATION_FAMILY_NORM`。Prompt本身没有给 C05 精确函数，所以 Pro正确标成仍需决定。

这必须进入 E3 ablation：`none / raw norm / frozen-table-or-correctly-rounded log1p(norm)`，不能由
provider自行补义。

### 3.6 MPFR/Arb exact-dyadic策略是候选依赖，不是免费确定性

Pro提出 bucket sum与family square-sum先按 exact dyadic求和、最后一次舍入，sqrt/log1p分别由
correctly-rounded库完成。它能减少插入/归约顺序分叉，但会引入新的维护、版本、性能和跨语言
provider依赖。

本地已有更小的候选：feature层保持 rational/integer；count 0..255使用预冻结 binary64 table；
model层冻结 operation order、bit fixtures与provider。下一项 deterministic-math实验应比较两者的
bytes、峰值资源与实现复杂度。只有常规 fixed-order binary64确实分叉或不能通过 holdback时，才为
exact-dyadic/MPFR增加成本。

### 3.7 “所有七个 family eligible”不足以构成 model contract

family级允许不等于每个 channel/stat/identity可进入每个 classifier。下一版仍需 closed、machine
readable的 per-classifier eligibility：raw exact、numeric、missing、categorical context、ngram和
family norm分别列出。否则两个provider仍会对同一family选择不同列。

## 4. C01：外部方案也不能解除当前判退

Pro的 C01部分提出了 TOP256、context `MISSING/OTHER`、numeric exact/missing与统一候选比较，但它
依赖若干尚未冻结的选择：

- conjunction是 strict AND、带negation pattern，还是完整二位Boolean mapping；
- support是trigger coverage、预测分支人数、正确人数还是混合约束；
- F1未知 atom是 selector absence还是整行 OOV fallback；
- singleton context由什么routing/schema证据决定；
- candidate freeze、calibration label selection、holdout prediction与holdout label评分的能力边界。

本地 minisuite v0已因这些问题中的五项被独立红队判为
`REJECT_AS_EXECUTABLE_C01_SEMANTICS`。因此 Pro的长篇建议只能作为修复输入，不能把 v0或 Proposal A
升格。实际 D0/D1 sensitivity、T role-null、G与3200仍是 Unknown/Not Run。

## 5. 当前最小竞争实验

下一步采用 Pro的 `pre-label compiler duel`思想，但按本地真实边界修正为
`MI-DUEL-01`：

1. 每个 `(challenge, private_control_family)` 独立冻结 calibration membership；执行环境物理上
   不存在 label读取能力；
2. 比较三种 universe：
   - static validation language + static expansion；
   - calibration-only identities；
   - static validation language + calibration active numeric + fixed categorical/ngram blocks；
3. 同时比较 exact sparse shadow与 4096/8192/16384 signed hash；用 opposite-sign collision验证
   continuous sum和presence OR；
4. E3比较 family norm off/raw/log1p，E4比较 type-7、`averaged_inverted_cdf`和更简单no-centering；
5. valid fixtures比较两个provider的 manifest/MCSR2 bytes；invalid fixtures比较第一 failure code；
6. 当前12份F只报告 shape、nnz、collision、OOV-like与bytes，不读role label、不报告功效；
7. 不使用G，不消耗fresh formal holdout，不启动3200。

区分性判据：

- calibration出现 routing/primitives不允许的 identity：calibration-only方案暴露其语义弱点；
- static expansion制造大量全missing列而不增加已登记检测能力：hybrid更优；
- exact sparse在同一任务/成本边界完整胜出：删除signed hash候选；
- continuous signed sum归零而presence仍为1：保留独立OR source/view；
- 两个provider对hybrid bytes或failure code不同：继续修machine contract，不能进入G；
- simple math与exact-dyadic结果逐字节相同且simple明显更低成本：删除MPFR/Arb依赖；反之再保留。

## 6. 状态决定

```text
PRO_B_RETURN_CAPTURED
HYBRID_LAYERING_RETAINED_AS_COMPETITOR
T_ONLY_GLOBAL_UNIVERSE_REJECTED
ROUTE_AWARE_NGRAM_LOCAL_MISSING_MATERIAL_RESOLVED_BY_CANDIDATE_BYTES
QUANTILE_C05_NORM_AND_DETERMINISTIC_MATH_REMAIN_COMPETING_DECISIONS
C01_V0_REJECTED_AND_UNDER_REPAIR
MODEL_INPUT_NOT_CANON
G_NOT_AUTHORIZED
FORMAL_3200_NOT_RUN
```

只有 MI-DUEL-01、修复后的 C01 独立验收和 collector semantic admission都关闭后，才值得把这些
选择写进 `MODEL-INPUT-V2S.candidate.json` 与 `DETERMINISTIC-MATH-V2S.candidate.json`。
