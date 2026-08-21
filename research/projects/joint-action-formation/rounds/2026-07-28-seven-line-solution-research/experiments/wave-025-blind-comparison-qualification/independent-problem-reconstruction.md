# Wave 025 独立问题重建：A1–A5 公平比较资格

日期：2026-08-01  
状态：`INDEPENDENT PROBLEM RECONSTRUCTION / NO RUNNER / NO RANKING`

## 结论先行

A1–A5 的比较资格不能由“同一份 prompt”“随机打乱顺序”或“所有文件哈希一致”恢复。真正需要
恢复的是一个可解释的反事实：

> 若同一个合格问题实例由不同 treatment 处理，观察到的结果差异应来自 treatment 本身及其
> 预先声明的合法依赖，而不是答案泄漏、world 不同、运行顺序、共享状态、evaluator 反馈、
> controller 代做、选择性适用或成本遗漏。

因此，公平比较的最小单位不是一次进程启动，而是
`冻结问题实例 × 合法适用域 × 隔离 world clone × treatment × replicate`。比较资格属于整个
batch，而不是某个 arm 单独拥有的属性。

本报告的核心判断是：只有同时形成以下证据闭包，A1–A5 才能恢复**有界比较资格**：

1. 比较问题、适用域和估计对象在看结果前冻结；
2. 五个 treatment 都由真实 treatment 实例执行，而不是名称或代理实现；
3. 每个 treatment 获得语义等价的合法机会，但不会因“公平”而获得原本无权获得的 Authority；
4. 隐藏 world、分配、顺序、其他 treatment 状态和 evaluator oracle 对 candidate 不可见；
5. 每个 arm 使用独立 truth-owner clone，能够证明无跨 arm、跨 world、跨 replicate 污染；
6. randomization、replication 和非适用处理足以支持预先声明的比较，而不是一次演示；
7. evaluator 在评分冻结前不知道 treatment identity，不接受 candidate/controller 的结果自述，
   只重算原生 Authority、Effect、Acceptance 和成本证据；
8. leak-only attacker、顺序置换、污染 canary、oracle 攻击和 root 改写攻击均未击穿上述边界；
9. 独立操作者在新运行根复现同一资格判断。

这仍只允许在冻结任务族与适用 strata 内比较，不产生全局赢家，也不证明 V1/V2 已解决。

## 一、从 V1/V2 恢复比较真正要回答的问题

Problem V1 要求冻结 `S0 / V0 / Q`、必要 Principal、Authority Locus、目标域 witness 和强基线，
并区分发现、条件创造、问题改写、执行、Effect、Adoption、Acceptance 与 Settlement。Problem V2
进一步要求不同主体的局部世界、权威、责任和披露策略不能被安全折叠；中心、平台、制度、
人类和联邦机制都是可选解，不是预定敌我。

所以 A1–A5 不应回答“哪个标签更像通爻”，而应回答三个更窄的问题：

1. **解题比较**：在共同任务与合法适用条件下，哪个实际 treatment 更好地保留 `V0`、满足
   `Q`、处理拒绝/Unknown，并产生可验证的 Effect/Acceptance？
2. **条件比较**：每个 treatment 依赖哪些 Authority、信息、平台、模型、人力和既有制度？
   这些条件在多少任务分布中真实存在？
3. **生命周期比较**：首次形成、重复运行、漂移、恢复、迁移和治理的总成本与失败是什么？

这三个问题不能被一个总分吞并。尤其 A1 lawful center 的 lawful Authority 是其适用条件，不能
为了“equal information”非法复制给其他 arms；反过来，也不能只在强中心最有利的世界运行 A1，
再把它与其他 arms 的全分布结果直接比较。

## 二、先冻结 estimand，避免比较对象在运行后变化

令：

