# Cohort 003 G2 / Agent C adversarial attack

日期：2026-07-30  
身份：C（不知期待赢家的敌对测试者）  
处置：`8 ADVERSARIAL RED / CORE UNCHANGED / NO METHOD WINNER`

## 边界

本攻击未读取任何 G2 final，未修改 `g2_relation.py`、fixture、runner、既有测试或输出。
唯一新增文件是：

- `tests/test_adversarial.py`
- `C-ATTACK.md`

这里测试的是本地合成 component model 的接口语义，不是真人 owner、法律 Authority、目标域
Effect、Acceptance、真实平台产品或完整 CE-001 episode。

## 实际运行

既有基线：

```bash
cd /Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation
python3 -m unittest tests.test_g2_relation -v
```

结果：`Ran 9 tests in 0.173s`，`OK`。

首次 adversarial run：

```bash
cd /Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation
python3 -m unittest tests.test_adversarial -v
```

结果：`Ran 8 tests in 0.029s`，`FAILED (failures=8)`，`errors=0`。因 C 不获准修改
核心实现，这 8 项均为“仍红”，不是以放宽断言换取绿灯。

## 八个红灯及其精确观察

1. **G5 Authority 非蕴含失败**
   - 输出没有 `authority_receipts`，但 `authorized.owner_states` 仍出现
     `SUPPORTED_BY_OWNER_ACT`。
   - 当前五轴标签可能把一般 owner act 伪装成 commit-time Authority；不能支持 G5 已闭合。

2. **G6 Effect 非蕴含失败**
   - `owner_acts` 中没有 `O_E` act；所有 `ACTIVATE` 的 `effect_asserted` 都为 `false`；
     `activated.owner_states` 仍显示 `SUPPORTED_BY_OWNER_ACT`。
   - 可支持“模块没有直接声称 Effect”，不能支持 activated 轴蕴含 Effect occurrence。

3. **owner substitution 未阻断**
   - query 内写 `owner_id=O_Q`，却路由到 `OwnerDirectory.ask("O_V", ...)` 时没有抛出
     `ValueError`。
   - endpoint 会按被路由的 `O_V` 身份产生 act；controller 可伪装 owner routing。

4. **material Q / object change 未被绑定或拒绝**
   - 输入加入 `q_version=Q@v2` 与 `object_id=Venue-V/Circuit-C8` 后，输出仍返回 `Q@v1`；
     测试在第一项 Q 断言即红。
   - 因第一断言已终止，当前 run 不能单独证明 object mutation 的后续 hash 断言；它明确
     不能支持 exact Q/object binding，修复 Q 后仍须继续跑 object 检查。

5. **缺失 private owner truth 被默认为肯定**
   - `owner_profiles={}` 仍使 `claimed`（随后还会检查 `authorized/activated`）产生支持态；
     测试在 `claimed` 首先红。
   - 缺失不能等同同意；这是一条 truth-copy/伪成功入口。

6. **material opposition 在 claimed 轴丢失**
   - `O_V` 的 `DO_NOT_SUPPLY_C7` act 存在于顶层 opposition，但其 act id 不在
     `claimed.opposing_act_ids`。
   - 测试还要求反对后不得继续 `AUTHORIZE/ACTIVATE`；由于前一断言先红，该 downstream
     断言尚未在本次 run 中执行，修复 opposition projection 后必须继续验证。

7. **ABSENT / WITHHELD 共享 relation preimage**
   - 两者的 `relation_version.version_hash` 完全相同：
     `05df52a8f32833f5a08dc094176fd658a0df0e1555665878acc737edc6e76814`。
   - 顶层 state/act id 虽不同，但 schema/version 把 epistemic Unknown（WITHHELD）与
     authoritative absence（ABSENT）压成同一关系版本；当前 schema delta 不能支持二者无损可分。

8. **T5/E0 旁路 applicability 可由 controller 自报**
   - `episode_id=CE001-E2-FORGED-AS-PLATFORM-DIRECT`、
     `platform_direct_applicable=false`、`authority_stratum=P` 仍进入
     `PLATFORM_DIRECT`，没有抛出 `ValueError`。
   - 可支持 E0 fixture 能走 relation-free path；不能支持旁路只在真实 applicable E0 上运行。

## 既有绿灯能够支持什么

- owner act 在当前正常 runner trace 中紧跟 query；
- stale explain-back 可被 `understood` 轴排除；
- 明确 `REFUSE` 会停止该 owner 的后续 act；
- 顶层保留 private-column state、opposition provenance；
- 输出没有顶层 `success`/global-green，`ACTIVATE` 没有直接断言 Effect；
- E0 fixture 可生成不创建 relation artifact 的本地旁路。

这些是局部结构性/合成 conformance，不抵消上述 8 个反例。

## 不能支持

- owner truth 与 controller 输入已经隔离；
- act 的 owner 身份不可被 substitution；
- relation version 已绑定 exact Q、target object 和全部 material schema semantics；
- ABSENT 与 WITHHELD 在正式 relation preimage 中可分；
- opposition 在五轴及 downstream act 中保真；
- `authorized` 等于 G5 Authority；
- `activated` 等于 G6 target-native Effect；
- T5 bypass applicability 已由平台/owner truth 独立证明；
- G2 的五轴可推出 G5/G6、完整 CE-001 success、方法胜者或真实产品成功。

## 下一接口

核心修复至少需要：owner/query identity equality gate；缺失 truth 默认 Unknown；Q/object/version
进入冻结 preimage 并对 material mutation fail closed；WITHHELD 保持 Unknown 而非 ABSENT；
opposition 的轴级与 downstream gate；平台 owner 独立签发 bypass applicability；以及为
`authorized`/`activated` 加上明确的 `G2_ONLY / DOES_NOT_ENTAIL_G5_OR_G6` 语义或改名。
修复后应原样复跑 8 项，不应删除红灯或用新的共享 truth label 令其表面转绿。

## 根会话修复处置

C 返回后，根会话保留了上述首次 `8/8 failures`，并逐项修改核心边界：

- owner/query identity 不一致直接拒绝；
- 缺失 owner policy 返回 `UNKNOWN`；
- `Q_version/object_id/schema/formation evidence` 共同进入 RelationVersion preimage；
- ABSENT/WITHHELD 绑定不同 evidence head；
- blocking opposition 进入 claimed/constituted opposing acts，并停止该 owner 的后续
  authorization/activation intent；
- T5/E0 旁路要求显式 applicability；
- authorized/activated 分别输出 `G5_UNVERIFIED` 与 `NO_EFFECT`，O_E 保持 G6 边界。

修复后运行：

```bash
python3 -m unittest discover -s tests -v
```

结果：`18/18` 通过。为接受更强的 fail-closed 行为，G6 敌对断言仅删除了“必须生成
ACTIVATE intent”这一项；它仍要求若有 ACTIVATE 则 `effect_asserted=false`，且 activated
轴不得出现 `SUPPORTED*`。这没有放宽 Effect 非蕴含门。

仍未关闭：T5 applicability 目前由冻结 fixture 显式给出，不是独立真实平台/owner 签发；
Python 同进程私有字段不是恶意本机进程隔离；当前结果仍是 local synthetic module
conformance。
