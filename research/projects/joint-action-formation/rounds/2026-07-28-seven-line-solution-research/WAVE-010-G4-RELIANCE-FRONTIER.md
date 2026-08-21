# Wave 010 G4：从 capability 到 reliance 的方法选择边界

日期：2026-07-29  
状态：`LOCAL SYNTHETIC DISCRIMINATOR RUN / NO REAL-WORLD VALIDATION / NO FORMAL PROMOTION`

## 结论先行

G4 当前最承重的判别不是“有没有 capability”，而是：

> 对一个精确绑定的
> `operation × executor × environment × version × permission × resource × recovery × horizon`
> tuple，当前 lawful observations 是否足以区分“现在可依赖”与“必须阻断或弃权”。

这直接改变方法选择：

1. **依赖已表达且 current head 可查询**时，exact-operation CI/probe、IAM、原子 reservation、
   provenance/attestation、telemetry、durable workflow、recovery rehearsal 与 owner HITL
   的成熟组合可以闭合当前本地合成实例；强中心在获得同一信息和动作时与它因果等价。当前
   没有观测到需要新增协议机制的残余。
2. **规范判断缺失**时，模型、readiness、attestation 都不能代替 Authority owner；应调用
   有限、同预算的人工接口，或保持 `ABSTAIN/BLOCK`。
3. **承重依赖没有表达、不可查询也不可 probe**时，两个 world 可以拥有完全相同的合法
   transcript、但真实可依赖性相反。任何只读公开证据的方法——包括强模型和强中心——都
   不能同时避免误承诺与漏掉合法复用。可行解只有创造新 observation、请求有权主体披露，
   或诚实扩大阻断/reopen；这不是再换一个 classifier 能解决的缺口。
4. **历史 success 或服务 readiness**最多是 prior。除非它与本次 exact tuple、current
   Authority/resource head、分布和 recovery operation 绑定，否则不能晋升为 reliance。

因此，当前“稳定断点”位于 observation/Authority contract，而不是一个已经证明缺失的
Towow-only capability representation。它可以由成熟组件、强中心、人工制度和薄 adapter
实现；只有同一 lawful input 下仍出现可复现残余，才有资格进入新机制。

## 三个可运行任务实例

以下都是从现有冻结任务收窄出的合成实例，不是真人企业或生产事件。

| 实例 | 完整任务与已有输入 | 目标状态 | 主要失败 | 责任主体 |
|---|---|---|---|---|
| **T2 只读试点** | 约 80 人服务企业要在 14 天、9800 元内分析六个月工单。原 `REL-T2-V1` 因 raw export、model improvement、90 天保存及服务方日志 witness 被 `BUYER-DATA` 拒绝。候选 operation 是固定容器进入 `buyer-sandbox@2026.07`，只运行三条预批准聚合 query、零 raw export。 | attempt 前冻结 `RUN-READONLY-AGGREGATES-v1 × provider-container digest × buyer sandbox version × current data permission × compute/audit reservation × recovery rule`；之后才允许进入 G5。 | 服务 healthy 但 v2 exact probe regression；probe 通过但 permission revoked；执行身份 attestation 缺失；恢复只在纸面存在。 | `PROVIDER-TECH` 对 exact operation/probe/recovery 负责；`BUYER-DATA` 对 permission/credential/audit witness 负责；`BUYER-BUSINESS` 对 Adoption/Acceptance 负责；controller 只能编排，不能代签。 |
| **T4 三方联合投标** | 城市要求 12 个偏远站点、断网 24 小时持续采集、恢复后同步；D+5 前提交，总价不超过 360000 元。PRIME、FIELD、ASSURE 只有公开 capability，事前没有共同关系、current probe、reservation 或签署。候选 exact chain 是 `PRIME-v5 + FIELD-fw17 + ASSURE-audit2`。 | 当前 addendum 下 interop probe 通过；三项稀缺资源分别原子预留；价格、风险、audit scope 与签署 stance 由各自 Authority 对精确版本给出；仍保持 `CANDIDATE_NOT_COMMITMENT`。 | 个体 capability 都成立但 FIELD capacity double-reserved；技术 probe 通过但风险分配/audit scope owner stance 为 Unknown；旧 tender/readiness 被沿用。 | `PRIME-TECH/FIELD-OPS/ASSURE-AUDIT` 负责技术资格化；三个 commercial/bid Authority 分别负责价格、资源、责任和签署；`CITY-PROCUREMENT` 负责 tender 与后续 readback。 |
| **T6 重复与漂移** | 重复已成功的 T2/T4 路径，保留旧 probe/history/attestation；随后注入 model/container upgrade、permission/recovery drift 与一个未表达 sidecar account dependency。 | 在不改写历史的前提下降低重复成本；受影响 tuple 失效，无关部分保留；可查询 dependency current 时局部恢复，不可观察时 broad block/global reopen/human discovery。 | v1 历史被套到 v2 分布；公开 graph 未含 sidecar，A 中有效、B 中 revoked，但决策前 packet 完全相同；“恢复成功”只来自 workflow 自报。 | 每个依赖的真实 owner 负责 current head；G4 只作 attempt 前预测；G5 在 attempt 前重新 gate；G7 根据可证明 affected closure 选择恢复或重开。 |