- `c`：一个冻结问题实例及其 hidden world；
- `a ∈ {A1,…,A5}`：实际 treatment；
- `r`：独立 replicate；
- `I(a,c)`：在看结果前冻结的 treatment 适用谓词；
- `Y(a,c,r)`：由原生事实重算的多维结果，而不是 arm 自报的 success；
- `K(a,c,r)`：披露、等待、模型、人力、基础设施、失败与恢复成本向量。

比较前必须在 sealed manifest 中声明至少一种估计对象：

- `DEPLOYMENT-PACKAGE`：比较完整可部署组合，合法权限、平台和工具属于 treatment；
- `REASONING-CORE`：所有 arms 在同一信息/工具接口上比较决策内核；
- `COMPONENT-ABLATION`：只比较某组件的因果责任，其他组成完全相同；
- `LIFECYCLE-POLICY`：比较一串 episode 的重复、漂移与重开，不把单次运行当单位。

这些 estimand 不能混在同一个 winner 结论中。A3 调用成熟 workflow、A5 使用软件、A1 内部使用
模型都可能是有效 deployment package；但这不能再被解释成“模型”“人类”或“中心”单组件的
因果胜负。若要解释组件责任，必须另做 factorial/ablation。

### 适用域而不是事后豁免

`I(a,c)` 必须在结果前由 problem facts 判定：

- A1 只有在存在能够合法覆盖所需决策的中心 Authority 时才适用；
- A2 可以测试等信息中心的整合能力，但不能继承 A1 的不可代行权威；
- A3 必须是真实冻结 provider/model/session/tool treatment；
- A4 必须是冻结的确定性成熟组合，不得由 controller 临时补推理；
- A5 必须是真实、边界明确的人类制度，而不是模型模拟的“human-like”回答。

非适用结果记为 `NOT_APPLICABLE`，不能算 FAIL，也不能被丢弃。公平报告至少需要：

1. 所有 arms 共同适用的交集 strata 内结果；
2. 各自适用域覆盖率；
3. 全任务分布上的 `PASS/PARTIAL/FAIL/UNKNOWN/NOT_APPLICABLE/NOT_RUN` 分布。

没有这三项，“A1 在适用场景 100%”和“A3 在全场景 80%”不可比较。

## 三、公平不等于逐字节相同

公平需要冻结**语义机会**，而不是把异质 treatment 强行压成相同字节：

- 共同：exact `Q / V0 / S0`、object、Target、operation、deadline、Authority topology、允许的
  action/API、预算口径、停止规则、关键底线、evaluator 语义；
- 可以不同：人类可读界面、模型 tokenization、确定性 adapter、平台原生格式、内部数据结构；
- 必须审计：这些 modality adapter 是否增删了事实、暗示答案、隐藏成本或替 treatment 完成推理。

“同一 JSON”可能对 A4 友好、对 A5 不可用；不同表示也可能在语义闭包完全等价时公平。需要
独立 adapter conformance 证明，而不是用 byte equality 代替。

同理，blindness 不是把现实也藏起来。candidate 必须能通过真实任务允许的 lawful API 获得
本应可观察的 Authority/Target 状态。隐藏的应是**实验答案与分配信息**。一个真实的 signed
revocation response 可以合法改变决策；一个路径名中的 `world-r`、额外的错误字段或 evaluator
返回的“接近正确”则是实验泄漏。

### 同构伪装不等于同构

最危险的假成功是：研究者只投影自己记录的字段，再证明投影逐字节相同。真实 candidate 的
可观察面还包括目录、process table、时钟、调度、cache、网络会话、key issuance、文件历史和
先前交互。两个 world 在记录投影上相同，却可在完整观察面上完全可分，这就是**同构伪装**。

资格要求应在每个 arm 内检验：给定相同公共事实、在第一个 lawful truth response 前，仅改变
hidden role 的 clones 不应产生可用于分类 role/expected result 的观察分布。这个要求不强迫 A1
和 A5 的界面彼此相同；它要求各自界面内部不编码当前 hidden answer。反过来，若为了 byte
equality 删除了人类或平台在现实中必须理解的语义，同样不公平。

