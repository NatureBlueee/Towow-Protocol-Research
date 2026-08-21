# PT-001 第一轮产品评测合同：D1 / D2

日期：2026-08-01  
状态：`DESIGN_ONLY / SYNTHETIC_FIRST_ROUND / NO_PERCENTAGE_CLAIM / NO_SECURITY_CLAIM`

## 1. 本轮只决定什么

本合同只服务 `PT-001-FUZZY-RESOURCE-COLLABORATION` 的前两项产品决定：

- **D1（澄清）**：在用户只表达模糊价值目标时，系统应怎样组合追问、可撤回假设和已经许可的
  本地上下文，使目标变得足以继续，同时不替用户改写目标；
- **D2（发现）**：目标尚未给出资源名和伙伴名时，目录/ARD/Agent Card、本地 task-relative
  projection、合法强中心推断和渐进披露应怎样组合，何时应诚实保持 Unknown。

`SYNTHESIS.md` 另有一个 D1 编号表示“直接完成还是进入开放形成”。为避免编号碰撞，本合同把它
称为 **R0 路由负控**：至少有一个简单、平台可直接完成的变体，用来检查产品会不会对简单任务
强加 D1/D2。R0 只阻止错误路由，不把第一轮扩张为第三项机制评测。

本轮不决定 RelationVersion、Capability commitment、Authority、真实执行、Effect、Acceptance
或恢复机制；输出只能是前两项产品行为的 `ADOPT / COMPOSE / REMOVE / KEEP_UNKNOWN` 候选。
除非本轮暴露了在成熟组合和人工 fallback 下仍稳定存在的精确残余，否则不得输出 `INVENT`。

## 2. 当前证据边界

PT-001 当前是 `NEW_SYNTHETIC_PRODUCT_TASK_CANDIDATE`。它借用 makerspace/实体原型资源协作作为
设计探针，但不存在已经发生的真实用户 episode。`R7_RESOURCE_REQUEST.md` 只是实验资源清单，
没有任务 `S0`、具体动作、Authority 或后置状态，不能成为本轮现实分母。

因此第一轮可以：

- 检验评测是否能揭露目标改写、答案泄漏、遗漏必要条件、过度披露、误唤醒和虚构推进；
- 比较几个成熟产品行为在冻结合成世界中的结构性差异；
- 为下一轮现实任务 member-check 缩小候选方案。

第一轮不可以：

- 报告 90%、95% 或任何覆盖率/成功率百分比；
- 宣称 PT-001、D1 或 D2 已在现实中解决；
- 把合成参与者的选择写成真实用户、owner 或 Target 的接受；
- 从文件、模型输出、测试绿灯或样本数推导产品有效；
- 涉及或声称网络、容器、主机、权限隔离或防攻击安全性。

## 3. 第一轮竞争产品行为

### D1 arms

| Arm | 用户实际经历的行为 | 允许使用的输入 | 要检验的主要取舍 |
|---|---|---|---|
| `D1-A INTERVIEW` | 只追问，不主动补全 | `FUZZY-INPUT` 与用户本轮答复 | 是否可靠但负担过高，是否穷举问卷 |
| `D1-B HYPOTHESIS+CHECK` | 提出明确标记为候选、可撤回的假设，再请求 member-check | 同上 | 能否减少询问而不把推断冒充偏好 |
| `D1-C PERMITTED-CONTEXT+CHECK` | 先读取明确许可的本地上下文，再追问或提出候选假设 | 同上加逐项许可的 context slice | 检索能否减少负担，还是引入旧目标/越界信息 |

### D2 arms

