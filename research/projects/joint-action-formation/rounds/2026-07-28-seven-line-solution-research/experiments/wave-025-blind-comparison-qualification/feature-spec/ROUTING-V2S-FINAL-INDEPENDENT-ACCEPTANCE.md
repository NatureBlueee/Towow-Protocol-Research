# Wave025 V2S routing 最终独立验收

状态：`ACCEPTED_SCOPED_EXECUTABLE_STRUCTURAL_ROUTING_CANDIDATE / NOT_ADOPTED / NOT_FORMAL_CANON`

日期：2026-08-01

本轮只复核 `ROUTING-V2S-POST-FIX-INDEPENDENT-ACCEPTANCE.md` 留下的 routing residual，
没有修改 routing candidate、schema、checker、test 或 audit。旧 feature engine/reference output
没有被当作答案。Receipt semantic admission、C01--C05/model、G/power 和 feature provider 尚未完成
继续保持 `NOT_PROVEN`，但没有被重复算作 routing 失败。

## 1. 冻结对象

| artifact | bytes | SHA-256 |
|---|---:|---|
| `FEATURE-ROUTING-V2S.candidate.json` | 103078 | `0f8e294d31d70fe065df4b8fab963827a0b8c52fdc2d549bc27197da0a848439` |
| `FEATURE-ROUTING-V2S.candidate.schema.json` | 10056 | `1cb50ad5b74c94cfff6fd048b427c964b3e84d22665d6920ae561613d4f25444` |
| `routing_v2s_coverage.py` | 46707 | `6f7ae2d5f5cb7dca2a5d4bb60027e6ba4a985abf9d49f85a35b9fb6d4edf82c8` |
| `tests/test_routing_v2s_coverage.py` | 21518 | `4df567ea9ed4845fdb1b482f01c7818a5e927099a7b0b49b00af7b45b6eba5b5` |
| `ROUTING-V2S-AUDIT.md` | 13179 | `5a631fc306e8d88015c2bc346e681c38411ebdd1402510d9d612808e71c86a4a` |
| `COLLECTOR-RECEIPT-V1.candidate.schema.json` | 27874 | `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209` |
| `V2S-PRIMITIVES.candidate.json` | 12178 | `2786e83d36a4d709915c84b57994b351dc29100a104413b6832c508fa197226b` |

独立 JSON 重编码确认 routing candidate 与 routing schema 都是 compact、key-sorted UTF-8 JSON
加一个 LF。Candidate 对 receipt schema 和 primitives 的 SHA/byte length 均与实际传入 raw bytes
逐项相等。Receipt schema 自身仍是 27874-byte pretty JSON，而不是相同 canonical form；当前 routing
精确绑定的就是这组 raw bytes，所以它不是当前 routing failure。若未来统一 canonical release，
必须重新绑定，不能沿用当前 digest。

## 2. 最终 residual 结论

| residual | 结论 | 独立证据 |
|---|---|---|
| R032/R093 `PARENT` 是否仍带 item index | `ACCEPT` | 两行的 index 0/1 `ORDERED` CTX2 均不同、`PARENT` CTX2 均相同；R093 `immediate_delta_ns` 与 `input_stat_elapsed_ns` 的 `PARENT` 仍不同。 |
| capture 删除、字面化、类型错误是否静态 fail | `ACCEPT` | 对 R028 分别删除 `KEY:{field}`、改成 `KEY:collapsed`、改成 `ORDERED:{field}`，三者都在静态 verify 阶段以 `required capture field must be referenced exactly once as KEY` 拒绝。 |
| BAG 同 `(family, CTX2, base_stat)` 第二 input channel | `ACCEPT` | 给 R109 同一 BAG context 增加 `ALT_NUMERIC/value` 并合法重建 matrix，verify 以 `BAG exactly-one-input-channel collision` 拒绝；独立按正确 key 重算当前表为 1140 owners、零 collision。 |
| 同步增加 pseudo row/spec/matrix/schema/digest 能否自授权 | `ACCEPT` | 同步复制 R053/PBR005、重建 matrix、改 candidate digest，并把调用者传入的 routing schema 放宽到 25，仍以 `pseudo expected universe differs from frozen schema-derived manifest` 拒绝。 |
| “独立审过的 pseudo-selection registry”来源 | `UNKNOWN / NON-BLOCKING PROVENANCE DEBT` | 当前目录中能定位到的是 candidate/schema 中的 24/固定 digest和 checker 常量；没有定位到独立 registry artifact 或它的审查 receipt。因此本验收只接受“当前冻结 checker/schema 能阻止 candidate/schema 同步自授权”，不接受“selection policy 已由可追溯独立 registry 证明”这一更强叙述。 |

