# Wave 025 盲比较资格：Red-team preflight

日期：2026-08-01  
状态：`PREFLIGHT ONLY / IMPLEMENTATION NOT REVIEWED / COMPARISON NOT ADMITTED`

## 审计边界

本文只攻击实验设计是否有资格产生盲比较证据，不判断 A1–A5、C1–C3 或任何尚未冻结候选方案
孰优孰劣。本文形成时：

- 已读取 `research/NOW.md`、当前 `PROGRAM.md`、Wave 024 最终 Question/审计/root 材料；
- 已读取 Wave 013 的 fair-baseline/interface/runner 合同、Wave 014 hidden causal twin 合同、
  Wave 015 visibility/hidden-world 合同；
- 没有读取 Wave 025 其他 Agent 的任何输出；
- 没有读取或修改 Wave 025 实现、fixture、candidate、evaluator 或运行产物。

以下是预注册的威胁模型、拒绝门和最低可执行测试，不是已通过的结果。

## 先准确定义“盲”

设：

- `H`：候选不应提前知道的 hidden world/case/treatment assignment；
- `A`：候选 arm 的实际 executable 及其合法 native stack；
- `P`：所有 arm 应得到的冻结 public task、预算和 API 契约；
- `O_pre`：从进程创建开始，直到第一个合法的 owner/Target/world 原生响应为止，candidate
  通过公开输入、文件系统、进程、IPC、网络、错误、时钟、缓存和任何可用工具实际
  能观察到的完整 transcript；
- `τ*`：第一个契约允许因 `H` 而不同的原生响应。

完整资格不是“JSON 字段一样”，而是在冻结的威胁模型下，对每个 arm 分别支持：

```text
H ⊥ O_pre | P, A, budget block
```

该式在工程上只能被有界检验：

1. 对应该逐字节相同的 paired fork，`O_pre` 必须逐字节一致；
2. 对必须重新采样的 opaque 值，只允许预注册的 α-renaming，且其分布必须与 `H` 可交换；
3. 专用 leak-probe 和预注册分类器在 fresh holdout 上不能从 `O_pre` 恢复 `H`
   到高于阈值的水平。

候选当然可以知道自己属于哪种 arm；需要被隐藏的是 world/case、期望结果、未来事件、
私有 topology、其他 arm 结果和 evaluator-private holdout，不是候选自己的方法身份。

`τ*` 之后的合法原生响应可以不同；让 arm 通过合法 query/probe 发现世界事实是解题能力，
不是泄漏。但一个响应只有在以下条件同时成立时才是 lawful divergence：

- 它是 candidate 实际调用的冻结 public API 所允许返回的事实；
- 内容来自对应 truth owner 的原生 receipt/readback，不是 controller 补的 label；
- root 能从 actual transcript 逐字节定位第一处差异及其 causal parent；
- 在该差异之前，错误形状、长度、时序、文件/进程状态和所有旁路仍满足本合同。

## 威胁模型

### 要防的现实行为

1. **会主动观察的 candidate**：不仅读 payload，还会统计长度、计时、解析 opaque 值、
   枚举可读文件/进程/socket/FD，试探错误，利用缓存和跨运行残留；
2. **知道答案的 controller/world author**：为图方便，可能通过 path、运行顺序、进程数、
   DB shape、故障时机或专用 adapter 无意中反射 hidden assignment；
3. **会被历史污染的 runtime/provider**：共享 model conversation、prompt cache、工具 cache、
   文件缓存、连接池、网络重试或上一个 arm 的临时产物；
4. **会因候选而改变的 evaluator**：在看到候选输出后修改阈值、补专用解析器、
   选择有利 mutation，或按 arm label 使用不同成功规则；
5. **会根据 evaluator 调适的 candidate/developer**：读取 private tests、oracle、grader 返回、
   前一次分数或 holdout 差异后重试，从而通过 evaluator 而不是解决任务。

### 保护对象

- semantic case/world label 及其同义改写；
- expected disposition/score、oracle truth、future owner decision、fault schedule；
- private owner/Target topology、Authority stratum 结论、decoy/alternative identity；
- hidden assignment 的随机种子、排序与未公开 commitment preimage；
- 其他 arm 的 input/output/transcript/score 与先前运行残留；
- evaluator 实现、private fixtures/tests、holdout/mutation 生成器和尚未展示的阈值细节。

### 信任与非目标

