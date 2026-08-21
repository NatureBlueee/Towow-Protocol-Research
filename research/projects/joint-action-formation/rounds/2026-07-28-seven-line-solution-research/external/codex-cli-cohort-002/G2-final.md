# G2 第二批 Codex CLI 独立研究结论

状态：`G2-O1 IMPLEMENTED / LOCAL SYNTHETIC DISCRIMINATOR PASS`

日期：2026-07-29  
实现目录：`experiments/wave-011-g2-owner-evidence-open-schema/`

## 结论先行

本轮把第一批 G2 的“单进程 owner oracle + 预编码答案风险”推进成了一个可攻击的
12-world owner-evidence/open-schema 候选。最终结果不是“发现了 G2 专属引擎”，而是：

1. 在当前脚本化 owner evidence、公开观察预算和 Authority endpoint 下，structured human
   institution、equal-envelope strong center、本地成熟组件组合、signed replicated state
   四臂均能逐项重建五轴；每个 world 的四臂五轴完全相同。
2. 当前 12-world 合成分母中，没有观察到成熟/强中心方案之外的
   relation-semantic residual，也没有观察到 replicated state 的形成语义增益。
3. 这是现成路线的正结果，不是 G2 的失败：若人工制度、强中心或成熟组合完整解决原问题，
   就应直接采用。当前证据只支持它们在本 benchmark 上的合成 conformance。
4. T5 controls 确实旁路 relation machinery：四臂均走 platform-direct，未创建
   institution/central-decision/mature-composition/replicated relation artifact。有效拒绝也
   保持为正确结果。
5. 仍不能把结果写成“真实成熟产品已经验证”或“真实 owner 已理解并认领”。成熟组合臂只是
   本地组件语义模拟；owner 是 private oracle 编排的脚本进程。

## 实际多 Agent 研究

本 CLI 会话实际并行启动了三名内部研究者，没有模拟：

| 内部研究者 | 实际任务 | 主要交付 |
|---|---|---|
| `/root/g2_kernel` | A：原生 G2 kernel、open-schema、局部认领 | `g2o1/kernel.py`、12-world public fixture、private oracle、`A-KERNEL.md` |
| `/root/g2_simulator` | B：owner-evidence simulator | actor/evaluator/method workers、四臂 runner、`B-SIMULATOR.md` |
| `/root/g2_attack` | C：攻击 owner oracle、预编码 schema、2×2 混淆、false formation | `tests/test_g2o1.py`、`C-ATTACK.md` |

根会话负责读取正典、整合、发现 T5 伪旁路风险、补最终 T5 硬断言、冻结输出和形成研究判断。

## 冻结分母与实现

- 4 `T2_BLIND`：schema delta/parameter-only、理解/误解、current/stale stance；
- 4 `T4_HELD_OUT`：column absent/withheld、局部异议、relation-level coupled constraint；
- 2 `T5_CONTROL`：平台直接完成、平台直接有效拒绝；
- 2 `AUTHORITY_PRESSURE`：shared institution + equivocation、plural authorities +
  partition/recovery。

公开 fixture 不含 `relation_valid`、`material_change`、`opposition_preserved`。每个
Principal 与 world/schema、constitution、private-column、Authority、target/Acceptance、
topology truth owner 均由独立 actor 子进程生成随机 Ed25519 key，只返回 public key、
签名事件和 PID。controller 与 method worker 不接收 private key。

五轴分别输出：

`constituted / understood / claimed / authorized / activated`

另报 schema change、private-column recall、provenance/opposition、stale/revoke、
duplicate reservation、partition recovery 与粗成本。Authority topology 来自 world；
state placement 来自方法臂，二者没有互相推导。

## 冻结运行结果

`python3 runner.py` 的本轮冻结输出为 `outputs/results.json`：

- 12 worlds × 4 arms = 48 runs；
- 五轴 true 计数：
  `constituted=24 / understood=44 / claimed=24 / authorized=32 / activated=24`；
- method axes 对 event-derived reference：`240/240`；
- schema-change：`48/48`；
- opposition provenance round-trip：`48/48`；
- 106 个 distinct owner actor PIDs；
- 单次冻结 runner：`51.28s`。

逐 world 五轴（四臂相同）：

