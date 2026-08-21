# Wave 025 F actual-shape feature benchmark

日期：2026-08-01  
状态：`REFERENCE-EXTRACTOR ACTUAL-SHAPE BENCHMARK / NOT FULL EVALUATOR REHEARSAL`

## 输入

输入是 F smoke 已 `CLOSED`/`REVEALED` 的 12 份 `collector-features.json`。F 的 qualification
状态仍是 `NOT_QUALIFIED`；这里仅使用 candidate-visible raw receipt 的实际形状测量 feature
extraction，不读取 role 来选 feature，也不产生 detector/T verdict。

绑定：

- F precommit：`d9a44ab9a5a781a90b70e25ff2a448a329c151ca19998255a2d4d6b45904a77e`
- F closed：`26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e`
- F reveal：`7f698271d211441ad46b6851d8b219238f6e81b87f72afbdcf6de579adb70287`
- reference extractor：`710602d7e259c0cdab151979ab2aeb439279faae270eda40357f24726beb5bf5`
- full feature spec：`8398fb773dca1f7da1edd9a5dcef742f27db7ee954fc9f90de8de56713f1236a`

## 实测

| 指标 | 12-slot 实测范围/结果 |
|---|---:|
| receipt bytes | 11,817–12,498 |
| raw scalar leaves | 528–547 |
| numeric output features | 6,139–6,907 |
| categorical output features | 1,243–1,281 |
| extraction mean | 49.851 ms/receipt |
| extraction max | 66.451 ms/receipt |
| 3,200 receipts 朴素线性外推 | 159.5 s |

D1 receipt 的 leaf/numeric/categorical 数量更高是可观察 canary surface 的预期结构，不能在正式
profile 中被归一化删除。D0/T 也存在实时 process/timing/path 差异；这些是 leak attack 的输入，
不是 runner 应先替 evaluator 清理的噪声。

同一进程内对全部 12 份 receipt 独立重提取两次，canonical output 逐字相等；按 UTF-8 slot ID
排序后，各 output SHA-256 digest 串联的 aggregate SHA-256 为：

```text
e38162a370737ab95f00bf9b51e46bfa4671bfa33cc0158ed6d557e8a0fa5a66
```

## 改变了什么

实际 F receipt 比早期单份报告拥有更多 numeric output（约 6.1k–6.9k，而非约 3.4k），但完整
reference extraction 的 3,200-row 外推仍为分钟级，不支持为了 extraction 成本采用 96 numeric /
128 categorical 或 5,831 learned-width 上限。它加强了 `PROFILE-SELECTION.md` 对完整叶方案的选择。

## 不能说明什么

- 这不是独立 extractor；reference code 与 feature-spec 同源。
- 这没有构建 dense/sparse model matrix，没有运行 C01–C05、Armijo、kNN、9,999 permutation、Holm
  或 class-wise CI。
- 12 个 smoke receipt 不能替代 3,200-row rehearsal、max-size tree/process/truncation fixture、峰值
  RSS/cache/disk/wall ceiling 或双进程 replay。
- 线性外推是成本线索，不是正式成本保证，也不是 blindness evidence。