## 四、五个 observation cut

比较需要冻结信息何时可以出现：

1. `T0 / SEALED`：问题生成、hidden world、分配和 truth 已冻结；candidate 尚未启动。
2. `T1 / PUBLIC-PREIMAGE`：candidate 只获得任务公共面、合法接口和 treatment 自身配置。
3. `T2 / LAWFUL-INTERACTION`：candidate 可以 ask/query/probe，并收到现实任务本来允许的响应。
4. `T3–T4 / EFFECT-AND-ACCEPTANCE`：Target 与各 owner 原生推进 Effect、拒绝、Acceptance/finality。
5. `T5 / BATCH-SEALED-UNBLIND`：全部 treatment 与 replicates 终态冻结后才解封分配、真值和评分。

Wave 024 证明，仅核对 T1 中记录的 payload/argv/env/cwd 相同不够：固定 `S→R→U` 顺序和同 UID
运行根仍让 candidate 在 T2 前通过目录、历史和 timing 推断 world。Wave 025 的资格标准必须
覆盖**所有可观测通道的分布**，而不是一张字段表。

## 五、必须隐藏、允许公开、只能事后解封

### 5.1 Candidate 在终态前必须隐藏

- hidden world role、case label、expected decision、ground-truth branch；
- treatment-to-clone 分配、batch 执行顺序、master seed、派生 seed 和随机化 block；
- fault/trigger 的具体时点、撤销是否已发生、helper/decoy 身份，除非它们由 lawful API 正常暴露；
- evaluator 私有 fixtures、answer key、阈值实例、失败分类和剩余尝试反馈；
- 其他 arms/replicates 的目录、进程、transcript、cache、receipt、得分和资源消耗；
- selector/controller 的私有 schedule、world manifest、root receipt 与文件命名映射；
- 能通过字典攻击恢复 hidden role 的 hash、opaque handle、certificate/key issuance order；
- 前序运行的 provider conversation、human 记忆、warm cache、rate-limit 状态和共享 scratch；
- 可把 timing、inode、PID、hostname、路径、错误形状或响应长度映射回答案的通道。

Treatment 可以知道“自己是 A3”或“自己采用 A1 protocol”；A5 人类不可能也没必要忘记自己是
人。必须隐藏的是其当前 clone 的答案、实验假说和其他 treatment 状态，而非 treatment 自身身份。

### 5.2 运行前允许且通常必须公开

- 原始任务价值、`Q / V0`、不可接受底线、deadline 和允许的结果类型；
- 合法 action/API 语义、认证根、查询费用、budget、retry/stop 规则；
- `PASS/PARTIAL/FAIL/UNKNOWN/REFUSE/NOT_APPLICABLE` 的公共语义与关键底线；
- 哪些 Authority/Target/owner response 是现实任务中合法可观察的；
- treatment contract、依赖、版本、工具与 permitted egress；
- 成本口径和需要留下的 usage/human-time/disclosure receipts；
- 训练/calibration cases，但不能包含 evaluation clone 或可逆映射；
- 结构 validator，只能告诉 candidate 文件/schema 是否可解析，不能泄漏 secret semantic score。

评分原则应公开，否则研究变成猜 evaluator；具体 held-out world、answer key 和 adversarial
fixture 必须保密，否则研究变成过拟合测试。

### 5.3 只能在 batch 封存后解封

- allocation map、执行顺序、master seed 与 clone derivation；
- hidden world manifest、fault schedule、answer key 和 case provenance；
- evaluator 的 secret fixture 实例与 semantic verdict；
- treatment label 与已冻结的语义评分 join；
- cross-arm transcripts、成本比较和 aggregate statistics；
- rerun/adjudication 所需的失败证据。

其中真实隐私、人员身份、受限 Authority 材料可以只向独立 auditor 解封，甚至永久不公开；
“post-run”不是自动公开个人或权威材料的许可。