| world | constituted | understood | claimed | authorized | activated |
|---|---:|---:|---:|---:|---:|
| T2-01 | 1 | 1 | 1 | 1 | 1 |
| T2-02 | 0 | 0 | 0 | 1 | 0 |
| T2-03 | 1 | 1 | 1 | 1 | 1 |
| T2-04 | 0 | 1 | 0 | 0 | 0 |
| T4-01 absent | 0 | 1 | 0 | 0 | 0 |
| T4-02 withheld | 0 | 1 | 0 | 0 | 0 |
| T4-03 local opposition/duplicate | 0 | 1 | 0 | 0 | 0 |
| T4-04 coupled constraint | 1 | 1 | 1 | 1 | 1 |
| T5-01 direct success | 1 | 1 | 1 | 1 | 1 |
| T5-02 direct refusal | 0 | 1 | 0 | 1 | 0 |
| AUTH-01 shared institution | 1 | 1 | 1 | 1 | 1 |
| AUTH-02 plural authorities | 1 | 1 | 1 | 1 | 1 |

T5 的五轴保留 benchmark 的 owner/action 分解，但 method output 明确
`platform_direct=true / relation_artifact_created=false / schema_reopen=false`，四臂均为
4 operations。

## 攻击与修复历史

保留红灯而不是只报最终绿灯：

1. 首轮：`1 failed + 11 errors`，fixture/runner 尚未齐；另发现 schema delta 只报路径、不报
   added values。
2. 第二轮：结构测试 `3 passed`，完整 runner 在 45s 合同下超时并产生 9 setup errors；
   测试上限升到 180s，这只是允许继续语义攻击，不是性能通过。
3. 第三轮：`8 passed / 4 failed`；两项为攻击 matcher 自身误报，真实红灯包括 shared
   equivocation 未 fail-close/recover。
4. 第四轮：`9 passed / 3 failed`；暴露 stale 与 revoke 被合并成同一事件，无法观察
   stale current-head。
5. C 稳定无并发复核：`12 passed in 101.72s`；包含 private `expected.axes` 全反转后的
   第二次 48-run，measured axes/diagnostics 不变。
6. 根会话补入 T5 真 platform-direct 断言后最终复核：
   `13 passed in 201.78s`。较长用时是两次完整 48-run 子进程执行的实际成本负结果。

## 证据边界与当前判断

支持：

- `SCRIPTED_OWNER_CONFORMANCE / LOCAL_SYNTHETIC`；
- expected answer block 没有驱动 runtime axes/diagnostics；
- misunderstanding、refusal、silence、partial opposition、stale、revoke、duplicate、
  absent/withheld 与 topology pressure 在当前 fixture 中可区分；
- central/replicated placement 在相同 Authority topology 下没有形成语义差异；
- 四种现成路线在当前合法 owner-event envelope 上均为正向候选解。

不支持：

- 真人理解、现实主体认领、法律 Authority 或真实目标域 Acceptance；
- 实际采购/CLM/CMMN/IAM/HITL 产品的端到端集成、维护、迁移或锁定成本；
- 四臂的独立实现证据：它们共享 owner-event generator、evaluator 与同一实现环境；
- open world 一般性：fresh schema 与 held-out facts 仍由同一 benchmark author/oracle
  编排；
- 现实频率、生产一致性、长期漂移、净价值或 V1/V2 一般解。

因此当前最强可写结论是：

> G2-O1 在 12 个冻结合成 world 上通过 owner-evidence/open-schema discriminator；四种方法
> 同分，未观察到 G2 专属 residual 或 replication semantic gain。下一轮若继续，不应再增加
> 同源 synthetic worlds，而应使用真实成熟产品组合、独立 case author/owner、真实
> Authority/Acceptance readback 与生命周期成本，寻找会改变选择的残余。

## 冻结凭据

- public fixture SHA-256：
  `c67a6c8ac1ac872cc6940ba8dea233b0a8624fe096468f1c412632210ab08a12`
- private oracle SHA-256：
  `58c9cb16802be29dbc443067410f0eac1c6325c3a51e09686bb0b7e8c8dec018`
- results SHA-256：
  `7437ba36a238b5aef5fffb13c20c6209d011a5cf48776447db7b02ceff95d4a4`

本会话没有修改 `research/NOW.md`、本轮 `PROGRAM.md`、G2 LineContract、V1/V2 或任何正式
研究状态。