最后一项不重开当前 24 项 routing table：我从当前 pseudo specs 独立投影出 24 项、SHA-256 为
`67108f341f517ec93be9c7d79d1b4cc1ec3235bbf6e6b98a7c5d69b070c9f3cd`，并在十二份 F receipt 上
逐事件检查恰好一个 active selector alternative和恰好一个声明 owner，均无冲突。它只限制未来
对“schema-derived / separately reviewed”的证据表述，并继续阻止 formal promotion。

## 3. 独立重建与 F 遍历

我使用不 import `routing_v2s_coverage.py` 的 matcher、runtime selector evaluator、CTX2 encoder、
matrix/BAG derivation、scalar walker 和 pseudo walker复核当前 exact artifacts，得到：

- 641-entry matrix，SHA-256
  `1b5a0a9da3e90f9f945dfb51a8d71f5485244d60e4b2f98356496a2b956e62af`；
- 1140 个 `(family, concrete CTX2, base_stat)` BAG numeric identity owners，零 collision；
- 24-entry pseudo projection，SHA-256
  `67108f341f517ec93be9c7d79d1b4cc1ec3235bbf6e6b98a7c5d69b070c9f3cd`；
- raw receipt/primitives bindings分别为
  `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209 / 27874`
  和 `2786e83d36a4d709915c84b57994b351dc29100a104413b6832c508fa197226b / 12178`。

十二份 F receipt 的独立 traversal 汇总：

| receipts | scalar leaves | pseudo events | unknown | multiply-owned | scalar-one collision | pseudo selector/owner bad |
|---:|---:|---:|---:|---:|---:|---:|
| 8 | 528 | 71 | 0 | 0 | 0 | 0 |
| 4 | 547 | 74 | 0 | 0 | 0 | 0 |

这只证明当前 F 分布上的 executable structural routing，不证明 semantic admission、真实频率、
provider byte conformance、model column closure或 empirical power。

## 4. 原生 suite 与 checker

```text
tests/test_routing_v2s_coverage.py: 56 passed
feature-spec/tests: 125 passed

route_count=109
manifest_leaf_variants=454
manifest_unique_path_atom=371
unowned=0
multiply_owned=0
pseudo specs=9 branch + 7 container + 5 record + 3 absence
channel_stat_matrix_entries=641
bag_numeric_identity_owners=1140
structural_ownership=PASS
admission_or_semantic_completeness=NOT_PROVEN
```

测试绿灯只用于回归佐证；最终接受依赖上面的独立重建、具体 attack rejection 和 raw-byte绑定，
不是测试数量本身。

## 5. 复现命令

在本 wave 目录执行：

```sh
PYTHONPYCACHEPREFIX=/tmp/wave025-routing-final-pycache \
  python3 -m pytest -q feature-spec/tests/test_routing_v2s_coverage.py

PYTHONPYCACHEPREFIX=/tmp/wave025-routing-final-suite-pycache \
  python3 -m pytest -q feature-spec/tests

python3 feature-spec/routing_v2s_coverage.py

shasum -a 256 \
  feature-spec/FEATURE-ROUTING-V2S.candidate.json \
  feature-spec/FEATURE-ROUTING-V2S.candidate.schema.json \
  feature-spec/routing_v2s_coverage.py \
  feature-spec/tests/test_routing_v2s_coverage.py \
  feature-spec/ROUTING-V2S-AUDIT.md \
  feature-spec/COLLECTOR-RECEIPT-V1.candidate.schema.json \
  feature-spec/V2S-PRIMITIVES.candidate.json
```

四个 residual 的现有回归入口为：

- `test_parent_view_drops_item_index_but_keeps_series_identity`；
- `test_deleting_or_literalizing_a_required_capture_reference_fails_statically`；
- `test_second_bag_input_channel_for_same_family_context_base_stat_is_rejected`；
- `test_synchronized_extra_pseudo_row_spec_and_matrix_cannot_self_authorize`。

本轮另执行了 R028 `ORDERED:{field}` 类型错误 mutation；它与删除/字面化一样静态 fail，当前 suite
尚未把这个第三种 mutation 单列成 test，但 checker行为已复核。

## 6. 验收决定

先前两个真正阻断 executable routing 的问题已经关闭：

1. `PARENT` 不再把 item index带进 series parent；
2. BAG uniqueness gate 不再把 input channel错误地放入 collision key。

capture静态完整性和 pseudo同步自授权 residual 也已关闭，current exact 109-row/24-pseudo artifact
在独立 F traversal中零结构冲突。因此签发范围严格限定的：

> `ACCEPTED_SCOPED_EXECUTABLE_STRUCTURAL_ROUTING_CANDIDATE`。

这不是 root adoption，也不把 candidate 改成 formal canon。Formal promotion仍需候选自身已经声明的
semantic admission、canonical release binding、两套 clean-room byte-conformant providers、
C01--C05/model-input closure、holdback/counterexample，以及后续 G/power证据。Pseudo selection policy的
独立 registry provenance也应在任何“independently schema-derived”对外主张之前补齐。
