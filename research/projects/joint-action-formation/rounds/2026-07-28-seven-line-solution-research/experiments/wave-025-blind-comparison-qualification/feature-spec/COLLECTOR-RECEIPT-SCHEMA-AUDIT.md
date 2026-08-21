# Wave 025 Collector Receipt V1 closed-schema audit

Date: 2026-08-01  
Status: `CANDIDATE / STRUCTURAL-ADMISSION-ONLY`  
Schema: `COLLECTOR-RECEIPT-V1.candidate.schema.json`  
Schema SHA-256: `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209`

## 1. 结论

`COLLECTOR-RECEIPT-V1.candidate.schema.json` 将
`WAVE025_LEAK_ONLY_FEATURES_V1` 的 **collector V1 容器形状**闭合了。根对象和所有可接受的嵌套
对象均使用 `additionalProperties: false`；根对象精确要求 `FEATURE-SPEC.json`
`/input_boundary/accepted_top_level_fields_exact` 列出的 15 个字段。

验证结果：

- F smoke 的 12 份 `collector-features.json`：**12/12 通过**；
- 从 `collector.js` 失败分支构造的合法 shape：**11/11 通过**；
- 未知字段、丢失字段、分支矛盾、TAB vector 破坏、数组伪重复等变异：**21/21 被拒绝**；
- Draft 2020-12 meta-schema 检查：**PASS**；
- 遍历所有宣言 `type: object` 的 schema node，未发现 open object：**PASS**。

可复现入口是
`feature-spec/tests/test_collector_receipt_schema_candidate.py`。它用固定 SHA-256 绑定
candidate schema、`collector.js`、F `precommit.json` 和 `closed.json`，再逐 slot 核对
`closed.json -> slot-receipt.json -> collector-features.json` 的 manifest hash。测试仅读 F；
在验证前后重算 12 份 receipt hash 并要求完全一致。可用以下命令复现：

```bash
python3 -m pytest -q feature-spec/tests/test_collector_receipt_schema_candidate.py
```

从 Wave 025 experiment root 执行时，结果为 `5 passed`；同目录全部 feature-spec tests 为
`51 passed`。

没有发现 12 份 F receipt 与 `collector.js` 实际输出 shape 不一致。发现了若干
**producer 未强制、candidate admission schema 却施加了上限**的边界，它们在第 6 节被明确
标记，不得当成 collector V1 的 producer invariant。

## 2. 形状是怎样从源码得出的

| 位置 | closed shape | 源码依据与关键决定 |
|---|---|---|
| root | 精确 15 keys | `collectFeatures()` 唯一组装成功 receipt（`collector.js:542-609`）；与当前 `input_boundary` 字段集合相同 |
| `hostname.os_hostname` | `{ok:true,value:string,error:null}` 或 `{ok:false,value:null,error:NormalizedError}` | 该字段走 `captureValue`（`463-468, 586-594`） |
| `hostname.etc_hostname` | 直接 `string` 或 `{error:NormalizedError}` | 该字段不走 `captureValue`，是另一种 capture 形状（`588-593`） |
| `identity.user_info` | 五字段 success 对象或只有 `{error}` 的 failure 对象 | `collectIdentity()` 的 `try/catch`（`516-539`） |
| tree | exact `{available,entries,errors,truncated}`；`available:false` 时其他三项固定为 `[],[],false` | `collectTree()`（`204-260`） |
| tree entry | non-symlink 的 11 个必需字段；symlink 额外必需 `symlink_target:string|null` | `statFeature()` 只在 `isSymbolicLink()` 中加入 target（`183-201`） |
| tree error | exact `{path,error}` | `lstat/readdir` 两个 catch 都生成同一 shape（`218-240`） |
| process view | `available:true` success，`available:false` no-proc，或 `available:false` read-error 三个互斥分支 | `collectProcessView()`（`293-357`） |
| process entry | exact success 7 fields 或 exact `{pid,error}` | 每个 PID 的 `try/catch`（`315-335`） |
| process status | 只允许 `name,state,ppid,uid,gid,threads`，六项各自 optional | `parseStatus()` 只复制实际出现的 allowlist line（`280-290`） |
| `status.uid/gid` | 四段非负 decimal，中间是三个字面 TAB | Linux `/proc/*/status` 的实际 F 形状；不把它误当成一个 decimal |
| process self | exact 5 keys；`cgroup/mountinfo/status` 各自是 digest success 或 `{error}` | `337-350` |
| timing capture | uptime 是 number-capture 互斥 union | `captureValue()` 与 `492-493` |
| timing probe | exact success/failure union；三个固定名字与固定顺序 | `measureOperation()` 与 `496-512` |
| timing vectors | 两组各精确 32 个 unsigned decimal string | `TIMING_SAMPLES=32` 与两个 loop（`21, 471-496`） |
| collection window | exact `{start,end}`，每点为 `{wall_clock_ms,monotonic_ns}` | `550-553, 601-607` |