- root 可以预注册合同、调度与 evaluator，但不得在候选返回后改写；
- world truth owner 和 evaluator 可以知道 `H`，candidate 和其 native provider 不可知；
- 本资格应至少抵抗普通同用户文件/进程枚举；若仍让 candidate 与 hidden world 共享同一
  UID 和可读根目录，完整 blind-comparison 资格直接失败；
- 不声称抵抗 host administrator、kernel/hypervisor 破坏、物理侧信道或外部 provider 主动合谋。

## 历史失败必须变成当前回归

| 历史 | 已经证明的失败 | Wave 025 必须的阻断动作 |
|---|---|---|
| Wave 013 v1 | `case_id`、case-derived run/process/path 直接给 arm | 公开面只从 allowlist 正向构造；语义 label 及变换形式全面扫描 |
| Wave 013 v2 | 删了明文 label，但 private manifest 的普通 hash 可由两候选字典反查 | private commitment 使用 candidate 不可见的随机 root nonce 并每 run unlinkable；跑完字典反查攻击 |
| Wave 013 v2 | `multiprocessing.spawn` 继承 parent `--case` argv | 不信 launcher 声明；从 child 内和 OS 外部观测 actual argv/env/cwd/process title |
| Wave 013/015 | owner 数、endpoint/FD 数、registry digest 可以泄漏 topology | 固定 broker surface；私有 topology 进入另一权限域；主动枚举 FD/socket/process |
| Wave 014 | alpha shape 相同不证明 scheduling/timing 不可区分 | 建立实际 transcript 字节/消息/时序记录与统计等价性攻击 |
| Wave 015 | allowlist、最小 env、fresh cwd、真实 spawn 仅支持 cooperative input boundary | 使用独立 UID/容器/VM 或等价权限域；对可读祖先路径、process topology、FD 和 traffic 发起攻击 |
| Wave 024 | 记录字段同形，但固定 `S→R→U`、同 UID 共享 root 仍使 blindness 失败 | 随机化且区组平衡的顺序；每 clone 独立权限域；candidate 无法枚举任何先前/同批 world |

上表中“已修复”只是对当时窄作用域的历史判断，不能从旧绿灯推导 Wave 025 的新候选、
新多臂 runner 或新 provider 自动继承了同一保证。

## 允许差异与拒绝差异

### 允许的 treatment 差异

- arm 自己的 executable/model/provider/native workflow 及冻结依赖；
- 在共同预算内由 arm 自主使用的计算、人工、query 和工具调用；
- 经由冻结 API 实际获得的 lawful owner/Target response；
- 由 arm 行为自身造成的成本、延迟、错误、拒绝、Effect 和恢复差异。

### 在 `τ*` 之前一律拒绝的差异

- label、label 同义词、预期结果、私有真值或未来事件的任何直接/间接编码；
- public hash/UUID/token 对小型 private candidate set 的可枚举映射；
- path、inode/permission/xattr/mtime、文件名、文件数、文件大小或磁盘占用的 world 相关差异；
- argv、env、cwd、process title/name、PID/PPID 模式、进程/线程数、退出状态；
- FD/socket/port/endpoint/TLS key ID/certificate length 或网络连接数相关差异；
- DB filename、schema、table/index/column 集、`user_version`、page count、WAL/SHM/journal、row count 或 lock 形状；
- status code、exception class、error text/locale/stack trace、response length/count/order、retry/backoff/timeout 形状；
- latency、CPU/memory/I/O、traffic volume、队列深度、调度和时钟 bucket 的 assignment 相关差异；
- arm/world 固定顺序、上一 run 产物、暖缓存、连接复用、model conversation/memory 或 grader feedback；
- 从同一 PRNG seed/state/counter 同时派生 hidden assignment 与 public ID/nonce/padding/jitter；
- evaluator 按 arm ID/path/format 分支，候选看到 private evaluator/tests/oracle，或 evaluator 在候选返回后修改。

## 通道级拒绝清单

下表中任一项可恢复 hidden assignment，该 run 就不是“候选失败”，而是
`BLIND_QUALIFICATION_FAILED`，不得计分。