## 六、恢复比较资格所需的证据闭包

### Q0 比较问题与 unit 冻结

证据：pre-run manifest 明确 estimand、task version、`Q / V0 / S0`、关键底线、适用谓词、unit、
replicate、预算、停止规则、缺失数据和 adjudication。任何 material change 生成新 batch，不追改。

失败反例：运行后发现 A1 不适用，便把该 case 从 A1 分母删除，却保留在 A3/A4/A5 分母。

### Q1 treatment 身份真实且封存

证据：

- A1：中心 Principal/Authority scope、policy/version、实际调用入口和 native receipt；
- A2：等信息中心的完整输入、工具、无额外 Authority 证明；
- A3：真实 provider、model/version、settings、fresh session、system/tool envelope、原始 transcript、
  usage/error receipt；
- A4：代码、依赖、配置、artifact hash 和 deterministic/non-deterministic boundary；
- A5：真实参与者/制度角色、同意、训练、材料、时间、升级与拒绝规则；若参与者看过别的 arm，
  必须按 crossover 而非独立样本分析。

所有 treatment 的实际运行 bytes/外部版本必须在首次结果前绑定。标签相同、内部 implementation
漂移的 runs 不能合并。

### Q2 world clone 与 truth-owner 等价

证据：每个 arm/replicate 获得独立 Target、Authority、owner stores/keys/namespaces；它们由同一
sealed semantic template 实例化，但没有共享可变事实。clone certificate 证明 exact
Q/object/Target/operation、初始状态、Authority topology 与 intervention schedule 等价。

需要满足：

- controller 只能调度，不能写 Authority/Effect/Acceptance truth；
- 各 world 的随机 nonce 和路径不可反推出 role；
- world 的因果顺序由原生 receipt/head/event 重算；
- 不能先在一个全局 Authority store revoke，再把后续 worlds 换标签；
- 对 T6 这类 sequence task，整个 episode sequence 是 clone unit，不能在中途重置希望保留的历史。

### Q3 semantic input 与合法机会等价

证据：独立 conformance evaluator 对各 modality adapter 做双向语义核验；同一 task fact 不因 arm
缺失，额外 hints、预求解字段和 answer-correlated errors 不进入任何 arm。adaptive query 可以
不同，但允许的 query space、收费、deadline、响应 authority 和 rate limits 必须可比较。

如果某能力是 treatment 的合法组成，就保留并计入依赖/成本；如果是共同环境能力，就对所有 arms
同样存在。一个成熟 Target gate 不能既在环境里替所有 arms 防错，又被记成某个 arm 的独占推理
成果。环境安全拒绝和 candidate 正确诊断要分别评分。

### Q4 隔离与 side-channel 证据

仅声明“candidate 没读”不够。至少需要以下实测：

1. candidate 无权读取 selector/root、其他 world、其他 arm、进程列表和 shared temp；
2. egress allowlist 阻止外部 mailbox、共享网页会话、provider history 或 covert storage；
3. hostname、cwd、argv、env、FD、UID namespace、path depth、inode、PID、key/cert 顺序、响应长度、
   错误形状和 timing envelope 不携带 role；
4. cache、quota、model session、human participant、tool state 和 target store 不跨 replicate 复用，
   除非复用本身就是冻结的 lifecycle treatment；
5. 隔离失败能够由 canary 和审计日志检测，而不是只靠约定。

### Q5 blind leakage 的经验反证

运行一个或多个不解题、只攻击泄漏的 `LEAK-ONLY` candidate。在 held-out clones 上，它只能观察
T1 表面，不调用 lawful truth API，却尝试预测 role、expected outcome、order 和 treatment mapping。

资格证据至少包括：

- 预先冻结的 chance baseline、样本量和置信区间；
- 多种攻击者：路径/进程枚举、timing classifier、hash dictionary、error-shape classifier、
  cache/probe attacker；