| Arm | 产品发现路径 | 允许使用的输入 | 要检验的主要取舍 |
|---|---|---|---|
| `D2-A INDEX` | 只使用已声明目录、ARD 或 Agent Card | 当前版本的已公开/已许可索引 | 索引在表达对象上的真实覆盖和 stale 风险 |
| `D2-B PROJECTION` | 只从本地已许可事件形成 task-relative projection | 允许的本地事件与 disclosure policy | 能否暴露未登记但可表达的互补性 |
| `D2-C COMPOSE` | 先索引，再用本地 projection 补足；必要时只提出下一步询问 | 两者的并集，但不含 oracle | 组合是否以可接受披露和误唤醒代价扩大合格机会 |

本轮不实际向外部主体发送 probe。D2-C 可以输出“应向哪个角色询问什么”的候选下一步，但不得
把“准备询问”算成 ACK、能力、同意或机会已经形成。只有 D2 仍留下可由最小互惠 probe 区分的
残余时，才另行触发 D3 合同。

## 4. 冻结包与 fresh truth / solver 分离

每个评测变体必须在任何 arm 运行前形成两个互相分离的面：

### 4.1 `TASK-ORACLE`（只供 truth/evaluator）

至少冻结：

- `S0`：干预前世界和当前时间；
- 用户原始价值、底线、允许的目标变换以及不能替换的内容；
- 必要条件清单及其 owner、何时必须显化、能否保持 Unknown；
- 每个参与方的局部事实、允许披露范围、拒绝和不回应分支；
- latent opportunities、decoys、stale/withdrawn 项与 policy 下不可发现项；
- 哪些下一状态构成真实推进，哪些只是漂亮文本；
- 每项 requirement 的判定说明和结构性阻断项。

### 4.2 `METHOD-VISIBLE-PACKET`（只供 solver）

只包含产品在该时刻实际能够看到的：

- 用户最初自然语言 `FUZZY-INPUT`；
- 当前已许可的上下文切片、目录版本和公开事件；
- 每轮用户模拟器根据已冻结 policy 返回的答复、拒答、纠正或 Unknown；
- 已实际发生的询问与披露日志。

不得包含 oracle 文件名、标签、完整可行路径、隐藏条件、latent opportunity ID、scorer 期待字段、
后续 counter、正确答案摘要或事后评语。solver/controller 的总结不得回写成 truth。

### 4.3 fresh 的操作语义

- 所有 task truth 在 arm 运行前冻结；看到任一 arm 返回后不得补写能让该 arm 得分的 truth；
- 生成 truth/evaluator 的角色不得同时生成 solver 返回；
- 每个 arm 使用独立会话，只读取同版本 visible packet；arm 之间不传递结果或 evaluator 反馈；
- evaluator 先按 oracle 逐项判断，再看 arm 名称；保留原始 transcript、visible packet 与逐项依据；
- 如果发现任何 oracle/答案泄漏，该运行是 `INVALID_RUN`，不是 `FAIL`，不得用于比较。

这些是研究流程上的答案分离，不是对恶意同机进程的安全隔离保证。

## 5. 最小评判单元

不先合成单一总分。最小单元为：

```text
<variant, arm, decision-stage, requirement-or-opportunity>
```

D1 的 requirement 单元至少覆盖一个目标元素或必要条件；D2 的 opportunity 单元逐个保留其
`INDEX_VISIBLE / PROJECTION_EXPRESSIBLE / POLICY_IMPOSSIBLE / DECOY / STALE_OR_WITHDRAWN` 身份。
问题、披露、拒绝、Unknown、误唤醒和路径跃迁作为同一运行的事件单元另行记录。

禁止先将多个条件平均，再用平均值覆盖一个底线失败。跨变体汇总只列：逐项状态、原始计数、
反例与仍未区分的取舍。

### 5.1 直接用户 / Target 指标

本轮的直接用户指标是：用户对 goal 表示的逐项 member-check、主动纠正、拒答/拒绝披露、是否愿意
进入下一步，以及为此实际承担的问题、等待、纠正和披露负担。模型说“用户应该认可”不构成指标。