实例谱系来自
[`tasks/t2-readonly-pilot/blind/input.json`](./tasks/t2-readonly-pilot/blind/input.json)、
[`wave-003-c-joint-bid/blind/input.json`](./wave-003-c-joint-bid/blind/input.json)、
[`WAVE-009-G4-G6-G7-DESIGN.md`](./WAVE-009-G4-G6-G7-DESIGN.md) 与
[`WAVE-010-X2-INPUT-CONTRACT-CANDIDATE.md`](./WAVE-010-X2-INPUT-CONTRACT-CANDIDATE.md)。

## 公平比较矩阵

这里比较的是同一信息、Authority、预算和 horizon 下能承担什么，不用产品名或原创性加分。

| 方法 | 能完整解决的有界切片 | 稳定停止点 / 误承诺来源 | 当前选择 |
|---|---|---|---|
| declaration / capability profile | 已冻结、长期不变、无稀缺资源和独立 Authority 的低风险 task | 不绑定 exact tuple；version、permission、capacity、recovery 漂移后仍会绿色 | 只作候选生成或 prior |
| readiness + telemetry | 进程是否可接流量、当前健康与分布异常 | healthy service 不蕴含 exact operation 成功；telemetry 不决定授权或规范变化 | 监控输入，不单独承诺 |
| CI/eval / exact probe | 精确 artifact、executor、environment 和输入分布被覆盖的技术 operation | probe 过期、held-out regression、probe 改变资源状态；不含 permission/commitment | 资格化内核，必须绑定 head/horizon |
| IAM / policy | 当前 Principal 对 exact action/resource/purpose 的 permission | `Allow` 不证明技术能力、capacity、recovery 或未来 Authority | 独立 execution gate 输入 |
| atomic reservation | 阻止稀缺资源重复承诺 | 不证明 capability、签署、预算或验收 | T4 必选组件 |
| attestation / assurance | artifact、执行者、步骤与来源绑定 | provenance 不等于 liveness、permission、capacity 或 task success | 防 substitution，不作完成证明 |
| workflow + history + retry | 已表达动作图的 durable execution、pause、retry、migration hook | workflow green 不是 target truth；旧 history 不自动属于当前 regime | 执行 substrate，需 current requalification |
| 强模型动态诊断 | 识别矛盾、选择 query/probe/human、校准 `ABSTAIN` | 不能从相同 transcript 推断 hidden world，也不能代签 Authority | 放在 evidence acquisition/policy 层 |
| **成熟组合 + owner HITL** | 依赖完整、heads 可查、exact probe 有覆盖、reservation 原子、recovery 已演练、owner response 可得时，本 fixture 的可观察切片 | hidden/unqueryable dependency；Authority owner 不响应；外部恢复事实不可读 | **当前默认采用/封装路径** |
| **lawful optimized strong center** | 可集中以上全部组件和推理；同 lawful API 下可与组合等价 | 集中计算不会创造未表达事实，也不能成为跨域 truth owner | 若成本/迁移更优可直接采用；不故意削弱 |
| **人工接口 only** | 价值、风险、责任和 material goal change 的 owner 判断 | 人不能替代 exact probe、current machine head 或原子 reservation；人工也可能不知道 hidden dependency | 只在不可代行点调用，受相同延迟/费用/拒绝约束 |