| ID | 通道 | 可执行的利用方式 | 必须的拒绝/证据 |
|---|---|---|---|
| `L01-LABEL-TRANSCODE` | label/文本 | 搜索 case、expected、world、future event 及其大小写、Unicode、缩写、base-N、压缩、串联和同义改写 | 全部 candidate-visible bytes 命中数为 0；新 public 字段不在 allowlist 时 fail closed |
| `L02-HASH-DICTIONARY` | hash/UUID/token | 枚举全部 private candidate/preimage 及组合，计算常见 hash、namespaced UUID、截断/编码形式，对照可见值 | 普通 private hash 不入 arm；commitment 使用不可见 root nonce、每 run 重随机化且不可链接 |
| `L03-PATH-FILE-SIZE` | path/文件 metadata | 枚举 cwd、祖先/相邻目录、temp root、cache/log/artifact；读 stat、inode、size、blocks、mtime、permission、xattr | 每 clone 的 private root 在另一权限域不可枚举；public tree 的 bytes 与 metadata 均符合冻结等价类 |
| `L04-ARGV-ENV-BOOTSTRAP` | launch surface | child 内读 actual argv/env/cwd/process title，并从 OS 外部观测 spawn/import/bootstrap 短窗口 | 两个视角都只看到冻结 neutral surface；不依赖临时无锁改 parent 全局状态 |
| `L05-DB-SHAPE` | DB/schema/store | 通过可读 DB 枚举 `sqlite_master`、PRAGMA、page count、row count、journal/lock/companion 差异 | private DB 不可读且拒绝形状同形；若 DB 必须公开，则 schema、文件大小、page/journal/lock 在 `τ*` 前等价 |
| `L06-ERROR-PROBE` | error text/shape | 主动发 malformed request、unknown handle、wrong nonce、过量 query、timeout 和 retry，比较 code/class/text/length/stack/latency | 非合法查询统一进入固定 public error family；错误不反射 private topology 或 future schedule |
| `L07-TIMING-TRAFFIC` | timing/traffic | 测量首字节、消息间隔、超时、队列深度、响应大小/数量、CPU/I/O/network traffic，训练分类器 | 优先使用 barrier/padding/bucket 做确定性同形；剩余分布须通过预注册等价和 fresh-holdout 泄漏分类测试 |
| `L08-ORDER-CARRYOVER` | order/跨 run 残留 | 从固定 S→R、case 连续块、arm 顺序、已存在目录/结果或前一轮反馈推断当前 assignment | evaluator-private block randomization/Latin-square；每 clone 独立 root/session；交叉顺序重放不改变结果 |
| `L09-PROCESS-IPC-STATE` | process/FD/socket | 枚举 PID/PPID/start time/name/count/thread/exit status/open FD/socket/port/IPC queue，定位 alternative、decoy、fault process | hidden services 位于 candidate 不可见的 PID/IPC/network namespace 或等价权限域；public broker surface 固定 |
| `L10-CACHE-SESSION` | cache/历史 | 利用 model conversation/memory、prompt cache hit timing、tool/browser cache、DNS/TLS/connection pool、`__pycache__`、上次临时文件 | 每 run 新 session/context/root；冷/暖状态在 hidden class 之间分层平衡；无法观测的 provider cache 显式记 `UNKNOWN` |
| `L11-SHARED-RNG` | random source | 已知 PRNG 算法、公开 token 和调用次数时，回推与其共享 seed/state/counter 的 assignment/order | assignment RNG、public-ID RNG、candidate RNG、padding/jitter RNG 分别使用独立 root 和 domain separation；候选无权读 state/counter |
| `L12-OPAQUE-TOPOLOGY` | opaque handle/topology | 学习 handle 长度、前缀、排序、稳定性、endpoint map 与 owner/Target 数的关系 | 交换或重采样 handle 并重绑 private registry 后，决策只跟 lawful evidence 走；没有稳定 case→handle 映射 |
| `L13-EVALUATOR-ADAPTATION` | evaluator/grader | 用专用 arm parser/阈值，看到输出后补规则，或候选读 private tests/分数后重试 | evaluator/schema/threshold/mutation set 运行前外部锚定；换 arm label/order/path 不改分；评分后不得同批重试 |
| `L14-ADAPTER-DECISION` | arm-specific adapter | adapter 根据 arm 自报 success 补造原生事实，或对不同臂使用宽严不同的 normalization | adapter 只做冻结的无损转码/验签；交叉提交同一 native evidence 时 evaluator 结果不随arm label 改变 |
| `L15-ROOT-FEEDBACK` | seal/历史反馈 | 候选返回后全量改 world/evaluator/tests，再重算本地 hash；或用 grader 的逐轮错误缩小 holdout | 运行前外部 append-only/signature root 锚定全部代码、数据、RNG commitment、顺序与阈值；一次 sealed submission |

## Runner 必须先具备的结构

### 1. 完整 public allowlist，不是 blacklist projection