F 样本只覆盖 success-dominant 分支：`os_hostname` 12/12 success，`etc_hostname` 12/12 string，
`user_info` 12/12 success，process 24/24 success。因此又从源码构造了 11 个合法分支：
OS-hostname failure、etc-hostname failure、user-info failure、tree unavailable、process view unavailable、
process-view readdir failure、per-process failure、self-file failure、partial/empty status、uptime capture failure、
timing probe success。它们全部通过，以避免 schema 只是拟合 F 的 12 个正常样本。

## 3. 与当前 input boundary 的关系

当前 `FEATURE-SPEC.json` 要求：

- accepted file 是 `collector-features.json`；
- accepted receipt schema 是 `WAVE025_LEAK_ONLY_FEATURES_V1`；
- root key 必须精确；
- unknown 和 missing 字段 fail closed；
- host-only material 不得拷贝进 predictor matrix。

本 schema 只实现前三项的结构 admission，并将 unknown/missing 向下延伸到每个已知嵌套
对象。它 **不接受 host receipt 与 collector receipt 的 join**，也不会把 challenge、role、slot ID、
host timestamps 等变成 predictor。其根本原因不是它已经证明了 non-leakage，而是这些字段
根本不属于它接受的文档。

## 4. 负例检查

21 个变异都从一份已通过的 F receipt deep-copy 而来，每次只改动对应的局部：

| # | mutation | 必须拒绝的原因 |
|---:|---|---|
| 1 | root 加 `role` | root unknown field |
| 2 | root 删 `cwd` | root missing field |
| 3 | `contract` 加 `score` | nested unknown field |
| 4 | 复制一个 environment item | duplicate-like array structure |
| 5 | `os_hostname.ok=true` 但 `error` 为 object | capture union contradiction |
| 6 | 把 `etc_hostname` 写成 `{ok,value,error}` | 混淆两种 hostname capture |
| 7 | success `user_info` 再加 `error` | success/failure union contradiction |
| 8 | non-symlink entry 加 `symlink_target` | entry branch contradiction |
| 9 | symlink entry 删 `symlink_target` | symlink branch incomplete |
| 10 | tree `available=false` 但保留 entries | availability contradiction |
| 11 | 复制一个 tree entry | duplicate-like array structure |
| 12 | process success 再加 `error` | process branch contradiction |
| 13 | `status.uid` 使用空格分隔 | 不是 TAB vector |
| 14 | `status.uid` 只有三段 | vector arity 错误 |
| 15 | self digest success 再加 `error` | digest capture contradiction |
| 16 | uptime `ok=false,value=1` | capture contradiction |
| 17 | 交换前两个 timing probes | 固定 probe 顺序被破坏 |
| 18 | timing vector 删一项 | 不是 32 samples |
| 19 | collection point 加 `host_order` | nested unknown field |
| 20 | normalized error 删 `path` | normalized error incomplete |
| 21 | 复制一个 visible-canary item | collector 明确 deduplicate 的数组出现伪重复 |

这些检查证明的只是“目标变异被该 schema 拒绝”，不是 collector 没有其他逻辑错误。

## 5. JSON Schema 不能单独证明的约束

1. **UTF-8 byte length。** `maxLength` 计算 Unicode code point，不是
   `Buffer.byteLength(value, "utf8")`。因此 schema 无法证明 `value_byte_length`、
   `token_byte_length`、`cmdline_byte_length` 与对应原始 byte 相等，也无法重算 hash。