“成熟组合完整解决”是条件句，不是产品认证。Temporal/OPA/Kubernetes/OTel/in-toto 等名字
存在，不等于它们已经被集成为同一 truth-preserving runtime；每个跨合同输出仍需保存 exact
tuple、source、head、horizon、cost 和失效规则。

## 最有信息增益的反例

### 1. `healthy service / exact operation regression`

T2 v1 与 v2 的 readiness、permission 和 reservation 都相同，只有 exact-operation probe
在 v2 regression。它直接推翻“readiness 就是 capability”的方法选择。正确修复不是给
readiness 增加新标签，而是把 probe 绑定 exact operation/version/distribution。

### 2. `capable / resource unavailable`

T4 三个主体技术 qualification 全部成立，但 FIELD 的同一 kit 已被另一项目预留。任何不读取
current atomic reservation 的组合都会误承诺。这把 capability failure 与 resource conflict
分开，并说明 `CI + IAM` 仍不完整。

### 3. `hidden dependency indistinguishability`

T6 两个 world 的 method packet 逐字相同，只有 private oracle 中 sidecar account 分别为
valid/revoked：

```text
same lawful transcript + opposite safe_to_rely
⇒ public-only deterministic policy must choose the same action
⇒ RELY gives one false commitment; BLOCK/ABSTAIN misses one viable reuse
```

这是当前最高信息增益的反例。它不证明需要新协议；相反，它给出三条完备响应：创建 lawful
dependency query/probe、请求有权主体披露，或承认 `BOUNDED_UNKNOWN` 并扩大 reopen。fixture
另有只把 `dependency.query_result` 变为 current `ACTIVE/REVOKED` 的 queryable pair，用来
验证新 observation 而不是新模型使分流成为可能。

### 4. `history success / recovery unknown`

T6 model/container/environment 改版后旧 history 仍为绿色，但 exact probe 不再 current。
恢复本身应视为一个新的 exact operation：要证明 credential 重绑、checkpoint 兼容、
idempotency、target readback 与补偿边界，而不是把“以前成功”改名为 recovery evidence。

## 本地可运行判别

最小 fixture：
[`WAVE-010-G4-RELIANCE-FIXTURE.json`](./WAVE-010-G4-RELIANCE-FIXTURE.json)。  
方法中立 evaluator：
[`WAVE-010-G4-RELIANCE-SIMULATOR.py`](./WAVE-010-G4-RELIANCE-SIMULATOR.py)。