- label permutation 和 directory/order permutation 后预测仍在 chance envelope；
- 注入一个已知 leak 的 positive control 时检测器能够显著发现，避免“攻击器太弱”假阴性；
- 在真实 candidate 运行后复核 forbidden-channel canary 未被读取。

leak-only 通过是必要非充分条件；低统计功效不能写成“证明无泄漏”。

### Q6 randomization、counterbalancing 与 replication

证据：assignment 在 pre-run root 后由 candidate 不可见的 committed seed 产生，并在 batch 封存后
解封重算。按 task family、Authority topology、difficulty 和 world branch 做 block randomization；
每个 block 内随机 treatment-to-clone 和 execution order。

随机顺序本身不提供隔离。还需：

- 每个 replicate 的 mutable world 独立；
- 远程 provider 的时段、quota 和 service drift 在 arms 间 counterbalance；
- A5 优先 between-subject；若用同一人，采用预注册 crossover/Latin square、washout 和 learning
  term，不能把第二次运行当独立样本；
- stochastic A3 和 human A5 有足够 replicates，报告区间和 abstention，不以一次最好返回代替；
- rerun 规则预先冻结，失败后不得只给某个 arm 额外尝试。

### Q7 evaluator 不成为 oracle

证据：公共 validator 只给结构反馈；semantic evaluator 在 batch 期间单向离线运行，不向 candidate
返回 partial score、错误字段、距离、通过数或剩余测试。所有结果冻结后才解封。

semantic evaluator 应：

- 不 import treatment/runtime，不执行 candidate 提供的“summary”；
- 在 treatment label 仍隐藏时，从 native Authority/Target/owner stores 重算任务结果；
- 对 treatment label permutation 保持相同 semantic score；
- 把安全拒绝、正确 Unknown、晚失败、错误 Effect、Acceptance 缺失分别记账；
- 先冻结 semantic verdict，再由另一过程 join treatment 和 cost；
- 自身输入、代码、secret fixtures 与输出由 pre-run root 和 append-only post-run root 绑定；
- 接受独立 attack suite：candidate 写 evaluator 预期文件、改 root、伪造 summary、重签 semantic
  mismatch、利用 validator 迭代探测，均 fail closed。

### Q8 非干扰与跨世界污染证据

需要验证近似的 SUTVA：一个 arm 的结果不因其他 arms 的分配或先后而改变，除非研究对象本身是
跨 episode ecology。实证包括：

- 同一 clone template 在不同 order/permutation 下重放，结果分布不随前序 arm 变化；
- clean/cold 与 intentionally warm positive control 能被区分；
- shared-state canary、conversation nonce、cache key、quota receipt、file handle 和 DB head 不跨 world；
- 删除任一 predecessor world 后，当前 arm 输入与结果不应改变；
- parallel 与 serial 运行的资源竞争被测量；若容量/限流导致干扰，进入成本与失败结果而非隐藏。

### Q9 原生 outcome 与因果归属

每次 scored run 至少需要：actual candidate action、Target-native Effect/refusal、exact readback、
对应 owner Acceptance/finality、失败/补偿和停止证据。candidate、controller 或公共平台的 success
字段均不能替代这些事实。

同时需要区分：

- 环境 guard 正确阻断了错误动作；
- candidate 自己正确诊断并选择了动作；
- helper/controller 代 candidate 产生 Effect；
- 目标状态碰巧由并发外因出现。

否则五个 arms 都可能被同一个强 Target 自动修正为绿色，而比较不到 treatment 解题能力。

### Q10 成本与披露 receipt

同一 semantic outcome 之外，逐 run 原生记录：模型/provider usage、tool calls、人工分钟和角色、
询问轮数、等待、披露对象/内容/保存期、基础设施、规则建立、重试、错误恢复、治理与机会损失。

