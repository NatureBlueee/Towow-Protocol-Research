# F 批次独立证据审计

> 审计对象：`runs/smoke-v13-20260801-f/`  
> 审计基线：当前 `QUALIFICATION-CONTRACT.md`、`BATCH-EVIDENCE-CONTRACT.md` 与当前选定 `EXECUTABLE-ATTACK-PROFILE.json`  
> 审计边界：只从冻结原始字节、Git object、Docker 收据与当前合同重算；没有读取 runner 源码，也不把 runner 自报的校验结果当作独立证据。本文不是一次新的正式 qualification，也不改变任何 profile、claim 或 hypothesis 状态。

## 结论

F 的冻结证据没有发现字节损坏或内部自相矛盾：七个顶层 JSON 的原始哈希链、三项 commitment、12-slot 人口与区组平衡、执行顺序、slot 文件清单与哈希、Merkle root、三条 collector 输出通道、逐 slot 的五次 `docker exec`、19 条 daemon event，以及 created → running → exited 三阶段 inspect，均可由原始材料独立重算并相互闭合。

旧 evaluator 对新增字段 fail-closed，在它自身冻结的旧 allowlist 下是正确行为；但它把 `evidence_extraction_profile` 和 `supervisor_script_sha256` 视为 unknown field 所产生的 `evidence_integrity=FAIL`，不是 F 在当前 V1.3 合同下的证据损坏，而是 evaluator 与合同接口版本不兼容。旧 evaluator 最终给出的 `NOT_QUALIFIED` 仍然是正确的上限结论，但理由应改写为：F 是 12-slot smoke，不是 3200-slot formal；F 没有绑定或执行当前选定 attack profile；其 11 项外部绑定仍未满足；D0 的候选可见、已注册检测面没有被证明；正式统计、复演、成本和耐久外部锚也都不存在。F 中的 `UNKNOWN` 不得解释为机制失败或负向科学证据。

## 1. 冻结材料与原始哈希

所有七个顶层 JSON 都是递归 key-sort、无多余空白、末尾一个 LF 的 canonical UTF-8 JSON。以下值直接对文件原始字节执行 SHA-256 得到：

| 对象 | SHA-256 |
|---|---|
| `precommit.json` | `d9a44ab9a5a781a90b70e25ff2a448a329c151ca19998255a2d4d6b45904a77e` |
| `anchor-receipt.json` | `16f3d7d494afac916d3ef4af6d1b8697c5cd51770f65f140b7bd6d679aae9cb9` |
| `public-plan.json` | `09a8fc8a57906bc3d4182af7f3b1f08cccf5c36b2a6c6a07c2ccf1a9033acf72` |
| `runner-private-state.json` | `1bc65e04d729bb2ce5c1ebb70583660f88d84e6fe72ab201aba833b9fdeafc22` |
| `closed.json` | `26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e` |
| `reveal.json` | `7f698271d211441ad46b6851d8b219238f6e81b87f72afbdcf6de579adb70287` |
| `evaluation.json` | `7edd1c573ffa042a6b7a30d2d2ab8e7877ffdd8b75643dbd18cc9f7a7c943bc0` |

原始字节重算确认：

- `anchor-receipt → precommit`、`runner-private-state → precommit`、`closed → precommit`、`closed → anchor-receipt`、`reveal → closed` 全部匹配。
- `runner-private-state → public-plan` 匹配。
- private state 与 reveal 的三个 domain、12-slot 执行顺序和 assignment mapping 完全相等；mapping 唯一的字段名差异是 private 中的 `private_canary_token_or_null` 在 reveal 中改名为 `canary_token_or_null`，值逐项相同。
- `runner-private-state.json` 文件权限为 `0600`。这里只证明当前文件权限和揭示后的一致性，不证明运行前没有其他同权限主体读取它。

`precommit.json` 中绑定的输入和程序哈希也可由工作区现存原始字节重算：

| 输入/程序 | 重算 SHA-256 |
|---|---|
| `QUESTION.md` | `8733d30e9f44d5765dfa02b54da1a1e9328cb7af155bff01d283d017ea683377` |
| `QUALIFICATION-CONTRACT.md` | `7a382b8c91af6819b4e66b69691fd250b6b52c77a7f5229a077698790de0c670` |
| `BATCH-EVIDENCE-CONTRACT.md` | `d194f56add3739b66e8056ca1c1fd7297b8bf381b1a27ca6bbb2ee419f62cbbf` |
| collector source | `bc18911c65815da3747755eae44b8f77398d034f9c7c67b54430893c5a1ad699` |
| Dockerfile | `a22d89b34c595ff533dc65323a87e41e4731d08a6cb1da2d15e998b84467f18a` |
| runner source原始字节（未读取内容） | `32614983f5292a708ac38118f587bed50cbb8aa44f5a9c2179a1fe12ae378e3e` |
| 旧 evaluator source | `40864bff4bfa43e323fddebbb129fdc407a1ca366f081288396e7d4ba40bdc95` |
| feature spec | `8398fb773dca1f7da1edd9a5dcef742f27db7ee954fc9f90de8de56713f1236a` |
| public packet | `e634c53f11db2d6de71f4a3d96eb694f3524fb64c2f446af80bcbfdc26fdffb5` |
| supervisor script | `996351d58f726a0e8280f239e056e1f2a0d0398b2122879c752845822a9aa631` |