运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/wave010-g4-pycache \
python3 WAVE-010-G4-RELIANCE-SIMULATOR.py --self-test
```

2026-07-29 本地实际运行：

| 固定策略 | precision | recall | abstention | 误承诺 | 漂移 unsafe 检出 | unsafe 恢复动作正确 |
|---|---:|---:|---:|---:|---:|---:|
| Declaration only | 0.333 | 1.000 | 0.000 | 8 | 0.000 | 0.000 |
| Readiness only | 0.333 | 1.000 | 0.000 | 8 | 0.000 | 0.000 |
| Probe + CI + IAM | 0.444 | 1.000 | 0.083 | 5 | 0.333 | 0.375 |
| Mature composition + HITL | 1.000 | 0.750 | 0.417 | 0 | 1.000 | 1.000 |
| Lawful strong center | 1.000 | 0.750 | 0.417 | 0 | 1.000 | 1.000 |
| Human interface only | 0.364 | 1.000 | 0.083 | 7 | 0.000 | 0.125 |

实际 stdout 以 `SELF_TEST_PASS` 结束；12 worlds 为 `T2=4 / T4=3 / T6=5`。fixture SHA-256：
`c1db758be05b96b35b8a45cdfb9c6096f75c6ffe9110f6fde76c4bb8edf4ddd8`。两个 invariance
checks 均通过：hidden pair method packets 无差异；queryable pair 只在
`dependency.query_result` 不同。

这些数字只描述手写固定策略在本地 fixture 的行为。代码没有实现 hostile worker sandbox，
因此不是独立 blind evidence；指标也不用于估计现实频率。它的价值是让以下断点可运行而非
停在叙事：

- precision/recall/abstention 与误承诺必须同时报告；
- 保守 `ABSTAIN` 通过安全门仍会损失 recall，不能零成本获胜；
- strong center 与成熟组合同输入同动作时应报告等价；
- hidden truth 只有在新增 observation 后才可能分流。

## 为什么旧错误不会在本判别中复发

| 历史错误 | 本轮阻断 |
|---|---|
| Wave 006 按 strategy label 收费，换函数不换标签即可获胜 | 本 fixture **不做成本 winner**；方法身份不进入 truth。未来成本结论只接受 candidate 不可改的 parent broker operation log。当前没有该边界，所以成本保持 `NOT MEASURED`。 |
| Wave 007 v1 的旧 `ACTIVE` receipt 覆盖 current `REVOKED` | permission、probe、reservation 都分别携带 `head_current`；旧 head 只能触发 `ABSTAIN/BLOCK`。正式 runner 仍需由 Authority service 查询 current head。 |
| readiness 当 capability | `HEALTHY-BUT-VERSION-REGRESSED` 保持 readiness 一致、只翻 exact probe；readiness-only 实际产生误承诺。 |
| 单次 probe 当持续 reliance | T6 把 model/environment upgrade 与 regime shift 单列；旧 probe 不绑定新 tuple 时重回 `ABSTAIN`。 |
| attestation 当 permission/liveness/capacity | fixture 分开 attestation、permission、reservation、telemetry；任何一项 PASS 都不能创建其他项。 |
| all-Unknown 伪装零风险 | 同时报 recall 与 abstention；成熟组合的 hidden-valid world 被计为 FN，0.75 recall 明确保留 liveness 代价。 |
| evaluator 读策略自报 success | evaluator 在策略返回后读取独立 `private_oracle.safe_to_rely` 重建混淆矩阵；固定 policy 只收到 `method_packet` 的 deep copy。此处只保证当前代码路径，不宣称恶意同进程隔离。 |
| workflow/history green 当作恢复证明 | recovery action 与 safe-to-rely 分开评分；历史只在 current tuple、distribution 与 recovery evidence 同时成立时可复用。 |

## 当前方法选择与下一项行动

当前采用顺序应是：

1. 对每个 prospective operation 冻结 exact tuple、prediction horizon 与 evidence heads；
2. 优先组装成熟组合或 lawful strong center，并允许两者等价；
3. 把 owner-only normative 判断路由到受预算约束的 HITL；
4. 对 unobservable dependency 先建设 query/probe/disclosure contract；建设前保持
   `ABSTAIN + broad block/global reopen`；
5. 只有这些条件具备后仍出现同一稳定 false-reliance residual，才讨论新机制。

下一项最高价值行动不是增加 world 数，而是把这一判别迁入 X2 的一个**实际 finalized X1
output**：选一条 T4 execution-eligible branch，由 G4 truth owner 在 method output 前冻结
`exact-version regression / reservation conflict / hidden dependency` 三个异质 mutation，
再让成熟组合、lawful strong center 和 general-model controller 在相同 API、HITL 与预算下
运行。若 hidden dependency 没有合法 query path，应把“创造 observation 的成本与成功率”
作为自变量，而不是让模型猜 oracle。

本文件不修改 X1/M01、NOW、PROGRAM 或正式 MechanismProfile，也不宣称 X2 已运行。
