# D0 control family design candidate

状态：`DESIGN_CANDIDATE_NOT_IMPLEMENTED_NOT_BOUND`  
候选 family：`D0_RESIDUE_OPAQUE_BASENAME_V1`  
作用域：只修复 D0 predecessor/shared-state control 的注册信号；不改变 runner、collector、FEATURE-SPEC、合同或当前 attack profile。

## 结论

最小而足够尖锐的 D0 control，不需要让 collector 读取 residue 文件内容。让 sacrificial predecessor 在该 slot 独占的 shared residue 中创建**恰好一个空文件**，其 basename 从两个等长、同形状、预先私密登记并按 role 映射的 opaque tag 中选择；candidate 随后以 `/shared-residue` 为 CWD、只读挂载同一 residue。

现有 collector 已把 CWD 的目录树记录到 `/directory_trees/cwd`，其中每个文件的相对 `path` 会进入 `F04_DIRECTORY_AND_SHARED_STATE` 的 `path_exact_category`。因此，在 D0 calibration 中，C01 可以冻结“某一 exact basename category 出现则判一类，否则判另一类”的单 token presence 规则；相同 role→basename 映射跨 calibration/holdout 保持不变，规则可直接泛化。T 不创建 predecessor、不挂载 `/shared-residue`，也不拥有这两个 basename。

这只是一个可实现设计和可证伪预测，不是已实现结果，也不关闭 `B04_D0_PRIVATE_FAMILY_REGISTRY_UNBOUND`。

## 1. 为什么 F 的旧 D0 不足

F 的 predecessor 确实写入了 role-correlated token，但文件名固定为 `current-role-token`，两个 role 的文件大小又同为 51 bytes。collector 的 `collectVisibleCanaries()` 只扫描 environment 与 `/challenge`，不会扫描 CWD 文件内容；它对 `/shared-residue` 只通过 `collectTree()` 输出 path 和 metadata。因此 F 中 `visible_canaries=[]`，而 CWD 树只有相同文件名、相同大小及不稳定 inode/time，无法形成跨 split 稳定的登记 role signal。

本候选把 role 信息放到 collector 已经登记的 **F04 exact path**，而不是假定 collector 会读取它实际上不会读取的内容。

## 2. 候选机制

### 2.1 公开、role-free 的 family template

public plan 最多可以冻结以下 role-free 事实：

- family ID：`D0_RESIDUE_OPAQUE_BASENAME_V1`；
- D0 使用 sacrificial predecessor；
- shared residue 在 candidate 内的 destination 与 CWD 都是 `/shared-residue`；
- residue 每 slot 独占，host source 只由 opaque slot ID 派生，不由 role 派生；
- predecessor 后、candidate 前，residue 必须是只含一个空 regular file 的树；
- basename 语法为 `d0-residue-v1-` 加 32 个小写十六进制字符；
- 两个合法 basename 必须等长、同字符类、彼此不同；
- candidate 挂载只读，T 没有此 mount、CWD、predecessor 或 session。

public plan 不得包含：两个 tag 的 bytes/hash、tag→role 映射、registry seed、每 slot role、执行顺序，或含实际 tag 的 predecessor command。

### 2.2 私有 family registry instance

在 external anchor 之前生成并冻结一份单独的 private registry instance：

1. 用 OS CSPRNG 独立生成两个不同的 16-byte tag，编码为 32-char lowercase hex；不从 role 名、slot ID、order、phase 或 public seed 派生。
2. 私下把两个 tag 一一映射到两个 role。该映射在本 family 的全部 100 个 calibration 与 100 个 holdout D0 slots 中保持不变。
3. exact registry bytes 的 SHA-256 绑定到当前 profile 的 `D0_private_family_registry_sha256`，并在 external precommit anchor 之前完成；registry、tag 和映射不进入 public plan，也不挂入 candidate。
4. close 后才 reveal registry bytes；evaluator 先从无 label receipt 抽取 features，再用 reveal 做 role/family join。registry 只能作为 subgroup selector 与预期 signal 审计材料，不能直接成为 predictor。

本设计文件不是该 private registry instance；它不含实际 tag 或 role mapping。当前同目录已有 `PRIVATE-CONTROL-REGISTRY.preformal-candidate.json`，其中 D0 使用新生成的两枚 16-byte CSPRNG tag，D1 按要求复用 F reveal 中的当前 token。后者已经在旧 smoke reveal 中公开，所以整个实例明确标为 preformal candidate，不能作为 formal 的新鲜私有 registry，也尚未绑定 profile/precommit。

### 2.3 每个 D0 slot 的 predecessor→candidate 链