arm-visible object 必须从 public contract 正向新建，未登记字段默认拒绝。扫描必须递归到嵌套值，
且覆盖 canonical bytes、序列化后形式、字段名、文件名、header、exception 和运行 transcript。

公开 scoring specification 可以告诉候选什么是任务成功；不得给出 private case list、oracle answer、
evaluator implementation bug、holdout/mutation preimage 或预期分支。

### 2. 世界、候选、evaluator 三个权限域

最少需要：

- world/controller 域：持有 hidden assignment、private topology、schedule 和 truth-owner services；
- candidate 域：只持有 public task、固定 broker 和本 arm 的工具/预算，无法读取其他域的文件、
  process list、socket 和 logs；
- evaluator/root 域：只在 candidate 终止、native stores 冻结后读取事实，候选无法读取其代码、
  private tests 或中间分数。

`fresh tmp dir`、不同子进程或 `multiprocessing.spawn` 不是权限域。如果它们仍共享 UID、父目录、
process namespace 和可读 socket metadata，就不得声称完整隔离。

### 3. 两个独立随机平面

至少分离：

```text
PRIVATE: assignment / case order / holdout sampling / private schedule
PUBLIC:  run ID / opaque handles / nonces / padding / candidate-local seed
```

实际上 padding/jitter 若用于掩蔽 timing，应再使用第三个独立 domain，避免 public jitter 泄漏
assignment RNG 的调用位置。每个 RNG 的算法、domain label、seed commitment、调用者和导出物要在运行前
锚定，private seed 在 batch 完成前不公开。

### 4. 随机化、区组化和跨序重放

- world 顺序不可固定；arm 顺序不可固定；
- 按 machine/provider/account/time block 对 hidden class 做平衡，不让冷/暖 cache、限流或日内负载与 case 相关；
- 同一 public clone 需要覆盖相反顺序/交叉序；
- assignment/order commitment 在 launch 前写入候选无权改写的 root；
- candidate 不得从当前时间、run number、queue position 或已存在 artifact 推断序位。

### 5. 一次 sealed evaluation，禁止适配 holdout

- candidate executable/config/dependency/model version 在接触 holdout 前冻结；
- evaluator/schema/threshold/mutation generator 在接触 candidate output 前冻结；
- 同一 batch 没有逐 case 分数、错误文本、grader feedback 或中途修补；
- 重试只允许预注册的同因基础设施失败规则，对所有 arm/world 对称，不得因业务失败重跑；
- batch 冻结后才可揭示 private truth 和发布详细 feedback。

## 最低可执行攻击套件

每项 mutation 都必须重新生成全部普通 hash/签名/封包，使旧 seal 失配不能成为唯一拒绝原因。
攻击使用与正式 candidate 相同的 OS 权限、网络、工具和资源，不能用一个被额外锁死的假 probe 代替。

