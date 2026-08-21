# Wave 015 runner visibility contract

日期：2026-07-30  
状态：`COMPONENT IMPLEMENTATION CONTRACT / NO TOTAL RUNNER ACCEPTANCE`

## 目的

本组件只建立两个边界：

1. `ArmViewFactory` 从明确 public input allowlist 新建 arm view；
2. `BlindProcessLauncher` 启动真实 `multiprocessing spawn` child，并记录 child 实际看到的
   view、argv、cwd、process name、environment 与 inherited FD inventory。

它不实现 owner topology、Target Effect、fault injection、E3 pair fork、E4 discovery、
E6 migration 或独立合同 evaluator。

## ArmViewFactory

### 输入

输入必须精确等于：

```text
schema = CE001_ARM_PUBLIC_INPUT_V1
task:
  q_version
  object_id
  target_id
  deadline_minute
  required_duration_minutes
  required_power_kw
  power_tolerance_percent
```

未知顶层字段、未知 task 字段、嵌套 metadata/padding/private 字段全部 fail closed。

factory 自己生成固定长度、独立随机的：

```text
public_run_id
episode_instance_id
arm_binding_token
operation_id
```

`broker_surface` 也是唯一 arm-view schema 的一部分：

```text
endpoint_handle = 32 lowercase hex
capabilities = fixed sorted alphabet
surface_version = 1
```

Broker capabilities 在 factory 构造时冻结，不由 case 调用方动态增加。若外部提供实际
`OwnerTopologyBroker.public_surface()`，字段必须精确匹配，能力字母表必须与 factory
合同一致；否则 fail closed。这样 Hidden controller 与 blind launcher 不再维护第二套
不兼容的公开 view。

### 禁止的构造方式

factory 不接受 full manifest、bundle、private case 或 registry 后再删除字段。以下
blacklist projection 永远不允许：

```text
arm_view = {k: v for k, v in private_manifest if k not in forbidden}
```

原因是未来新增的 private 字段会默认流入 arm。当前 schema 采用 allowlist：未登记字段默认
不可见。

### 不可见材料

arm view 不得包含或派生自：

```text
semantic case id
expected disposition
world root
private receipt/reveal/truth
private/manifest hash
owner registry or topology
target registry
authority-stratum conclusion
alternative oracle
crash/fault schedule
effect-occurrence truth
```

调用方可以把本 run 的 private material 交给 factory 只用于 parent-side leak scan。factory
检查 raw material、嵌套字符串叶值以及各自 SHA-256 candidate hash；private material 本身
不进入生成结果。数字、布尔等常见标量不作为独立 needle，以免与 deadline 等公共值产生
无意义碰撞。

### paired visibility

`pair_projection` 只允许 α-renaming：

```text
public_run_id
episode_instance_id
arm_binding_token
operation_id
broker_surface.endpoint_handle
```

`assert_pair_compatible` 要求 α-normal form 相同，且两个 canonical raw view 的长度相同。它
用于阻止：

- E3A/E3B 通过可选字段或长度产生 pre-readback 标签；
- semantic candidate hash 写入任一 public 字段；
- 不同 broker capability 数量预告 topology。

这只证明启动 view 的 α-equivalence，不证明后续 owner/Target transcript 已同构。

## BlindProcessLauncher

launcher 使用真实 `spawn` context。child target 执行前安装：

```text
argv = ["wave015-blind-child", "--opaque"]
cwd = fresh opaque empty temporary directory
process name = fresh opaque fixed-shape name
environment = LANG/PATH/PYTHONHASHSEED minimal map
```

launcher 在 `process.start()` 时也暂时清理 parent argv/cwd/env，避免
`multiprocessing.spawn` preparation/import 阶段继承 semantic caller surface。该临界区由
模块内 lock 串行化，并在 `start()` 返回后恢复 parent 状态。

child 保存：

```text
validated arm view and canonical bytes
actual argv
actual cwd and cwd entries
actual multiprocessing process name
actual environment
inherited FD inventory
worker result
```

parent 再检查：

- child exit 0；
- argv/cwd/name/environment 等于 launcher 冻结值；
- cwd 为空；
- private raw material 与 candidate hash 不在 visible surface；
- worker 或 receipt 超时、未知字段、异常一律 fail closed。

## 预注册攻击

当前测试覆盖：

1. semantic `case_id`、world root、owner topology、crash schedule、private hash 顶层注入；
2. task 内嵌 case/metadata/fault schedule/registry hash；
3. semantic label 伪装成 Q/object/target；
4. private manifest SHA-256 伪装成 public value；
5. 可选 padding 制造长度标签；
6. E3A/E3B private candidates 对相同 public task 的 α-equivalence 与等长；
7. parent argv/cwd/process name/environment 带 semantic case，再启动真实 spawn child；
8. factory 后篡改 view，再由 launcher 第二门拒绝。

## 证据边界

本实现能够支持：

```text
PUBLIC_VIEW_ALLOWLIST = IMPLEMENTED
UNKNOWN_FIELD_DEFAULT = FAIL_CLOSED
PRIVATE_RAW_AND_CANDIDATE_HASH_SCAN = IMPLEMENTED
REAL_SPAWN_CHILD_VISIBLE_SURFACE_RECEIPT = IMPLEMENTED
ARGV_CWD_NAME_ENV_SANITIZATION = IMPLEMENTED_SCOPED
START_VIEW_ALPHA_EQUIVALENCE_CHECK = IMPLEMENTED
```

它不能支持：

```text
HOSTILE_SAME_OS_USER_ISOLATION = NOT ESTABLISHED
UNRELATED_CONCURRENT_SPAWN_SAFETY = NOT ESTABLISHED
OWNER_TOPOLOGY_BROKER = NOT IMPLEMENTED HERE
TARGET_SIGNED_NEGATIVE_READBACK = NOT IMPLEMENTED HERE
E3_PAIRED_WORLD_FORK = NOT IMPLEMENTED HERE
E4_ALTERNATIVE_HIDDEN_AFTER_REVOKE = NOT IMPLEMENTED HERE
E6_HIDDEN_SCENARIO_CONTROLLER = NOT IMPLEMENTED HERE
FULL WAVE015 RUNNER ACCEPTANCE = NOT COMPUTED
```

测试通过只说明列出的 visibility invariants 在本地实现和攻击集中成立，不说明剩余六案、
任何比较 arm 或 CE-001 完整任务已经运行。