1. host 创建由 opaque slot ID 唯一定位的空 residue root；source path 不含 role、phase、block 或 execution index。
2. 只有 predecessor 以 UID/GID `65534:65534`、可写挂载该 root。predecessor 根据 host-private registry mapping，用 exclusive create 生成：

   ```text
   /shared-residue/d0-residue-v1-<32-lowercase-hex-role-tag>
   ```

   文件为 0 bytes、regular file、固定 mode；不得创建 symlink、第二个 entry、role 字面量或其他输出。predecessor 自己把目录收敛到冻结 mode 后退出。
3. host 在不改写 residue 的前提下保存 predecessor 的 image/config/events、pre/post tree snapshot 与退出收据，验证 predecessor 前为空、后恰好一个合法 marker。
4. predecessor 被移除后，candidate 把**同一 source** 只读挂载为 `/shared-residue`，CWD 固定为该目录；candidate env、argv、hostname、resource envelope 不因 role 改变。
5. candidate 完成及 post-inspect 冻结后才清理该 slot root。清理失败则 quarantine，绝不把该 root 复用到任何后续 D0 或 T slot。

“predecessor 产生”在这里仍依赖受信任 host/daemon 和隔离边界；它不是抵抗同权限恶意 host admin 的密码学证明。

## 3. C01 为什么应当可检出

现有语义链是：

```text
predecessor-created basename
  → collector receipt /directory_trees/cwd/entries[*]/path
  → F04 path_exact_category
  → C01 single_exact_categorical_token_presence
```

按当前选定 profile，D0 calibration 与 holdout 各 100，每个 split 内每 role 50。对任一 role tag：

- calibration 中，该 exact path category 在对应 role 的 50 个 receipt 全部出现，在另一 role 的 50 个 receipt 全部不出现；
- C01 的 minimum total support=10、minimum per predicted class support=5 均满足；
- 两个 role basename 都能形成 complexity=1、calibration balanced accuracy=1 的 presence/absence 规则；无论 UTF-8 tie-break 选择哪一个，都有相同 holdout 预测；
- 当前 FEATURE-SPEC 不是普通单尾 `alpha=0.05`：它对两个 class 做 Bonferroni，冻结 `class_tail_alpha=0.025`。若 holdout 50/50 全部恢复，单类 50/50 成功的 Clopper–Pearson 下界为约 `0.9288782635`，仍高于登记阈值 `0.90`。

以上是设计所产生的**事前可检验预测**。只有独立 evaluator 从冻结 raw receipt 按 FEATURE-SPEC 重建 exact category、实际运行 C01，并在 fresh holdout 得到相应结果后，才能称 detector sensitivity 成立。

为防止“C01 被另一个副作用救活”，evaluation 还必须报告最终冻结规则的 feature family、source path、transform 和 category hash；若 primary rule 不来自登记的 marker-path exact category，本 family 的因果特异性不得宣称通过。

设计级 sanity check 已直接调用当前 collector 导出的 `collectTree()`，对一个临时 CWD 中的示例同形 marker 做观察：返回 `available=true`、`errors=[]`、`truncated=false`，并逐字保留 marker relative path、`type=file`、`mode=0o0400`、`size=0`。这只验证现有 collector 能观察该候选 surface；它没有模拟 container UID、predecessor provenance、feature extractor、C01 或 T exclusion，不能升格为实现/运行证据。

## 4. T 不进入该信号的必要条件

T 的排除不是“计划里没有”就算完成。至少要独立重算：

- T 的 actual inspect 中不存在 destination `/shared-residue`、任何 D0 residue source/source hash 或额外 bind；T 的 CWD 仍为冻结的 role-free `/app`。
- T 没有 predecessor container、predecessor command receipt、共享 session 或 residue lifecycle event。
- reveal 后，对全部 T 的 candidate-visible raw receipts 做 byte/category audit，两个 exact basename、其完整 SHA-256 category 以及任何 `/shared-residue` tree entry 的计数都必须为 0。
- host source inventory 证明 D0 residue roots 仅挂给对应 predecessor 与对应 D0 candidate；source reuse、跨 slot mount 或 cleanup quarantine 失败均 fail closed。
- 一个预注册的 preformal ingress test 先运行 D0 marker，再运行 T；T raw receipt 中出现 marker 或 mount 即否定该实现，不能归为普通噪声。

T 中共同存在但 role-free 的 public challenge、collector、image 与 resource envelope 不得被当作 D0 signal；challenge 只允许作为 stratum selector。

## 5. 额外改变的 surface 与审计