固定 token cap 并不自动公平。更稳妥的是运行多个预注册 resource envelope，报告 coverage–cost–risk
Pareto，而不是强迫 human、model 和 deterministic composition 共享一个虚假的单一单位。setup
成本、warm cache、human training 和平台订阅必须说明如何摊销。

### Q11 独立复现与 qualification receipt

最终资格不是 runner 自签。独立操作者在新 root、新 clone IDs、不同随机 order 上运行；独立
evaluator 重算 bytes、semantic hashes、签名、SQLite 原生事实、allocation 和 statistics。
qualification receipt 只列实际通过的 strata、arms、版本、replicates 与 claims。任何代码、
provider、human protocol、task 或 evaluator material change 使对应资格失效。

## 七、最强反例库

| 类别 | 最强伪成功 | 为什么现有浅门会放过 | 必须击中的证据 |
|---|---|---|---|
| 目录时间线 | 固定 S→R→U，R 启动时枚举到 S 目录 | payload/argv/env 仍完全相同 | 独立 namespace、随机 order、枚举 attacker |
| 路径/ID | `world-r`、UUID 前缀、path depth 编码答案 | schema 不含 case 字段 | opaque random namespace 与 label permutation |
| key 顺序 | 第 2 个签发证书/epoch/key 暗示 R | 签名都有效 | issuance 随机化、字典/顺序 attacker |
| timing | fence、cache、provider 冷启动造成可分类延迟 | 没有显式 label | timing envelope 检验；非研究变量则 padding，研究变量则随机化并计量 |
| 错误形状 | R 多一个字段/不同 status code，直接暴露 expected refusal | response “合法”且签名有效 | response semantic conformance、长度/shape attacker |
| hash dictionary | candidate 见到 hidden manifest hash，并从小字典反查 role | hash 看似 opaque | secret salt/commitment 只在隔离 root，candidate 不见 |
| shared Authority | 所有 worlds 前先 revoke，再把 S/U 换标签 | 最终 DB 有正确两条记录 | Authority-signed per-world causal predecessor |
| shared Target | A1 先 commit，A3 读到已改变状态 | 每个 arm 都有 receipt | 独立 Target clone/head canary |
| warm cache | 后运行的 A3/A4 使用前 arm 建好的索引/cache | 输入 bytes 相同 | cold/warm 分层、cache nonce、order invariance |
| provider memory | A3 的网页会话含先前 case 或 evaluator反馈 | 当前 prompt 干净 | fresh conversation/account context receipt |
| human learning | 同一 A5 人在前一 clone 学到 hidden generator | 每轮材料相同 | between-subject 或 crossover learning model |
| external mailbox | arms 通过联网工具交换 hidden facts | 本地文件隔离正常 | egress allowlist、session isolation、canary |
| evaluator gradient | candidate 反复提交，从错误提示推到答案 | 每次 validator 都“合规” | semantic evaluator batch 后单次解封 |
| evaluator源码oracle | candidate 读取 fixtures/expected JSON，直接产出匹配文件 | 输出结构与 hash 全绿 | evaluator隔离、native postcondition、attack fixture |
| controller代做 | arm 输出含糊 proposal，controller 完成合法调用 | 最终 Effect/Acceptance 真实 | candidate-action causal binding、helper removal |
| guard同化 | 强 Target 自动修复/拒绝所有错误，使五 arm 同绿 | 安全结果确实成立 | 分开计 candidate decision 与 environment safety |
| 选择性适用 | A1 只运行 unified-Authority cases，其他 arms 跑全部 | 各 arm 内百分比都正确 | pre-run applicability strata 与共同分母 |
| unequal adapter | A4 得到结构化真值，A5 得到缺字段叙述 | “任务内容大致相同” | 双向 semantic adapter conformance |
| budget偷换 | A3 可无限工具，A5 限 10 分钟；或反之 | 都叫一次 run | resource envelope 与原生 cost receipt |
| best-of-N | 只保留 A3 最佳一次，A4 单次 | 最终 artifact 只有一份 | attempt ledger、冻结 rerun policy、全返回入分母 |
| attrition | 慢/拒绝的 A5 run 被记为 NOT_RUN 后删除 | completed runs 看似强 | assignment ledger、attrition/Unknown 入报告 |
| secret seed 可读 | order 随机，但 seed 在 env/root 可读 | randomization 重算通过 | candidate 不可见 commitment domain |
| root rewrite | controller 看结果后同时改 manifest、world 与 hash | 内部 self-hash 全匹配 | controller 无权改写的 pre/post external root |
| scorer identity bias | evaluator 看见 arm 后给 human/center 不同解释 | 同一 evaluator 程序 | label-blind semantic verdict，事后 join |
| native格式偏置 | evaluator 只理解 A4 JSON，A5/A1 evidence 被 adapter 有损化 | 所有 arms 调同一 evaluator | treatment-native evidence adapter 的独立 conformance |
| distribution overfit | hidden generator 与公开训练模板同源，A3记住规律 | case label 真被隐藏 | 异源 held-out generator、permutation/novelty probes |
| time drift | provider/model 在一天中升级，arm 与时间固定关联 | 每次都有准确版本名 | block/counterbalanced time、version/service receipts |
| alias duplicate | arm 以新 ID/alias 重放同一 operation 得二次 Effect | request-id 幂等测试通过 | semantic occurrence/Target/operation closure |
| cross-episode pollution | T6 本应保留历史却被错误重置，或单次任务错误继承历史 | 每个 DB 自洽 | 先冻结 unit 是 episode 还是 sequence，再验证 head lineage |