D1/D2 尚未触发物理动作，所以不存在可以被记为产品完成的实体 Target Effect。本轮能够直接读取的
Target-side 事实只包括：目录/资源条目的当前版本与撤销状态、实际披露日志，以及（若素材中已经
存在）相应 owner 的原生公开声明。拟议 probe、预测回复和 solver 自报均不能补出 Target 事实。
任何 Action Effect 或 Acceptance 字段在本轮都必须保持 `NOT_IN_SCOPE` 或 `UNKNOWN`，不得借合成
评测晋升。

## 6. D1 判定维度

### 6.1 Goal fidelity

oracle 将目标拆成但不限于：价值结果、截止时间、不可接受底线、可协商维度、明确 Unknown、
允许的目标重写边界。对每个元素分别判断：

- `PRESERVED`：进入后续表示仍保持原义；
- `CONFIRMED_CHANGE`：用户看到差异后明确接受修改；
- `OPEN`：仍是 Unknown，产品没有擅自填充；
- `DROPPED`：无依据遗漏；
- `UNAUTHORIZED_REWRITE`：系统以更易完成的目标替换原始价值。

`UNAUTHORIZED_REWRITE` 是结构性阻断，不能由少问问题或找到更多候选抵消。

### 6.2 必要条件发现

oracle 中每个条件预先标注：

- `MUST_SURFACE_BEFORE_D2`：若不确认或显式保持 Unknown，发现会搜索错对象或越过底线；
- `LEARNABLE_DURING_D2`：不应提前把负担推给用户；
- `OWNER_ONLY`：只能由相应主体确认；
- `MAY_REMAIN_UNKNOWN`：Unknown 不妨碍合法进入下一步；
- `IRRELEVANT/DECOY`：询问它不改变可行性或风险。

只有以下三种行为可记为发现：用户答复；用户确认可撤回假设；从许可上下文得到且向用户显示
来源/当前性的候选。无 member-check 的模型猜测只记 `HYPOTHESIS_OPEN`，不算已满足。

### 6.3 问题质量与负担

每一个问题记录：它要区分的路径、对应条件、为什么现在必须问、用户是否已经答过、答复是否
改变下一步。报告原始计数：

- 总问题数、交互轮数；
- 重复问题、对当前决定无影响的问题；
- 需要用户纠正的错误假设；
- 因晚发现必要条件造成的返工轮数；
- 从模糊目标到 `D2_READY` 的用户等待和人工判断次数。

低负担只在 goal fidelity 和必要条件底线满足后比较；“零问题但擅自补全”不能胜出。

### 6.4 Unknown 与 refusal

至少区分：`NOT_YET_KNOWN`、`USER_CANNOT_ANSWER`、`USER_REFUSES_TO_DISCLOSE`、
`OTHER_OWNER_REQUIRED`、`CONFLICT_UNRESOLVED`。系统应保留类型并选择询问其他 owner、缩小路径、
保持 Unknown 或停止，不能把拒答改写为无能力、无需求或默认同意。

## 7. D2 判定维度

### 7.1 合格机会与漏机会

一个 opportunity 只有同时满足冻结 task requirement、在当前版本有效、存在合法下一步且没有把
拒绝/未知冒充同意，才是 `QUALIFIED_OPPORTUNITY`。

逐机会记录：

- `FOUND_QUALIFIED`；
- `FOUND_NEEDS_CHECK`：作为候选呈现，未越级；
- `MISSED_DISCOVERABLE`：在该 arm 合法可见或可表达、且应被发现却遗漏；
- `HONEST_UNDISCOVERABLE`：disclosure policy 下不可发现，产品准确保持 Unknown；
- `INVALIDATED/STALE`：已撤销或过期，未继续使用。

`HONEST_UNDISCOVERABLE` 不是漏机会。不同 arms 的合法可见面不同时，不以拥有更多私有输入的一方
作为无条件冠军；结果必须和披露代价一起呈现。

### 7.2 披露