| Surface | 是否目标信号 | 可能造成的错误 | 必须怎样审计 |
|---|---|---|---|
| marker 的 exact basename/path | 是，唯一登记 primary signal | 未跨 split 复用会触发 singleton 失败 | 冻结 registry；核对每 role 50 calibration + 50 holdout 使用同一 basename；C01 rule-source 必须指向 F04 exact path |
| marker path 的 n-gram、shape、tree-record 表示 | 是同一干预的派生表示，但不是 primary | 可能让其他 classifier 看似提供独立确认 | 做 marker-derived feature attribution；删除所有由 marker path 派生的 features 后重跑 shadow ablation，不把剩余模型共识算作 primary sensitivity |
| file/root 的 inode、device、ctime、mtime、directory size/nlink | 否 | 分配顺序或 filesystem drift 与 role 偶然相关，产生 false fail/false sensitivity | 固定可固定的 mode/uid/gid/size；逐叶 role/order permutation 与 Holm audit；marker-path 全量 ablation 后不得仍稳定恢复 role |
| `/shared-residue` CWD 与额外 read-only mount | 否；只是 D0 family envelope | challenge identity 可被误当 role predictor，或误进入 T | 在 D0 两 role 间逐字相同；challenge 仅作 stratum selector；T inspect/mount/receipt 做零存在审计 |
| predecessor 的 CPU、I/O、cache、daemon event 与 elapsed time | 否 | 当前 role token 的写入差异或执行顺序影响 timing/process features | 两 tag 等长、文件皆 0 bytes、同一代码路径；冻结 predecessor resource envelope；对 F05/F06 做 role/order association 与 role-null placebo predecessor audit |
| residue host source path、container name、opaque slot ID | 否，且 host-only | role-coded host naming 可污染 mountinfo hash或被错误 join 为 predictor | source/name 只从 independent opaque slot ID 派生；禁止 role/phase/order；host fields 永不进入 predictor；做 forbidden-field mutation test |
| actual tag/mapping 出现在 host receipts | 不是 predictor，只是 provenance/reveal | evaluator 可能把 private registry/host command 偷渡进 feature matrix | feature extraction 必须先于 reveal join；full scalar-leaf partition 与 forbidden-source mutation test必须通过 |
| stale residue 或 cleanup failure | 否 | D0 tag 串入其他 D0 family 或 T，破坏因果归属 | 每 slot unique root、无复用；失败 quarantine；全 batch source ownership graph 与 T zero-ingress audit |

建议的 preformal 因果审计不是扩大 formal claim，而是验证该 control family 是否真的只靠登记 signal 工作：

1. **role-null placebo predecessor**：执行同一 container、挂载、文件创建和清理，但两 role 都使用同一固定 basename；F04 marker exact path 以外不得稳定恢复 role。
2. **mapping inversion**：在单独、不可并入 formal 的 rehearsal batch 中交换两个 tag→role mapping；登记 exact-path rule 的预测方向必须随 mapping 反转，而 metadata/timing 关联不应保持原方向。
3. **marker-derived ablation**：从独立 feature vectors 中移除 exact path 及其所有 n-gram/shape/tree-record 派生项；任何残余 role recovery 单列为非目标 side effect，不能补救 primary C01 失败。
4. **T ingress sentinel**：D0 后紧接 T，检查 raw receipt、inspect、mount source graph 和 feature category 均无 marker。

## 6. Fail-closed 条件

出现任一情况，本 family 应为 `DETECTOR_INADEQUATE` 或 evidence-integrity failure，而不是把 T 判绿：

- registry 未在 external anchor 前冻结、哈希未绑定，或 calibration/holdout 使用不同 role tag；
- predecessor 前 residue 非空，后不是恰好一个 0-byte regular marker，或 marker 不是 predecessor 创建；
- actual basename 不匹配 private registry，source path/candidate name 含 role，或同一 residue 被跨 slot 复用；
- collector CWD tree unavailable/truncated/error，marker path 缺失，或出现第二个未登记 entry；
- C01 最终 rule 不来自登记 exact path，minimum support 不足，或 holdout 下界未达到当前阈值；
- T 出现 D0 mount、predecessor、marker bytes/category、source reuse 或共享 session；
- non-target ablation 仍恢复 role，但没有被单列为 side-effect/confounding finding；
- 实现需要修改 collector/FEATURE-SPEC/profile/合同，却没有先形成新的冻结版本和 adoption/anchor。

## 7. 本候选不宣称

- 未实现 predecessor、runner support、正式所需的新鲜 D1 private registry、profile/precommit binding、evaluator rule attribution 或运行审计；当前只有严格 schema、公开 registration、preformal private candidate、generator 与静态/生成测试；
- 未运行 smoke、rehearsal 或 formal；
- 未证明 C01、D0 sensitivity 或 T isolation；
- 未证明该人工 exact-path control 代表所有真实 shared-state leak；
- 未关闭当前 profile 的任何 blocking external binding；
- 未授权修改或重新冻结当前合同、profile、runner、collector 或既有 evidence。
