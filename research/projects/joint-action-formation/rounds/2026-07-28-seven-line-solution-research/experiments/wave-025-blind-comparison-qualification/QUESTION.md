# Wave 025：盲比较资格挑战

日期：2026-08-01  
状态：`FROZEN QUESTION / QUALIFICATION CHALLENGE PENDING`

## 原问题谱系

Problem V1/V2 要求在同一冻结问题、合法 Authority、原生 Effect/Acceptance 和完整成本下比较
强中心、通用模型、成熟组合、人类制度与其他方案。Wave 021 冻结了公平取向，Wave 023 发现
静态 manifest 不能准入真实运行，Wave 024 又实际反驳了“记录字段相同即 blindness”：固定
S→R→U 顺序与同 UID 文件/进程面仍可泄漏 hidden world。

因此本轮不直接比较 A1–A5。它先回答一个承重且有界的问题：

> 在 candidate 可以主动枚举环境、但不能读取合法响应之前，能否用成熟的 OCI/VM 隔离、
> 启动时冻结的秘密随机化、真实 host observation、专用 leak-only attacker、可检出正控和
> 独立 evaluator，建立或拒绝一个足以准入后续异质方案比较的经验性 blindness 资格？

现有容器、虚拟机、CSPRNG/HMAC、统计检验、SQLite、签名和 append-only root 若能解决，
就是通爻的正向方案；本轮不为“原创”重写内核、密码学或容器技术。通爻需要自持的是 exact
public projection、qualification state、evidence binding 和 fail-closed evaluator。

## 研究单位与 observation cut

完整比较单位是：

```text
frozen problem × applicability stratum × isolated world clone × treatment × replicate
```

本轮第一批只检验 `T0 SEALED → T1 PUBLIC-PREIMAGE`。设 hidden role 为 `H`，冻结 public bytes
为 `P`，candidate 实际可观察 transcript 为 `O_pre`。在登记威胁模型和 probe 类下检验：

```text
H ⟂ O_pre | P, candidate artifact, resource block
```

这不是信息论证明。第一条 lawful owner/Target response 之后可以因真实世界而不同；本批不运行
该动态交互，也不把 prefix 资格偷换成完整 blind comparison 资格。

## 本轮冻结 claims

1. `CL-025-LEAK-DETECTOR-SENSITIVITY`：当前 run 同权限 canary 与 predecessor/shared-state
   contamination 两类正控都能被预注册 leak-only collector 与 classifier 在 fresh holdout 上检出；
   否则正式“未发现泄漏”无效。
2. `CL-025-OCI-PREFIX-ISOLATION`：在绑定的 OCI image 与 isolation profile 下，hidden role
   不进入 mount、PID/network namespace、argv/env/cwd、公开文件、hostname、错误形状或其他登记
   `O_pre` 特征；fresh holdout 的预注册攻击优势不超过阈值。
3. `CL-025-SECRET-RANDOMIZATION-CLOSURE`：assignment/order 与 public IDs/padding 使用分离的
   CSPRNG/HMAC domain；pre-run commitment 在启动前外部锚定，batch close 后 reveal 可重算，
   candidate 不能由公开值反推 role 或顺序。
4. `CL-025-HOST-OBSERVED-LAUNCH`：实际 container image digest、user、network/read-only/capability/
   privilege/PID/mount 配置由 host receipt 重算，不信 runner 或 candidate 自报 `isolated=true`。
5. `CL-025-FULL-BLIND-COMPARISON-QUALIFICATION`：保持 `NOT_TESTED`。它还需要动态 fixed broker、
   earliest-lawful-divergence、evaluator freeze、跨 run contamination、每个真实 A1–A5 native
   treatment、A3 provider 与 A5 human 的分别资格。

前四项可以分别支持、失败或保持 Unknown；任何一项成功都不能晋升第五项。

## 威胁模型

防御：主动目录/进程/FD/socket/环境/时间/错误/cache 枚举，world author 无意反射答案，
跨 run 残留，共享 RNG 可回推，evaluator 反馈与 controller 代做。

信任：本机 Docker Desktop VM/daemon 与 Linux kernel、host root recorder、冻结 collector 与
evaluator preimage、外部 pre-run commitment 记录。暂不防 host administrator/hypervisor 合谋、
微架构侧信道、物理侧信道或外部 provider 主动串谋。

## 第一批结果状态

- `PREFIX_QUALIFIED_SCOPED`：四项 prefix claims 均通过，只准入下一层动态资格挑战；
- `STRUCTURAL_PREFIX_ONLY`：只有 schema/字节/启动字段绿灯；不准入；
- `NOT_QUALIFIED`：功效、root、host receipt 或关键通道缺失；
- `BLIND_QUALIFICATION_FAILED`：任一确定性泄漏、classifier 超阈值、共享 RNG、固定顺序或
  evaluator adaptation；拒绝比较证据，但保留与 blindness 无关的局部软件结果。

## 明确不负责

- 不运行、不评分、不排名 A1–A5/C1–C3；comparative runs=`0`，winner=`NONE`；
- 不证明动态 broker、Authority、Effect、Acceptance、成本公平或 lifecycle 已闭合；
- 不证明法律 Authority、物理 Effect、真实 human/provider、生产可靠性或 V1/V2 完整解决；
- 不把 Docker 配置、400 个样本、测试绿灯或一份漂亮 receipt 自动称为 blindness。

## 独立输入

问题冻结前，三个互不读取彼此输出的研究单元分别形成：

- `independent-problem-reconstruction.md`：比较单位、Q0–Q11 与 observation cuts；
- `red-team-preflight.md`：L01–L15、Q01–Q13 与统计拒绝门；
- `runtime-reuse-architecture.md`：历史成熟内核复用、OCI/VM、root、supervisor 与依赖风险。

Pro 只收到 `pro/TASK.md` 的 clean-room 最小包，没有收到上述结论或本地 Docker 选择；其返回
只能作为候选设计，不自动改变本问题。