当前选定 profile 的原始哈希为 `64a4e366a67ec2c12b1194d6fb01fab5b633529035a16f20b22acbf83346e5a7`，其 schema 哈希为 `841c3517e5c9574cc91532c9f7d5e03091667574275dbe25ea9bbbfb5c9d1f8e`。这两个值都没有被 F 的 precommit 绑定；F 绑定的是较早的通用 classifier plan 和旧 evaluator，而不是当前选定 profile。

## 2. Commitment、人口、顺序与 Merkle

对每个 domain 采用 F 实际可验证的字节公式：

```text
SHA256(domain_utf8 || 0x00 || seed_32_raw || 0x00 || nonce_32_raw || 0x00 || public_plan_raw_bytes)
```

使用 reveal 中解码后的 32-byte seed/nonce 与 `public-plan.json` 的精确原始字节重算，三项均匹配 precommit：

| Domain | 重算 commitment |
|---|---|
| `PRIVATE_ASSIGNMENT_ORDER` | `17e4ed19c108e7f7db3108f0721106272db1e333c2d06c1ffd3239908e037c05` |
| `PUBLIC_ID` | `2dbe8ec019258d5ca79e0eb92742c099fc95c6842be00deb8789329c1bd33c15` |
| `MEASUREMENT_PADDING` | `105215737a05b447a31a7cf4effba448527256b9d8f13bf539aa75b4056aead3` |

人口与顺序重算结果：

- public plan 的计数、slot 列表、reveal mapping、reveal execution order、closed slots 和实际 slot 目录都是同一组 12 个唯一 opaque slot ID。
- 六个 `{D0,D1,T} × {calibration,holdout}` 区组各有两个 slot，且每组严格 `R=1, S=1`。
- 12 份 slot receipt 的 `execution_index` 与 reveal order 完全一致；host monotonic start 全局递增，slot 之间没有执行时间重叠。
- `closed.json` 的首末 host 时间分别等于 12 份 receipt 的最小开始时间和最大结束时间。
- `closed.json` 声明 expected=12、actual directories=12、COMPLETE=12、unexpected=0，与磁盘事实一致。

Merkle 独立重算遵循 F 声明的 `SHA256-PAIR-CONCAT-DUPLICATE-LAST-W025-V1`：按 opaque slot ID 排序，以每份 canonical `slot-receipt.json` 原始字节的 SHA-256 为叶，内部节点为两个 raw 32-byte digest 拼接后的 SHA-256，奇数层复制末叶。所得根为：

```text
e80f30077cf32af0ccb2ee09e7790e7789a0885bc7926ba579016426ea747f54
```

与 `closed.json` 完全相同。

## 3. 12-slot 独立逐项结果

| # | Opaque slot | Domain/split/role | host commands | raw 三通道 | exec | events | inspect | 文件/收据哈希 |
|---:|---|---|---:|---|---:|---:|---|---|
| 1 | `s_7a908c429bd76c034ce1717edffeee7b` | D0/calibration/R | 21 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 2 | `s_c89d118fd97c439ec7ab651056b4f666` | D0/calibration/S | 22 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 3 | `s_d86c59f706a1b0c29b6f6f9113ba9fcf` | D1/calibration/S | 15 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 4 | `s_5c227844cf83c9b6242bbb868d17bb34` | D1/calibration/R | 15 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 5 | `s_9cbf1c2bec1f2d7456be3af8383798be` | T/calibration/R | 15 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 6 | `s_ed96a18aa593795736541d8ad3710fab` | D0/holdout/R | 21 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 7 | `s_56d540d297291d01517d98a4584e6d75` | D1/holdout/R | 16 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 8 | `s_5b2da5c0e038ec1d2d4f30e3f71dd116` | T/holdout/R | 15 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 9 | `s_bb1a326053a66b07fba7d50c5ad44b16` | D1/holdout/S | 15 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 10 | `s_335c02205bdd3141aae13a8193edb53f` | T/calibration/S | 15 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 11 | `s_037e8c5d9d3cf0e08a9b148a77d94a9d` | D0/holdout/S | 21 | 相等 | 5 | 19 | created→running→exited | 通过 |
| 12 | `s_fe76fb96000edf4bb63a124fb0611c66` | T/holdout/S | 15 | 相等 | 5 | 19 | created→running→exited | 通过 |

