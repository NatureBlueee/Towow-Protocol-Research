# G2 Cohort 003：CE-001 relation module

日期：2026-07-30  
状态：`LOCAL SYNTHETIC MODULE IMPLEMENTED / ADVERSARIAL RED REPAIRED /
NO FULL CE-001 RUN / NO FORMAL PROMOTION`

实现目录：
`experiments/wave-012-ce001-power-restoration/g2-relation/`

## 结论

本轮形成了一个可运行的 CE-001 G2 relation module。它不输出单一绿色关系状态，而是输出：

- 按 owner、query、exact RelationVersion 绑定的独立 `OwnerAct`；
- `constituted / understood / claimed / authorized / activated` 五轴 evidence；
- 逐主体 explain-back、claim、refusal、Unknown 与 scoped/blocking opposition；
- `ABSENT / WITHHELD / DISCLOSED / UNKNOWN` private-column evidence；
- typed schema delta、Q/object/schema/formation-evidence 共同绑定的 version preimage；
- T5（映射 CE-001 E0）platform-direct bypass，且不创建 RelationVersion；
- query-before-act raw trace。

`authorized` 与 `activated` 只保存跨线可组合证据：前者标明
`G5_UNVERIFIED`，后者标明 `NO_EFFECT`，并明确 `O_E=NOT_QUERIED_BY_G2`。G2 不把
一般 owner act 晋升为 G5 Authority，也不把 activation intent 晋升为 G6 Effect。

当前结果是本地合成 module conformance，不是 CE-001 八 case 闭合，也没有产生方法赢家。

## 实际内部 Agent

| identity | 职责 | 实际返回 |
|---|---|---|
| `/root/g2_a_reconstruct` | A：独立重建 G2 原始问题与 CE-001 接口 | 五轴非蕴含、E2/T5、private-column/opposition/schema-delta 验收矩阵；提出 contract reopen candidates；只读 |
| `/root/g2_b_implement` | B：实现最小可运行模块 | 初版核心、6 个 fixture 场景、9 项测试、runner 与 raw trace |
| `/root/g2_c_attack` | C：不读取期待赢家，攻击 truth-copy、alias、目标偷换和伪成功 | 新增 8 项 adversarial tests；首跑 `8/8 failures`；留下 `C-ATTACK.md` |

根会话负责重读正典、复跑、解释红灯、修复核心边界、扩为 18 项测试和形成最终研究判断。
这些 Agent 共享模型家族、仓库与研究传统，增加了职责与失败路径隔离，不构成外部独立复现。

## 模块边界

### E2 condition formation

E2 初始输入只有 owner profiles/endpoints，不含预生成 owner-event packet。每个 act 只能在
对应 query 后生成，trace 强制相邻保存 `owner_query → owner_act`。模块依次取得：

1. O_R private-column response；
2. 绑定 `Q_version / object_id / schema / formation evidence` 的 RelationVersion；
3. O_Q/O_V/O_R/O_S/O_P 各自的 constitutive stance；
4. 各主体 explain-back；
5. 各主体 exact-version claim/refusal/opposition；
6. 仅供 G5/G6 继续复核的 authorization/activation intent。

缺失 owner policy 默认 `UNKNOWN`，不自动同意。stale explain-back 只影响对应 owner 的
`understood` 轴，不抹除或伪造其他轴。blocking opposition 会停止该 owner 的后续
authorization/activation intent；非 blocking scoped opposition 同时保留支持与反对来源。

这里的 owner endpoint 是同进程 local synthetic service。它没有 event enumeration API，
但 Python 私有字段不构成对恶意同进程或同目录代码的隔离保证。

### T5 / E0 platform-direct

`CE001-T5-PLATFORM-DIRECT` 映射合同的 `E0-PLATFORM-DIRECT`。只有 fixture 显式标记
`platform_direct_applicable=true` 才能进入旁路；否则拒绝。旁路输出：

```text
path = T5_PLATFORM_DIRECT_BYPASS
relation_version = null
relation_artifact_created = false
second_relation_fact_source_created = false
```

五轴为 `NOT_APPLICABLE_PLATFORM_NATIVE`，不为满足 G2 指标强造 relation。当前 applicability
仍来自冻结 synthetic fixture，并非真实平台/owner 的独立签发。

## 实际运行与数字

命令：

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation
python3 -m unittest discover -s tests -v
python3 run.py
python3 -m json.tool outputs/raw-trace.json >/dev/null
PYTHONPYCACHEPREFIX=/private/tmp/g2-pycache python3 -m py_compile \
  g2_relation.py run.py tests/test_g2_relation.py tests/test_adversarial.py