| ID | 最低可执行测试 | 通过条件 |
|---|---|---|
| `Q01-RECURSIVE-NEEDLE` | 生成 private label/truth/schedule/topology/evaluator canary 的 Unicode、base-N、压缩、分片、字段名和常见 hash 字典；扫描全部 visible bytes | 零命中；每个 canary 的正负控均能证明 scanner 真的消费了对应 surface |
| `Q02-HANDLE-PERMUTATION` | 在不改 private truth/API 的条件下交换 opaque handle、token、UUID、key ID 和排序，完整重绑 registry | pre-`τ*` 行为不随值翻转；合法结果跟原生 evidence 而非 handle 走 |
| `Q03-ACTUAL-LAUNCH-DUAL-VIEW` | 同时由 child 内部和独立 OS observer 记录 binary hash、argv/env/cwd/title、PID/PPID、FD/socket、mount/namespace 和可读 tree | 除预注册的 arm-native executable/dependency 外，hidden class 不能由任一 actual launch 特征恢复 |
| `Q04-FS-DB-PROBE` | leak-probe 遍历所有可达 path，读 metadata/文件大小；对所有可读 SQLite 执行 schema/PRAGMA/page/row/journal/lock 枚举 | private world/evaluator/other-arm 材料不可达；public 差异均属于预注册等价类，不恢复 `H` |
| `Q05-PROCESS-NETWORK-PROBE` | 枚举 process/thread/FD/socket/port/endpoint/DNS/TLS/IPC 与存活/退出状态，在各个 pre-`τ*` 节点重复采样 | candidate 看不到 private topology/schedule/previous arm；固定 broker 在两 hidden class 的实际表面同形 |
| `Q06-ACTIVE-ERROR-PROBE` | 对固定 broker 执行 unknown/malformed/replayed/rate-limit/timeout 探测，记录完整错误 transcript 和时序 | 非 lawful world query 只得到同一 public error family；不因 owner 数、case 或 future fault 改变 |
| `Q07-EARLIEST-DIVERGENCE` | root 对 paired worlds 的 actual I/O、file/process snapshot、时间 bucket 逐项比较，定位第一差异 | 差异不早于 `τ*`，且必须绑定合法 native response；无法定位时返回 `INVALID_BLIND_PAIR` |
| `Q08-TIMING-TRAFFIC-CLASSIFIER` | 对首字节/间隔/超时、message/byte count、CPU/I/O/network 和队列特征运行规则、线性、tree/boosting 与 kNN 分类器 | fresh holdout 上没有预注册 classifier 超过泄漏阈值；同时通过预注册等价检验，不以“差异不显著”代替等价 |
| `Q09-ORDER-CACHE-CROSSOVER` | 用反向、Latin-square 和随机 block 重放 arm/world；交叉冷/暖 cache、连接重用与 provider/account/time block | assignment 与 order/cache block 独立；pre-`τ*` 可见面和结果不由 carryover 翻转；无法隔离的 cache 记 `NOT_QUALIFIED` |
| `Q10-RNG-DOMAIN-SEPARATION` | 冻结 RNG call ledger，尝试从 public ID/nonce/padding/jitter 重建 assignment/order；注入故意共享 seed 的负控 | 四类 RNG 的 root/domain/counter 不共享；负控被泄漏 probe 发现，正式运行无可重建映射 |
| `Q11-EVALUATOR-PERMUTATION` | 对同一份 native evidence 交换 arm label、submission path、run order、opaque ID；做跨臂提交和 adapter swap | 除身份/provenance 显示外，评分与证据判断逐字节不变；只有预注册 applicability 可影响资格 |
| `Q12-EVALUATOR-FREEZE-AND-FEEDBACK` | 在 candidate 返回前/后分别核对 evaluator/test/mutation/threshold hash；尝试读 private grader 与用中间分数发起第二次提交 | 运行前外部锚与运行后引用一致；candidate 不可读 grader；batch 内无 feedback-driven retry |
| `Q13-FULL-LEAK-PROBE` | 启动一个唯一目标是在 `τ*` 前预测 `H` 的专用 candidate，其权限与正式 arm 相同，允许组合 Q01–Q10 的任何特征 | 对 fresh assignment/public RNG/order 的 holdout 不超过预注册优势阈值；任一确定性规则成功即直接失败 |

### 最低量化门

实际冻结合同可以使用更严阈值，但不得在看到数据后放宽。二元 hidden pair 的最低资格建议为：

- classifier/leak-probe fresh holdout 至少 `400` 个 episodes，每 class 至少 `200`；
- 每个 classifier 的 balanced accuracy 在 one-sided 95% 上置信界不高于 `0.55`；
- 另做 label permutation test，并对预注册的多 classifier 使用 Holm 校正；
- timing/traffic 使用运行前冻结、能对应实际可利用窗口的等价容差 `ε_time/ε_bytes`，
  必须通过 equivalence test；只有普通差异检验 `p>0.05` 不构成等价证据；
- K 类世界时，fresh holdout 至少 `200K`，分类优势上限为 `1/K + 0.05`；
- 样本不足、provider cache 无法观察、某个 arm 无法运行同权限 leak-probe，均返回
  `NOT_QUALIFIED`，不以“未发现泄漏”代替证据。

统计门只能说明“预注册 probe 未在当前样本内恢复 assignment”，不是信息论不可区分证明。

## 哪些绿灯仍不构成盲测

以下结果单独或累加都不足以准入比较：

