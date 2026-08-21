# Wave 008 G3 最小判别模拟器

状态：`LOCAL_SYNTHETIC / RETAINED NEGATIVE PROBE / NOT A G3 DISCRIMINATOR`

> 重要：代码回归通过不等于本实验已经完成 G3 判别。外部独立重建指出，
> `APPLY_FORMATION_OPERATOR` 从 `S0` 起就在 public action alphabet 中；在没有计算
> 旧 action/preparation closure、没有给出有界 UNSAT 证书、也没有区分 model-level
> extension 之前，`F` 的成功可能只是旧模型内的条件性准备路径。本目录当前只保留为
> 最小机制探针；其 `FORMATION` 标签已经从机器输出中移除。

这个实验原计划回答一个窄问题：在冻结同一 `Q`、`V0`、必要 Principal、Authority Locus、
target-authoritative witness 和资源上限后，能否把三类结果机械地区分开：

- `D / DISCOVERY`：合格路径在 `S0` 已存在，static search 只是发现它；
- `A / ACTIVATION`：既有资源或工具存在但未激活，runner 激活后可达；
- `F / FORMATION`：`S0` 无等价路径，既有资源也不能激活；有权 operator 后同一 `Q`
  的路径首次出现，目标域 readback 为真，且 remove/reverse operator 后路径消失。

三个 hidden world 复用同一个不可变 `EpisodeContract` 对象及同一 fingerprint。Candidate
只收到 public contract、公开事件和已用预算；hidden state、`S0/S1` 判定、Authority 校验、
target readback 和最终分类只存在于 `truth.py`。Authority 是独立的
`principal:joint-authority-holder`，controller 只能选择何时调用该 locus，不能把自己
声明成 Holder。这个 HITL 仍是合成的预定 holder 行为，不是真人 consent 证据。
这是代码结构与信息接口隔离，不是抵抗拥有
同一仓库读取权限的恶意本机代码的安全沙箱。

## 比较臂

主矩阵在 D/A/F 上运行：

1. `static_search`
2. `activation_runner`
3. `formation_policy`
4. `same_information_strong_center_hitl`

攻击矩阵只在 F 上运行：

1. `wrong_authority`
2. `producer_only`
3. `remove_operator`
4. `reverse_operator`

所有臂共享最多 4 个 action / 4 个 cost unit 的资源上限。Candidate 的
`claimed_success` 不参与真值判定；producer assertion 不能替代 target witness。

## 预期判别

| World | static search | activation | formation policy | strong center + HITL |
|---|---|---|---|---|
| D | Discovery success | Discovery success | Discovery success | Discovery success |
| A | Unknown | Activation success | Activation success | Activation success |
| F | Unknown | Unknown | Operator-path candidate | Operator-path candidate |

四个攻击臂都应是保留原始原因码的 `NEGATIVE`。`wrong_authority` 只建立 Authority
失败，`producer_only` 只建立证据失败；二者都不能单独建立 operator 必要性。完整汇总应为：

- `SUCCESS=9`
- `UNKNOWN=3`
- `NEGATIVE=4`
- external model call `=0`

`remove_operator` 必须先出现有效 apply 和成功 target readback，再由同一 Authority
移除并观察不可达；对一个从未存在的 operator 直接 remove 只能产生
`FORMATION_OPERATOR_REMOVE_NOOP` 和 `UNKNOWN`，不得被解释为 operator 必要性。

同一规则策略改名后在三个 world 上运行成功，只是一个 central-topology 构造性正例。
它不是独立的 mature planner/workflow/HITL baseline，因此
`existing_solution_value=NOT_TESTED`。实验不使用 novelty score，也不把 operator-path
success 自动解释成 PFE、A2A、联邦或通爻的独特增量；本矩阵保持
`pfe_a2a_unique_increment=NOT_ESTABLISHED`。

## 运行

在本目录执行：

```bash
python3 -m unittest discover -s tests -v
python3 -m g3_discriminator
```

第二条命令打印确定性 JSON；它不读取网络、外部模型 prompt、外部模型 response、凭据或
工作区其他研究材料。

## Claim boundary

若测试通过，目前只支持：

- 这份本地合成 fixture 能机械地区分其预设的 discovery、activation 与 operator-applied
  三类 world；是否应把第三类解释为 bounded formation，仍需 closure/model-diff 试验；
- F fixture 的 operator-path 结果依赖有权 operator 和 target-authoritative readback，
  但在 old closure 被计算前保持 `formation_supported=false`；
- wrong-authority、producer-only、remove 和 reverse 攻击在本 evaluator 下不会被误判
  为 formation；
- same-information central-topology 命名下能够运行同一规则策略；
  这只是中心拓扑的构造性正例，不是成熟 planner/workflow/HITL 技术已经被实测覆盖的证据。

它不能支持：

- 真人 Principal 理解、授权、采纳、接受或承担责任；
- 商业价值、现实频率、生产就绪、跨组织迁移或长期净价值；
- PFE/A2A/联邦/通爻优于或不可替代于强中心、planning、CEGIS、workflow amendment、
  HITL 或现成平台；
- 这个候选 evaluator 对恶意同权限代码安全；
- 任何正式 mechanism/claim 状态变化。

Unknown 与 negative 都是正式输出，不会被丢弃、重写为成功或外推到未测试研究线。

独立攻击还确认，本 probe 不支持：

- executable `Q/V0`、必要主体参与或 target-authoritative readback；
- 真实 Holder callback/receipt（当前 Authority 仍只是字符串匹配）；
- operator 的 bounded-closure necessity；
- hidden world、evaluator 与 implementation 的 sealed fingerprint；
- 独立进程或对恶意同权限 candidate 的隔离；
- 真实公平成本（当前每种 action 都是一个整数 unit）。

因此它只用于保留失败机制与回归，不再作为 QHM-1 的基础 truth source。