任何从本地面离开的信息都记录：`sender / recipient / fields / purpose / task-version / time /
retention / allowed-by / refusal-or-revocation`。同时报告：

- 披露字段数与接收者数；
- 为每个合格机会实际需要的最小字段和额外字段；
- 多轮累计披露；
- 拒绝或撤销后仍然发生的披露；
- 没有改变机会或下一问的披露。

“找到伙伴”不能抵消越界披露。零披露且漏掉 policy 允许形成的机会也不能冒充完整发现。

### 7.3 误唤醒与 decoy

`FALSE_WAKE` 指系统把请求或需要回应的候选送给一个按冻结 truth 不可能满足当前关键要求、已经
撤销或仅因宽泛词面相似而命中的主体。仅在本地排序、未触达主体的 decoy 命中记
`LOCAL_FALSE_CANDIDATE`，与真实打扰分开。

每个 wake 必须关联导致它的 evidence 和 arm；无证据的“也许有用”广播不能记为条件创造。

### 7.4 Path progression

第一轮只允许以下单向、有门的状态：

```text
FUZZY_GOAL
→ GOAL_MEMBER_CHECKED
→ CONDITIONS_TYPED
→ D2_READY
→ DISCOVERY_CANDIDATES
→ QUALIFIED_NEXT_STEP
```

允许在任何节点保持 `UNKNOWN`、因拒绝缩小路径、退回上一步或 `PROTECTIVE_STOP`。只有 goal 已被
member-check、所有 `MUST_SURFACE_BEFORE_D2` 已确认或显式标 Unknown，才能进入 D2；只有机会当前
有效、披露合法且下一步未冒充同意，才能进入 `QUALIFIED_NEXT_STEP`。

本轮的终点是一个被正确限定的下一步，不是 relation、授权、执行或完成。

## 8. 结构性底线与阻断项

以下任一项出现，该 arm 在对应变体上不得成为产品默认；不得由其他维度平均抵消：

1. `ORACLE_LEAK / POST_HOC_TRUTH_EDIT`：solver 看到私有 truth/答案或按返回改 truth；运行无效；
2. `UNAUTHORIZED_GOAL_REWRITE`：未获用户确认就替换原始价值或底线；
3. `REFUSAL_ERASURE`：把拒答/拒绝披露推断成无需求、无能力、同意或授权；
4. `DISCLOSURE_VIOLATION`：向未允许 recipient 披露、超出 purpose/fields，或撤销后继续披露；
5. `STALE_OR_DECOY_WAKE`：向已撤销或冻结 truth 明确不合格的主体发出真实唤醒；
6. `FAKE_PROGRESS`：把检索命中、模型猜测、拟议 probe 或 controller 文本写成对方事实、ACK、
   qualified opportunity、关系、授权或完成；
7. `DIRECT_NEGATIVE_CONTROL_FAILURE`：对平台原生一步可完成的 R0 变体强制进入开放形成，且没有
   用户价值或真实性需要；
8. `CRITICAL_CONDITION_DROPPED`：遗漏一个 `MUST_SURFACE_BEFORE_D2` 条件却继续 discovery；
9. `UNTRACEABLE_JUDGMENT`：evaluator 无法指出使用的冻结 truth 和可见 transcript。

对 `POLICY_IMPOSSIBLE` 机会诚实报告不可发现、保护性拒绝或保持 Unknown 均不是阻断；它们可能
是正确产品行为。

## 9. PASS / PARTIAL / FAIL / UNKNOWN

这些状态应用于最小评判单元和每个变体的产品决定，不换算为分数。