这里的“通过”只表示 F 自身冻结证据的相等性和完整性，不是 scientific qualification。

每个 slot 还满足以下由原始字节独立验证的共同事实：

- `collector-stdout.bin == collector-out.bin == collector-features.json`，逐字节相等；`collector-stderr.bin` 为空；ready 为精确 `READY\n`；exit-code 为精确 `0\n`；supervisor control stdout 为精确 `WAVE025_SUPERVISOR_READY_V1\n`，stderr 为空。
- 实际文件集与 receipt 声明的 13 个文件精确相等；每个文件的原始 SHA-256 同时匹配 slot receipt 与 closed 清单。
- 恰好五次 candidate-specific `docker exec --user 65534:65534 <exact-container> /bin/cat <path>`，路径顺序严格为 ready、exit-code、stdout、stderr、features。五份 exec receipt 均 return 0、stderr 空、stdout 与相应冻结 raw file 相等，且开始时间在 ready 之后并按顺序不重叠。
- daemon event 恰好 19 条：`create,start`，五组 `exec_create,exec_start,exec_die`，最后 `kill,die`。每组的唯一 ExecID 在三条事件中一致，container ID 正确，`exec_die.exitCode=0`，没有额外 exec。
- candidate-specific inspect 恰好形成三个阶段：批次 raw pre-inspect 为 created/pre-start，host-launch 内的 ready inspect 为 running，批次 raw post-inspect 为 exited、exit 0、非 OOM。D0 另有 predecessor inspect，审计时按精确 candidate container name 过滤，没有混入 candidate 三阶段链。
- candidate 的网络、只读根、UID/GID、cap drop、no-new-privileges、PID、memory、CPU、mount 与工作目录在三阶段语义一致。Docker 只把 `HostConfig.OomKillDisable` 从 pre/running 的 `false` 归一为 post 的 `null`；这是原始 daemon 表示差异，不是配置漂移。

## 4. D0/D1 控制面实际证明了什么

### D1

四个 D1 receipt 都包含两个 `visible_canaries` 记录：entry name 与文件内容。相同 role 的 token 在 calibration 与 holdout 一致，collector 输出含位置名与 token hash。因此 F 确实证明了 D1 注册表面在这 4 个样本里存在且可读。

但每个 role/split 只有一个样本，远低于当前 full profile 中 C01 所需的正式支持量；F 也没有运行当前选定 profile。它只能证明 smoke 机制被正确构造，不能提供 C01 sensitivity、specificity 或任何正式区分结论。

### D0

四个 D0 host receipt 证明 predecessor 在独立容器中把 reveal 后对应 role 的 token 写入 `/shared-residue/current-role-token`，成功退出并被移除；candidate 随后把同一 residue 以只读方式挂载，工作目录为 `/shared-residue`。

但 collector receipt 只暴露目录元数据、固定文件名和相同的 51-byte 大小；`visible_canaries=[]`，没有文件内容或 token hash。inode/时间随执行变化，还可能与顺序混杂。因而 F 证明了“前序容器写入并挂载”的 host 机制，却没有证明当前注册特征中存在稳定、role-readable 的 D0 candidate-visible signal。D0 detector sensitivity 仍是 `UNKNOWN/NOT_TESTED`；这是机制与注册面的缺口，不是 F 证据字节损坏。

## 5. Git anchor 的证据边界

`anchor-receipt.json` 指向 Git blob `d78f436b9959a31c29f1c303f8a5a85db3b473af`。本地独立检查确认：

- object 类型是 `blob`，大小 4988 bytes；
- blob 内容的 SHA-256 正是 precommit 的 `d9a44a…`；
- 但该 object 不在 `git rev-list --objects --all` 的可达集合中，`git fsck --no-reflogs --unreachable` 将其报告为 unreachable blob。

所以它是精确的 content-addressed precommit 副本，但目前是 dangling、可被 GC 的本地 object，不能独自承担 durable append-only anchor。receipt 还声称存在用户可见 commentary anchor；本次本地审计无法独立 read-back 该外部记录。`qualifying_external_anchor_present=true` 只是 receipt 内的陈述，不是其自身证明。

## 6. 对旧 evaluator 结论的裁定

旧 evaluator 报告 unknown precommit fields：`evidence_extraction_profile` 与 `supervisor_script_sha256`，因而早停并输出 `NOT_QUALIFIED`。

应分三层理解：

