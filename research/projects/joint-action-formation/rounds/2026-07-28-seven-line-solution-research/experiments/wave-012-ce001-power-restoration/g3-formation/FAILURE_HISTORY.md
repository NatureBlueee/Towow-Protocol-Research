# Failure history

## 2026-07-30：实现前继承的红灯

- cohort 002 的 G3 五臂共用 `choose(packet)`，同动作与 candidate-exclusive 0 属于
  alias-by-construction，不能作为方法比较证据。
- 旧实现曾把 public action alphabet 中的 formation operator 当成已证明的新 formation，
  没有计算 old full-policy closure。
- 旧 remove 曾删除未先形成的 operator；wrong Authority、producer self-report、task
  substitution 与 open inventory 也曾形成伪成功。

本模块用单 line executor、独立 owner/scorer、old closure、exact-S0 replay、target exact
readback 和 open-inventory `Unknown` 把这些失败变成回归门。运行过程中新出现的红灯继续
追加在本文件，不以最终绿灯覆盖。

## 2026-07-30：第一次绿灯后的口径红灯

第一次执行为 `13/13`，但只返回聚合 `robust`，且 `measurable` 由实际 Effect 反推。
这会把 policy witness、actual execution 与 effect/safety/terminal robust 再次压平。

修复：

- 恢复六轴 `R_*`；
- 聚合 `reachability.robust` 明示为 `R_effect_robust` alias；
- `R_measurable_exists` 改由 old closure 或独立 extension-policy witness 产生；
- 增加“清除 actual Effect 后 measurable 仍为 TRUE”的反向测试；
- `T` 改为 `INVARIANT / CONTROLLER_SUBSTITUTION`。

第二次执行虽为 `14/14`，输出复核发现 complete inventory 的
`R_physical_exists` 因编辑时漏掉 return 而成为 JSON `null`，原测试只检查了键集合，没有
检查值域。修复 return，并把六轴所有值限制为 `TRUE/FALSE/UNKNOWN`。

## 2026-07-30：Agent C 第二轮攻击的四个 P0

最终 14/14 之后，内部 Agent C 的 mutation audit 仍复现四个 blocker：

1. E2 没有 exact proposal，错误 scope、controller signer、stale/tampered receipt 可通过；
2. S0 未绑定 owner policy/response snapshot，remove 实际改写 owner 答复而非删除 action；
3. E4 initial read 预给 alternative，RecoveryToValue 不检查 deadline、operation、完整约束
   与 O_Q/O_V Acceptance；
4. robust 值依赖 caller 临时传入的 branch，不存在冻结完整 denominator。

修复：

- executor 生成 exact proposal，owner receipt 绑定 proposal hash/current policy head，
  scorer 核验 Authority、scope、expiry、resource/Q/head 与 receipt hash；
- S0 credential 新增 owner heads、scripted response snapshot hash/status、budget、horizon、
  clock seed、public bytes；intervention delta 独立保存，remove 真删除 executable action；
- E4 改为 revoke 后独立 rediscovery；target readback 绑定 operation/resource/time/full
  constraints，实际调用 O_Q/O_V Acceptance endpoint，再重算完整任务价值；
- 完整 allowed response-family tree 尚未冻结，三个 robust 坐标统一降为 `UNKNOWN`，
  receipt 明示 denominator status；
- public semantic case ID 移入 private manifest，raw effect event 改成中性
  `EFFECT_READBACK_OBSERVED`。

新增 mutation 回归覆盖 wrong scope/signer/stale/tamper、owner-policy transplant、
deadline/operation/Acceptance 以及 producer exact-claim。