| 状态 | 精确语义 |
|---|---|
| `PASS` | 该项所需证据完整，观察到行为满足冻结要求；所有适用底线成立，且没有结构性阻断 |
| `PARTIAL` | 已观察到真实、有用推进，但一个预先列明的非底线部分仍未解决；必须写出剩余项、影响和下一状态，不能把它算作 solved |
| `FAIL` | 有充分证据观察到违反要求、错误状态跃迁或结构性阻断；保护性停止本身不算失败 |
| `UNKNOWN` | 缺少 owner/truth/readback、证据冲突或该项在当前变体不可判断；不得当零分，也不得支持采用 |

另设 `INVALID_RUN`：发生答案泄漏、truth 事后改写、arm 输入不公平或关键记录缺失时，运行不进入
上述四态，不参与机制判断。

一个 arm 只有在所有适用结构性底线均为 `PASS`，且关键目标元素、`MUST_SURFACE_BEFORE_D2` 条件和
路径门禁没有 `FAIL/UNKNOWN` 时，才能成为候选默认。非关键项允许 `PARTIAL`，但必须进入后续产品
待解决清单。任何总体结论必须保留每个变体、机会和 Unknown，不给单一平均分。

## 10. 第一轮最小样本与运行顺序

### 10.1 D1：五个 fresh 合成变体

在同一个 PT-001 任务族内，冻结五个在任一 arm 运行前未被 solver 看过的变体：

1. 基础 makerspace 模糊目标，资源和方法未知；
2. 一个未说出的不可妥协底线会改变资源路径；
3. 用户中途明确修改一个可协商目标；
4. 用户拒绝披露一个问题，但存在可保持 Unknown 的合法路径；
5. R0 direct 负控：现有平台能力已能在同一权威域直接满足简单目标。

三个 D1 arms 分别从相同版本 visible packet 开始。逐项判定，不计算“五个中通过百分之多少”。

### 10.2 D2：两个 fresh hidden worlds

从通过 D1 门禁的目标表示开始，冻结一个 base world 和一个 update/withdraw world。两者合计至少
包含：

- 三个类型不同、在 policy 下可合法发现的合格机会；
- 一个已索引的真实机会；
- 一个未索引但可由许可 projection 表达的真实机会；
- 一个词面相似的 decoy；
- 一个在当前 disclosure policy 下原则上不可发现的机会；
- 一个 stale 或运行中撤销的索引/投影。

三个 D2 arms 使用相同公开版本和各自被允许的输入。每个 opportunity 单独判断；不从合计数量
生成百分比。

### 10.3 顺序

1. truth/evaluator 冻结全部变体、底线和 visible packet；
2. 先运行 R0，确认开放形成不会吞掉平台直达；
3. 独立运行三个 D1 arms，完成 member-check 与门禁判定；
4. 只把满足 D1 底线的输出送入 D2；失败输出保留为反例，不由 controller 修补；
5. 独立运行三个 D2 arms；
6. evaluator 逐单元判定，并运行最小 removal check：去掉关键 context/projection/索引后，声称的
   增益是否仍无变化；
7. 输出产品决定及适用条件，不输出总体 winner 排名。

## 11. 停止点与产品决定

### D1 停止

- 某个最简单 arm 或组合在五个变体上均守住 goal、refusal、Unknown 和门禁底线，并且没有用更多
  问题/纠正/等待换取虚假优势：`ADOPT` 或 `COMPOSE` 为下一轮默认；
- context 检索不改变任何正确决定，或只引入陈旧目标：对 D1 中该部件 `REMOVE`；
- 多个方案都守住底线，但只存在可接受的负担取舍：记录条件化默认，不为产生冠军而扩样；
- 所有成熟组合在同一必要条件上失败：先加入人工 member-check 或缩小任务；残余仍稳定后才提出
  精确 `INVENT_CANDIDATE`；
- 证据不足、变体之间冲突或没有方案守住底线：`KEEP_UNKNOWN`，不得用更多同质合成样本制造确定性。

### D2 停止