1. public JSON 的 schema、字段数、字段名、长度或 canonical hash 相同；
2. grep 不到 `case_id` / `expected` / `S` / `R` 等明文；
3. 可见值“看起来随机”，或与一个 private hash 不相等；
4. start payload 等长，或 alpha shape 相同；
5. 文档声明 binary/argv/env/cwd/process name 相同，但没有 child 和 OS observer 的 actual receipt；
6. 使用 `spawn`、fresh temp dir、不同 PID 或进程内生成密钥；
7. candidate 参考实现没有写按 label 分支；主动 probe 仍可从可见环境学习答案；
8. 两个 world 最终 score/disposition 相同或不同；结果形状本身不证明 pre-response blindness；
9. 一个 pair、一个 seed、一个顺序或少量重复中 leak classifier 恰好在 chance；
10. 随机化顺序的计划存在，但 assignment seed 已公开、与 public token 共享 PRNG，或候选能读 queue position；
11. 所有单元/集成测试、manifest、checksum、self-hash 和本地 root seal 通过；
12. evaluator 不 import candidate/runtime；它仍可以按 arm label 分支或在看到输出后适配；
13. grep 不到 evaluator 中的 arm ID；专用 parser、path、schema 和阈值仍可构成隐性分支；
14. 当前 candidate 没有主动枚举文件/进程；这不证明它无法枚举；
15. public files 字节相同，但 size-on-disk、mtime、inode、WAL、lock、process count 或 timing 不同；
16. 候选“应该不知道”的口头说明，没有与正式 arm 同权限的 leak-probe 实测。

## 评分准入与拒绝状态

### `QUALIFIED_FOR_BLIND_COMPARISON`

只有在以下条件全部成立时才可登记：

- Q01–Q13 全部在冻结实现、fresh holdout 和正式同权限下通过；
- 每个实际 arm 都独立进行资格检验，不用 A4 或 leak-probe 的通过替代 A0/A1/A2/A3/A5；
- world/candidate/evaluator 权限域、randomization、cache block、顺序、预算、public view、
  lawful-divergence 位置、evaluator 和外部 root 都已预注册并绑定；
- 独立 root 能从 actual receipts 重算，而不信 controller/candidate 自报 `blind=true`；
- 任一不可观察的关键通道都记为 `NOT_TESTED`，不被默认为安全。

该状态只准入实际 blind comparison，不表示 evaluator 的任务真值必然正确，不表示预算已公平，
也不表示任何 arm 能解决任务。

### `STRUCTURAL_PREFIX_ONLY`

只证明 allowlist、字节/α-shape、argv/env/cwd 或某些启动面同形，但 timing、order、cache、
process/FS 隔离、active probing 或 evaluator adaptation 未关闭。该状态不准入计分。

### `NOT_QUALIFIED`

关键测试未运行、样本功效不足、provider/cache 不可观测、某 arm 无法提供同权限 probe，
或没有外部 pre-run root。不得计分。

### `BLIND_QUALIFICATION_FAILED`

任一确定性泄漏、classifier 超阈值、固定顺序/carryover、同 UID 可枚举 private world、shared RNG 可回推，
或 evaluator 发生 arm-specific/adaptive scoring。全批盲比较证据拒绝；可以保留与 blindness 无关的局部软件结果，
但不能保留为胜负或因果比较。

## Independent evaluator 的 fail-closed 规则

1. 不信 runner/controller 的 `blind=true`、same-shape 摘要或只记录净化后字段的 receipt；
2. 重算 actual visible bytes、launch dual view、file/process/DB snapshot、transcript 首差异、randomization/order 和
   leak-probe 原始预测；
3. 任一 arm/world 缺 artifact、只保留 summary、丢失 timing raw data、缺失 cache/RNG/order receipt，
   或原生事实与 root 断链，返回 `INVALID_EVIDENCE` 或 `NOT_QUALIFIED`；
4. 同一 candidate/evaluator 生成的自测不是独立证据；至少一个不 import runner/candidate 的核验器从冻结原始
   receipts 重算资格；
5. 一个 arm 泄漏时，不能继续报告它与其他 arm 的盲比较；其他 arm 只能保留自身未涉及比较的局部结果；
6. 在资格审查完成前，不计算或展示任务 score、coverage、cost Pareto、arm ranking 或 winner，
   避免这些结果反过来促使 evaluator/runner 适配。

## 最高可声称边界

即使全部门通过，最多也只能声称：

> 在本次冻结的 public contract、候选权限、独立 world/candidate/evaluator 运行域、
> 随机化区组调度和预注册 probe 类下，没有一项登记的 deterministic 或 statistical
> 攻击能在第一个 lawful native response 之前，以超过冻结阈值的水平从实际可见面恢复
> hidden assignment。因此这些 arm 有资格进入下一步未评分的 blind comparison run。

这仍不是信息论意义的绝对不可区分，不证明 evaluator 真值、预算等价、Authority/Effect/Acceptance，
不证明真人 A5、现实 provider 或生产世界，更不证明任何候选优胜。资格门只是防止“读出答案”
被误认为“解决问题”。