1. **相对旧 evaluator 自身冻结接口，早停正确。** 它没有静默忽略未知字段，也没有在无法解释输入时继续给出科学判断。
2. **相对当前 V1.3 合同，其 `evidence_integrity=FAIL` 原因已经失效。** 当前合同要求这两个字段；F 的字段和绑定可以重算。这里是旧 evaluator schema 落后，不是 F 证据损坏。
3. **`NOT_QUALIFIED` 仍是当前可给出的最高 verdict。** F 只是 smoke，且未绑定/运行选定 profile；正式所需的样本、控制、外部绑定、统计、复演、成本和耐久锚均未闭合。旧 evaluator 因早停留下的 claim `UNKNOWN` 只是“未评价”，不能支持或反驳任何机制主张。

## 7. F 已用事实澄清、但共享接口尚未规范化的歧义

| 歧义 | F 的实际事实 | 尚需规范化的内容 |
|---|---|---|
| 顶层与 receipt schema | F 给出了可工作的具体字段和嵌套形状 | 当前合同多为 prose/“至少”，需冻结 exact schema 与 schema hash |
| 新 precommit 字段 | F 使用 `evidence_extraction_profile`、`supervisor_script_sha256`，当前合同也要求 | evaluator allowlist/version negotiation 尚未同步 |
| Merkle | F 的 sort、raw-leaf、raw-digest concat、duplicate-last 可重算 | internal node domain、奇数层、空树等仍需成为规范，而非仅 run-local label |
| Commitment | F 的三项 commitment 可由 raw 32-byte seed/nonce 和精确 public-plan bytes 重算 | mapping/order/public ID/padding 的确定性派生算法仍未在合同中充分冻结 |
| monotonic 时间 | F 实际使用 start/finish ns，足以恢复全局顺序与无重叠 | 精确字段、时钟来源、跨 host 语义和允许比较尚无 schema 级定义 |
| raw/canonical 边界 | wrappers 与 features canonical；Docker inspect 保留 pretty raw daemon bytes | “所有 JSON canonical”需要明确列出 raw-daemon 例外 |
| post-cut 嵌套 | host command receipts 与 post observation extraction 位于 `host-launch.diagnostics` | 路径、必需项、失败语义和 hash 关系尚未冻结 |
| inspect 阶段 | pre=created，nested=running，post=terminal；`OomKillDisable false→null` | 三阶段命名、candidate 过滤和 Docker normalization 规则未规范化 |
| feature spec 可得性 | 当前工作区可按 precommit hash 找到并重算 | F package 本身不自包含该精确字节，跨环境复核依赖工作区 |
| anchor | Git blob 内容精确匹配 | object 可达性/耐久性、外部 commentary read-back 与 anchor qualification 未闭合 |

## 8. 仍然阻断 formal qualification 的事项

- F 是 `smoke`、12 slots；当前 profile 要求 formal 3200，不能由区组平衡或 12/12 complete 升格。
- F precommit 没有绑定当前选定 profile 的精确 bytes/hash/schema；当前 profile 自身状态仍是 `ROOT_ADOPTED_PREFORMAL_BLOCKED_NOT_EXECUTED`，所有 scientific states 为 `NOT_TESTED`。
- 当前 profile 列出的 11 项 external binding 仍未绑定。
- 缺少绑定精确 D0/D1 family registry 的正式材料；尤其 D0 没有在 candidate receipt 中形成 role-readable 注册特征。
- 缺少 host-only test inventory 及其冻结输入/输出。
- 缺少 full-profile frozen-prediction applicability audit；model-selection/randomization 仍未测试。
- 合同不足以让独立实现者仅凭规范重建 HMAC stream、Fisher–Yates、mapping、public IDs、padding 和 execution order；当前只能验证 reveal 与 commitment 一致。
- 缺少与当前接口一致、被 precommit 绑定的独立 evaluator 及其完整 C01–C05 实现。
- 缺少 3200-slot formal precommit、manifest、外部耐久 anchor、正式运行、double replay、统计与成本证据。
- F package 未自包含 feature spec 与 selected profile 的精确 bytes；Git blob 当前不可达，commentary anchor 未在本地独立 read-back。
- shared interface 的 exact JSON schemas、raw/canonical 例外、Merkle/inspect/monotonic normalization 尚未规范化。

## 最终证据状态

F 可以被保留为一个**内部一致、可逐字节复核、揭示了真实接口缺口的 V1.3 smoke evidence package**。它支持的最强结论是：当前收集与封存链在 12 个受控 slot 上按 F 的实际接口运行一致，并暴露了旧 evaluator 版本漂移、D0 注册信号缺口以及 anchor 耐久性问题。

它不支持：当前选定 profile 已执行、C01–C05 任一项得到科学支持、3200-slot formal 已通过、机制得到 qualification，或 D0/D1 结果可以泛化到正式总体。