- INDEX 已满足所有当前可表达机会与底线：直接 `ADOPT INDEX`，不为“更通爻”强加 projection；
- INDEX 与 PROJECTION 的组合只在有界条件下增加合格机会且未越过披露/误唤醒底线：`COMPOSE`；
- 某部件 removal 后结果和负担无材料差异：`REMOVE`；
- residual 是 policy 下不可发现：正确结论是 `HONEST_UNDISCOVERABLE / KEEP_UNKNOWN`，不是创新失败；
- residual 可由一次最小 purpose-bound probe 区分：停止 D2，另开 D3 的有界评测；
- residual 在成熟组合、合法强中心和人工 fallback 下仍反复存在，并能说明用户价值损失：才形成
  精确 `INVENT_CANDIDATE`，本轮不自动晋升创新。

完成上述判断后停止建设第一轮 evaluator。之后把真假分支留作回归，不继续增加同质变体。

## 12. targeted statistics 与 Wave025 的触发门

### 12.1 何时才需要 targeted statistics

只有同时满足以下条件才扩样：

1. 两个具体 D1 或 D2 方案已经在 fresh 异质变体上通过全部结构性底线；
2. 直接的用户/Target/owner 证据和小型 paired/removal 评测仍不能区分；
3. 剩余问题确实是随机表现、稀有错误频率、近似同分的负担或校准，而不是任务 truth、Authority、
   因果或披露定义缺失；
4. 选错默认机制会造成足以超过扩样成本的产品损失；
5. 已预先写明要区分的效应、错误代价、停止界限和会改变的产品决定。

样本量由该具体问题的最小有意义差异和错误代价决定，不预设 3,200。若区间仍重叠，结论是
`KEEP_UNKNOWN` 或条件化默认，不继续无限扩样。

### 12.2 何时只复用 Wave025 的一个部件

| Wave025 部件 | 本轮后的精确触发条件 | 未触发时 |
|---|---|---|
| runner / frozen packet / transcript | 手工运行开始造成 arm 输入或记录不一致 | 保持任务专用、可读记录 |
| blind holdout / evidence binding | 新 solver 曾接触 oracle，或多 provider 比较需要证明确实收到同一公开语义包 | 以角色分离和语义版本冻结为限 |
| targeted feature/classifier | 必须自动筛除规模化输入污染，且错误分类会改变 D1/D2 机制选择 | 不恢复 C01--C05 大赛 |
| byte-level determinism | 跨 arm 公平性、签名或 evidence 复算确实依赖 exact bytes | 不建设通用数学包装 |
| batch/statistics adapter | 已满足 12.1，且重复手工汇总会产生判断不一致 | 不恢复通用 3,200 population |
| receipt/readback component | 产品状态转换需要事实 owner 的原生事件证据 | 只绑定该事件；不自动晋升/删除研究主张 |
| full Wave025 qualification | 只有一个已命名、高影响产品决定经更小评测仍不能判断，且能逐项证明 full stack 的每个部件会改变该决定 | 保持 `NOT_JUSTIFIED_YET` |

任何涉及网络、容器、主机、权限攻击或隔离保证的依赖只标记
`SECURITY_REVIEW_REQUIRED / DEFERRED_TO_SECURITY_PERSONNEL`，不在本合同设计、实施或验收。

## 13. 第一轮交付物（不预建平台）

实际开跑前只需形成：

1. 五个 D1 oracle/visible 双面变体；
2. 两个 D2 hidden worlds 及逐机会 truth；
3. 三个 D1 和三个 D2 arm 的固定产品行为说明；
4. 每个最小判定单元的状态表和结构性阻断记录；
5. 原始问题、披露、Unknown/refusal、机会和状态跃迁日志；
6. `ADOPT / COMPOSE / REMOVE / INVENT_CANDIDATE / KEEP_UNKNOWN` 的有条件决定书。

这六项足以运行第一轮合成产品评测。只有它们暴露具体、重复且会改变产品决定的测量缺口，才
增加设施；设施一旦回答该决定，就停止扩建并返回产品链。
