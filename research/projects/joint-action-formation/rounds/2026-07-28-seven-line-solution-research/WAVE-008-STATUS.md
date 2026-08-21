# Wave 008 status

日期：2026-07-29  
状态：`COMPLETE_LOCAL_SYNTHETIC / G3 CAUSAL REBASE AND QHM-1`

## 冻结问题

本波只处理 G3 的一个有界问题：

> 一个原本不合格的联合行动路径在披露、probe、工具或权限变化、承诺和执行后变为合格时，
> 怎样区分既存路径发现、既有能力/授权激活、同一目标下的条件创造、目标变化，以及
> controller 冒权或自证造成的伪成功？

严格 formation 是否发生、现有技术组合是否已经完整解决，以及 PFE/A2A/互动拓扑是否有
独立必要性，是三个不同判断。

## 当前并行线

1. `PRO-G3-001`
   - 外发任务：
     `external/pro-g3-001/TASK.md`
   - SHA-256：
     `fa3619842f76fdc0faf56be21a995e5bbea54d4a1d487b8ce04346975fc5c436`
   - 披露边界：只含 V1/V2 的操作性问题、局部合成来源陈述、失败史和证据等级；没有发送
     HW-C、oracle、私有正文、凭据或本地期待答案。
   - 状态：`COMPLETE / RAW RETURN SEALED`
   - 完整返回：
     `external/pro-g3-001/RESPONSE.md`
   - 返回 SHA-256（rendered text + final LF）：
     `188146740df4693b98023312ad140adb48725a5d6b2cda6d717414019bf06221`
   - 运行凭据：
     `external/pro-g3-001/run.json`
   - 首轮可见思考时长：`13m 19s`
   - 返回要求允许 `none needed`、中心、人类、adapter、成熟组合、无 formation 或
     `Unknown`，不要求通爻、A2A 或新机制具有增量。
2. 本地独立问题重建
   - 状态：`COMPLETE / NOT EXPOSED TO PRO`
   - 当前判断：G3 strict formation 仍为 `Unknown`；最小判别需要 discovery、activation、
     formation 三个配对世界和 matched strong-center + HITL。
3. 本地判别模拟器
   - 目录：`experiments/wave-008-g3-discriminator/`
   - 状态：`16/16 LOCAL CODE REGRESSION / RETAINED NEGATIVE PROBE / NOT G3 EVIDENCE`
   - 目标：冻结同一 `S0/Q/V0/Authority/witness/resource budget`，比较 static search、
     activation runner、formation policy、strong-center + HITL，并攻击 wrong-authority、
     producer-only 与 remove/reverse operator。
   - root 发现并修复 remove-before-apply 伪消融、controller-as-authority 与错误 necessity
     推断；独立 mutation audit 又证明 Q/V0/Principal 未执行、target/Authority 自验、
     label-driven classification、same-policy center 和未绑定 hidden semantics；
     Pro 的 prefix-closure 反例进一步证明当前 `F=FORMATION` 标签没有
     old-closure UNSAT 支撑，不能接受为 G3 结果。
4. G3 综合
   - 入口：`WAVE-008-G3-SYNTHESIS.md`
   - 当前状态：formation event、解决方法与拓扑增量已经拆开；strict formation 仍为
     `Unknown`，旧 fixture 只保留为机制探针。
5. 新并行工作
   - prefix-closure 理论反例与 `C/N/E/T/V` 边界：`COMPLETE / READ-ONLY`；
   - 旧 simulator 独立 mutation audit：`COMPLETE / 10 FAILURE CLASSES REPRODUCED`；
   - QHM-1 causal replayer 新实现：
     `10 WORLDS / 30 RUNS / 18 QUALIFIED / 9 BOUNDED UNSAT /
     3 OPEN UNKNOWN / 15 LOCAL TESTS PASS / INDEPENDENT ATTACK RECHECK PASS`；
   - 当前 bounded 正向结果：strong center、mature workflow composition 与 candidate
     均精确覆盖 6 个 SAT worlds，candidate 独有成功为 0；现有组合解决是通爻正向成果；
   - 已封住的独立攻击：all-stop 空集真值、同构 plan、claimant-supplied registry、
     wrong signed payload、unbound INSPECT response、hidden-world knowledge replay 与
     输出分母漂移。

## 独立性墙

- Pro 首轮只看到冻结外发任务，不看本地独立重建或本地模拟器实现。
- 本地实现者不读取 Pro prompt、过程或返回。
- root 已在两边完成后做第一次差异综合；后反馈修复明确属于 informed rebase，
  不冒充盲式独立证据。

## 当前证据边界

- Wave 007 的 52/52 只支持局部 authority/effect/reuse 组合，不支持 G3 一般 formation。
- 当前没有证据要求创造新协议机制。
- QHM-1 已支持“合成中心/规划/workflow/holder/adapter 组合在同一冻结有限问题下覆盖全部
  bounded SAT cases”；它不证明真实产品、真人流程、robust policy 或 V1/V2 一般问题已覆盖。
- 当前 `F` fixture 没有证明 old `L0+L1` bounded-UNSAT，因此不能支持 strict/global
  formation；新实验必须显式计算 action closure 与 model diff。
- HW-C 仍为 `0/11`，本波没有发送或启动它。
- 本波未使用 AgentKey。