```

最终结果：

- `18/18` tests 通过；
- 6 个场景：5 个 E2 relation scenario，1 个 T5/E0 bypass；
- 129 个 owner/platform acts；
- 264 条 raw trace records；
- canonical trace digest：
  `cb145099d4fdd560be33913362f67e8d2f53bd0759a7b46b856db94fce7a890a`；
- pretty JSON file SHA-256：
  `31c558b1f5a1fc672128d0d88f09cefdbf298558de47aa13446c20fb68e38cc7`。

关键文件 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `g2_relation.py` | `ade3658a710a72ada077ccdccc506ee3e4ba4c2babc6629eb897cf2baea2c3f3` |
| `fixtures/e0.json` | `335690efd1d91cb387512211db44ba33125615f1547ad7938eaf03482186fb17` |
| `fixtures/e2.json` | `3eac6e2bcfc8c7b94cac37739d1c627e9734763ab4bf09f6db6443db81fd105a` |
| `tests/test_g2_relation.py` | `dfcca73dd1988aa32c41f1c50508a3426c151afe4c2b95bd79cc23bc7f462d7d` |
| `tests/test_adversarial.py` | `75b869f210ddd8f181a85b8446b91da2d30cc1a5f4569dfb263068f82134b1b0` |

## 红灯历史与处置

初版既有测试是 `9/9 OK`，但 C 的独立 adversarial suite 随后得到
`8 tests / 8 failures / 0 errors`。八项红灯均保留：

1. generic AUTHORIZE act 被误标成 G5 Authority 支持；
2. `effect_asserted=false` 仍被误标成 activated 支持，且无 O_E；
3. query owner 与 routed endpoint 不一致仍能生成 act；
4. Q/object mutation 未进入 RelationVersion；
5. 缺失 owner truth 默认肯定；
6. blocking opposition 没进入轴级 opposing evidence，后续 act 仍产生；
7. ABSENT/WITHHELD 共享 relation preimage；
8. controller 可把不适用的 P-stratum case 伪报成 T5 bypass。

根会话逐项修复后，原样复跑 adversarial suite 为 `8/8 OK`，合并 suite 为 `18/18 OK`。
C 的 G6 测试只删除了“必须生成 ACTIVATE intent”这一非必要假设；仍要求若生成 intent，
不得断言 Effect，且轴状态不得出现 `SUPPORTED*`。

另一次 `py_compile` 首跑因系统默认尝试写
`~/Library/Caches/com.apple.python/...` 而得到 `PermissionError`；使用
`PYTHONPYCACHEPREFIX=/private/tmp/g2-pycache` 隔离缓存后通过。这是环境写入边界，不是代码
语义失败。

## 能支持

- 在当前 6 个 local synthetic 场景中，owner act 只能由逐次 query 触发；
- five-axis evidence 分开返回，缺失、误解、stale version、refusal、opposition 不被压成
  一个状态；
- exact Q/object/schema/formation evidence 进入 RelationVersion preimage；
- ABSENT 与 WITHHELD 的 epistemic 差异进入证据绑定；
- parameter/presentation-only delta 不被当作 material，role/action/evidence 等结构变化会
  形成 material delta；
- blocking opposition、owner routing substitution 与不适用 T5 bypass 会 fail closed；
- G2 输出可以由 G5/G6 继续组合，但不能自行替代其 truth owner。

## 不能支持

- 真人理解、现实主体认领、法律 Authority 或真实拒绝；
- 真实 Venue/Circuit C7 Effect、O_E readback、requester/venue Acceptance 或 Settlement；
- 真实 CMMN/CLM/IAM/workflow/HITL/平台产品端到端运行；
- 当前 fixture 的 T5 applicability 是独立现实 owner truth；
- 对恶意同进程、本机或同目录代码的 owner-policy 隔离；
- E2 的真实 formation operator 因果性或 `REMOVE_FORMATION_OPERATOR` 后的现实结果；
- CE-001 八 case、G1–G7 完整 episode、迁移/恢复或生产闭合；
- 强中心、成熟组合、人工制度、通用模型或候选机制的优劣；
- 新机制必要或不必要、V1/V2 一般解、任何正式 claim 状态变化。

真实产品均未安装、未运行，状态为 `NOT_RUN`。

## CONTRACT_REOPEN_CANDIDATE

合同不在本任务写入范围内，以下只登记候选：

1. CE owner 表没有独立 G2 constitution/materiality/comprehension truth owner；实现不能用
   全知 broker 默补。
2. prompt 要求五轴，但 G2 正典禁止晋升 Authority/Effect/Acceptance；应正式规定
   `authorized/activated` 仅为 owner evidence handoff，G5/G6 保持权威判断。
3. T5 是历史 control 名，CE 合同只有 E0；应正式绑定二者，避免新增或重复计分。
4. E2 未冻结 required principals、relation schema、formation operator、method-visible
   prefix 与 remove-operator resolution，因此本轮不能宣称 E2 case 已运行。
5. private-column/opposition/schema-delta 来自本任务与历史 G2 line，但尚未成为 CE 八 case
   的完整 owner/query/scoring contract；当前只能作为 module diagnostics。
6. 历史 activated 布尔曾合并 activation、Effect 与 Acceptance；CE 合同已把 occurrence、
   requester Acceptance、venue Acceptance、Settlement 分开，后续接口必须继续分列。

## 下一接口

下一步应由 episode controller 只把 owner endpoint descriptors、冻结 Q/object 和合法查询
envelope 交给 G2，而不是 owner-event packet。G2 返回当前 raw acts、RelationVersion 和
五轴 evidence；G5 独立取得 current Authority head，G6 独立取得 O_E target-native readback
及 O_Q/O_V Acceptance。只有跨线 exact
`episode_id/Q_version/object_id/operation_id/owner_id/evidence_hash` 一致时才能组合，
且组合结果仍不得反向改写任何 owner act。

本轮未修改 `CE-001-CONTRACT.md`、`research/NOW.md`、`PROGRAM.md`、Problem、LineContract
或机制状态。
