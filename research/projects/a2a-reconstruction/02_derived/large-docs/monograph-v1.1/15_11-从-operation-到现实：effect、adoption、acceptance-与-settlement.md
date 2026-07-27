---
derived_view: true
source_path: Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_R8_OPC_Constructive_Closure_v1.1/paper/通爻_主权智能主体共同现实形成_正式论文_v1.1.md
source_sha256: 42b3c6fa1da3a56ce07a20be6283d1efcfa4b15e9069b84d0634934067f86b6c
source_line_start: 1188
source_line_end: 1316
source_heading: "11　从 Operation 到现实：Effect、Adoption、Acceptance 与 Settlement"
---

> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。

# 11　从 Operation 到现实：Effect、Adoption、Acceptance 与 Settlement

## 11.1 为什么执行成功不是现实完成

自动化系统常把以下信号写成“完成”：模型说已经做了、工具调用没有抛异常、子进程退出码为 0、队列消息已发送、调用方数据库更新，或接收方返回 2xx。这些最多证明 Attempt 或中间步骤。现实 Effect 必须由目标世界中相称的权威状态证明。例如支付的 Effect 由支付系统记账状态、对方入账或可验证回执证明；代码部署的 Effect 由目标环境版本和健康检查证明；会议预约由双方日历或确认状态证明；“客户已经采用”则需要目标域 adoption 事件，而非发送方日志。

## 11.2 Operation 与 ActionAttempt

**定义 18（Operation Specification）。** Operation 是一个可执行、版本化、受 Mandate 约束的动作规范：

\[
Op = \langle Op_{act}, Op_{guard}, Op_{recovery} \rangle,
\]

\[
Op_{act} = \langle action, target, inputs, mandate, idempotency \rangle,
\]

\[
Op_{guard} = \langle preconditions, witness, timeout \rangle,
\]

\[
Op_{recovery} = \langle retry, compensation, expected\ effect \rangle.
\]

**定义 19（ActionAttempt）。** 每次运行产生唯一 AttemptID，并记录执行器、开始/结束时间、输入引用、工具结果和错误。多个 Attempt 可以对应同一逻辑 Operation；幂等键防止重试重复产生 Effect。

Operation 必须指向精确 RelationVersion 和 Mandate。若关系版本发生 material change，旧 Operation Specification 不能自动继承。对于不可逆动作，还应有 pre-effect validation：在真正改变目标世界之前再次检查授权、资源、目标地址和 witness 可用性。

## 11.3 Effect

**定义 20（Effect）。** Effect 是目标世界中可由相称 witness 观察到的状态变化：

\[
Eff = \langle Eff_{state}, Eff_{trace} \rangle,
\]

\[
Eff_{state} = \langle target\_domain, state\_before, state\_after \rangle,
\]

\[
Eff_{trace} = \langle witness, causal\_operation, time, reversibility \rangle.
\]

Effect 可能与预期不同，可能部分发生，也可能发生后被撤销。系统必须允许：

- `NO_EFFECT`；
- `PARTIAL_EFFECT`；
- `UNEXPECTED_EFFECT`；
- `EFFECT_CONFIRMED`；
- `EFFECT_REVOKED`；
- `EFFECT_UNKNOWN`。

Effect 的权威来源通常位于目标域。调用方可以提交 Attempt 和预期，但不能单方面宣布目标域状态。

## 11.4 Verification、Adoption 与 Acceptance

**Verification** 判断某 Claim 是否得到证据支持；它可以由技术、审计或第三方完成。

**Adoption** 表示目标域把结果纳入自己的真实运行状态，例如代码合并到生产分支、采购结果进入库存系统、方案写入真实 backlog。

**Acceptance** 是有权主体对 Effect 和交付义务的最终认领，可以是完全、条件、部分或拒绝。Acceptance 可能晚于 Adoption，也可能因组织惯性出现“已采用但未接受”的争议状态。

因此：

\[
ActionAttempt \neq Effect \neq Adoption \neq Acceptance.
\]

这四者必须由不同事件和 Authority 维护。任何统一成 `status=done` 的实现都会丢失争议、补救和责任边界。

## 11.5 Evidence Closure

**定义 21（Evidence Closure）。** 一个 Effect/Acceptance 主张只有在以下条件满足时闭合：

1. 每项关键 Claim 有来源；
2. 来源对该 Claim 具有相称权威；
3. 证据链可追溯且版本一致；
4. 已知 Defeater 被处理或记录为残余风险；
5. 目标世界 witness 可访问或可审计；
6. 需要的 Adoption 和 Acceptance 未被中间日志替代。

哈希、签名和 checksum 证明字节来源与完整性，却不能单独证明业务语义；模型解释证明其推理文本存在，却不能单独证明事实；第三方审计可以增强 Assurance，但不能替不相称的 Principal 接受。

## 11.6 Claim-specific WitnessPolicy

不同主张需要不同见证：

| Claim | 不充分证据 | 相称 witness 示例 |
|---|---|---|
| “文件已发送” | 发送端日志 | 接收端可读取回执 |
| “代码已部署” | CI 成功 | 目标环境版本 + 健康检查 |
| “付款已完成” | API 2xx | 账本入账/对方确认 |
| “能力可用” | 一次 demo | 条件范围内重复测试 + 恢复证据 |
| “客户已采用” | 服务方声明 | 客户目标系统或有权角色的 adoption |
| “主体已接受” | 沉默或自动勾选 | 精确版本的有权 Acceptance |

WitnessPolicy 应作为 Operation 或 Claim 的字段/策略，而不是再增加一类顶层对象。

## 11.7 争议、补救与 Settlement

**Settlement** 不是“系统结束”，而是当前争议和义务在某一制度下达到可接受的处置状态：履行、退款、补偿、仲裁决定、撤销或双方和解。Settlement 可以被新的证据、欺诈或外部裁决重开。

争议发生时，系统应：

1. 冻结受影响的不可逆 Operation；
2. 保存旧 RelationVersion、Mandate 和证据；
3. 分离“Effect 已发生”与“是否应接受”；
4. 识别有 Standing 的主体；
5. 进入人工裁决、TrustAdapter 或制度化补救；
6. 将结果写回事件账本而非覆盖历史。

## 11.8 跨域效力状态机

```text
SPECIFIED
→ AUTHORIZED
→ ATTEMPTED
→ EFFECT_UNKNOWN / NO_EFFECT / EFFECT_CONFIRMED
→ ADOPTED / NOT_ADOPTED
→ VERIFIED / CONTESTED
→ ACCEPTED / CONDITIONAL / REJECTED
→ SETTLED / REOPENED
```

该状态机允许出现“Effect confirmed but rejected”“adopted but disputed”“performed but no effect”等现实状态，而不是强迫所有结果进入单一 `success=true`。