这些反例不是都要求一种技术解决。它们要求资格报告说明：哪些被权限隔离，哪些被随机化吸收，
哪些作为研究变量测量，哪些仍为 `UNQUALIFIED`。

## 八、三类特别容易混淆的边界

### 8.1 隐藏答案，不隐藏合法 Authority

若现实任务要求 candidate 查询当前 Authority，则该响应应在 T2 合法公开。公平性要求各 arms
面对语义相同的查询机会和 authority source，不要求在 T2 后仍对真值无知。要隐藏的是 controller
事先知道的 role 与 expected verdict，以及现实 API 不会提供的 hints。

### 8.2 随机顺序，不共享同一个世界

把五个 arms 随机放入一个 mutable world 仍不公平：先运行者改变后运行者的世界。正确做法是
随机分配到独立 semantic clones；若研究共享世界中的竞争/资源争用，则必须把 joint assignment
作为新的任务与 unit，不能继续称为独立 treatment comparison。

### 8.3 evaluator 独立，不等于 evaluator 永远秘密

公共任务语义和评分原则必须公开；否则成功只是在猜私有规则。必须秘密的是 evaluation case、
answer key 和运行中的 semantic feedback。评分完成后可以解封供复核，但隐私/Authority 材料
可只对 auditor 开放。

## 九、资格判定逻辑

每个 batch/stratum 分别给出以下状态，不使用一个总绿色：

- `QUALIFIED_WITHIN_STRATUM`：Q0–Q11 的相关门均有证据，允许计算该 stratum 的 treatment contrasts；
- `NOT_APPLICABLE`：某 arm 的预冻结合法条件不成立，不计为失败，但进入 coverage；
- `UNQUALIFIED_LEAKAGE`：candidate 可能从 forbidden channel 恢复 role/答案；
- `UNQUALIFIED_INTERFERENCE`：共享 state、order、cache、provider 或 human learning 污染结果；
- `UNQUALIFIED_EVALUATOR_ORACLE`：运行中获得 semantic score/fixture反馈，或 evaluator看 arm 后评分；
- `UNQUALIFIED_TRUTH_SUBSTITUTION`：controller/candidate summary 替代原生 Authority/Effect/Acceptance；
- `UNQUALIFIED_TREATMENT_IDENTITY`：A3/A5 等只是代理、标签或不可复现版本；
- `UNQUALIFIED_ROOT`：pre-run freeze 或 post-run evidence 可由同一 writer 事后重写；
- `NOT_RUN / UNKNOWN`：证据不足，不能借此支持或反驳 arm。