2. **原始 JSON 的 duplicate member names。** 普通 parser 在 schema 运行前已经覆盖同名 key。
   `uniqueItems` 能拒绝数组中完全相同的 item，不能代替 raw-byte duplicate-key parser。
3. **canonical byte representation 和顺序。** schema 不证明 recursive-key-sort、compact JSON、
   one-LF，也不证明 environment/tree/process/canary 的 producer sort order。这些应由 raw-byte/
   canonical validator 检查。
4. **文件树深度。** `MAX_TREE_DEPTH=5` 是 collector 的 traversal 过程约束。仅从
   normalized path string 数 `/` 不能证明实际 traversal 过程、root 映射和 symlink 处理；
   需要 collector 单元测试或语义 validator。
5. **跨字段语义与时间关系。** schema 不能单独证明 digest/length 对应原文、
   `start <= end`、进程 PID 唯一且有序、tree path 唯一且有序，或被报告的
   filesystem type 实际存在。

因此正式 admission 至少需要：`strict UTF-8/raw JSON parser -> duplicate-key rejection ->
schema -> canonical-byte check -> cross-field/ordering/receipt-hash semantic checks`。

## 6. Candidate admission caps：不是 producer invariant

用户要求 schema 具有合理的结构和数组上限。本 candidate 因此设置了防御性 admission caps，
但其中只有一部分也由 producer 硬编码强制：

| field | schema cap | collector V1 是否同等强制 |
|---|---:|---|
| tree `entries` | 2048 | **是**，`MAX_TREE_ENTRIES` |
| process `processes` | 256 | **是**，`MAX_PROCESSES` |
| timing vectors | exactly 32 | **是**，`TIMING_SAMPLES` |
| process raw digest lengths | 65536 bytes | **是**，`readProcText` |
| environment items | 4096 | **否** |
| tree `errors` | 8192 | **否** |
| visible canaries | 65536 | **否** |
| subject bytes | 1 GiB | **否** |
| generic decoded string | 1,048,576 code points | **否，且不是 byte cap** |

后四项是 **V1 candidate admission restriction**。它们可以拒绝当前 producer 理论上可生成的合法
receipt：

- 用 4,097 个小 environment variables 启动 collector，源码会 map 全部变量，
  candidate schema 会拒绝第 4,097 项；
- 一个可读目录包含超过 8,192 个 `lstat` 失败的 child 时，`errors.push()` 不增加
  `entries.length`，所以 `MAX_TREE_ENTRIES` 不会限制 error 数；
- environment scan 在 `hits.length` 判断之前运行，而单个字符串的 token loop 也没有
  push 前 cap，所以 `visible_canaries` 不存在真正的 producer maxItems；
- `fs.readFileSync(subjectPath)` 没有 1 GiB 的 collector-level cap。

在这些 cap 被正式采用之前，必须二选一：

1. 在 collector V2 中在 append/read **之前** 强制同等限制，设 `truncated` 或 fail closed，
   并添加边界回归；或
2. 从正式 receipt schema 移除该上限，在原始文件层另做 batch byte-size admission。

`status.uid/gid` 的四段 TAB grammar 同样是 Linux `/proc` admission 约束，不是
`parseStatus()` 自己的 validator；源码只做 trim 和 allowlist copy。所以 status 的六个 key 保持
optional，但 key 出现时 `uid/gid` 必须满足实际接受环境的 TAB vector 语法。若要支持
非 Linux proc provider，应建新 schema/version，不应放宽 V1 后不留证据。

## 7. 不能从本 schema 推出的结论

本 schema 不决定：

- 哪个 receipt path 进入哪个 feature family；
- string/category/ngram/numeric 的 byte preimage、hash domain、index 和 collision 规则；
- ordered view 与 bag view 的语义；
- 哪些观测与 role 存在因果关系；
- D0/D1 是否具有足够 power，或 T 是否 non-leaking；
- collector 的权限、隔离、完整性、可复现性或科学有效性。

因此 `schema-valid` 只能读作：

> 该解析后文档属于 collector V1 candidate admission 容许的闭合 shape。

它不能读作 `feature-valid`、`attack-executed`、`qualified` 或 `scientifically valid`。