只有 `QUALIFIED_WITHIN_STRATUM` 的 runs 进入 coverage/cost contrast。任何 critical authority、privacy、
Effect/Acceptance 或 unsafe-continuation 底线失败，最多是 `PARTIAL_SOLUTION`。单次合格 batch 仍不
允许“总体赢家”；至少需要异质任务族、held-out 变体、足够 replicates、独立复现和结果稳定性。

## 十、Wave 024 对 Wave 025 的直接改变

Wave 024 有三项可复用的正向能力：Target-consumed fence、ACK-lost exact recovery、owner-native
postconditions。它们可成为共同 measurement/safety substrate，前提是：

- 对所有 arms 的世界语义相同；
- 它们只提供现实任务允许的 authority/effect boundary；
- 环境 guard 的安全贡献不冒充 candidate 的解题贡献；
- 若某个 treatment 把这套组合当自己的方法，则不能同时把它作为其他 arms 的免费隐藏 helper。

Wave 024 同时提供一个决定性负结果：完整 isomorphic blindness 因 fixed order 和 same-UID
side channels 失败。这个失败不能靠改名为“recorded equality”消失；必须由 Wave 025 的隔离、
随机化、leak-only 攻击和非干扰证据关闭。U 也必须保留：Authority revoke 存在但 Target 未 ACK
时 raw commit 可以发生，不能把 unordered sample 强塞入 S/R 评分。

## 十一、下一步最有区分力的研究动作

不先实现五 arm runner。先做一个**资格挑战 batch**，只检验比较基础设施：

1. 生成大量语义等价、label-permuted 的 S/R/U 与 decoy clones；
2. 让多个 leak-only attackers 在 T1 表面预测 role/order/expected result；
3. 对 fixed/random order、shared/isolated namespace、cold/warm cache、公开/隔离 seed 做 factorial；
4. 注入已知 path、timing、hash 和 evaluator-feedback leaks 作为 positive controls；
5. 用独立 evaluator 测 chance accuracy、order invariance、canary 和污染传播；
6. 只有资格门能够同时拒绝 positive controls、接受隔离 held-out clones，才准入真实 A1–A5；
7. 随后分别冻结真实 A3 provider 与真实 A5 human protocol，再运行有 replicates 的适用 strata。

这个动作的信息增益高于直接再跑一次 A1–A5：如果资格挑战失败，任何 arm 差异都无法解释；
如果通过，它第一次使实际比较结果具有明确的因果含义。

## 十二、本报告不声称

- 不给 A1–A5 排名或 winner；
- 不把 equal information 当成所有 deployment package 的唯一公平定义；
- 不要求隐藏现实任务本来允许观察的 Authority/Target 响应；
- 不声称 randomization 能代替权限隔离和独立 world；
- 不用 leak-only classifier 的一次 chance 结果证明绝对无侧信道；
- 不把本地 synthetic qualification 升格为真实 Authority、人类、物理 Effect 或生产证明；
- 不由 Wave 024 的三项正结果晋升其他 mechanism、A1–A5 或 Problem V1/V2；
- 不预设必须创新。成熟实验平台、容器/权限域、workflow、签名账本和统计设计若完整满足这些门，
  直接组合使用就是正向解决方案。

## 读取边界

本重建直接读取 `research/NOW.md`、本轮 `PROGRAM.md`、Problem V1/V2，以及 Wave 024 的
`QUESTION.md`、`ROOT-ACCEPTANCE.md`、`INDEPENDENT-AUDIT.md`。没有读取其他 Wave 025 Agent
输出，也没有实现 runner 或运行 A1–A5。
