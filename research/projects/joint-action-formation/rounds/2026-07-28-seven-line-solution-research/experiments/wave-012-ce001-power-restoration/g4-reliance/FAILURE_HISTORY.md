# G4 module failure history

状态：`PRESERVED / LOCAL IMPLEMENTATION HISTORY`

1. 先写 tests/fixture 后首次运行：
   `python3 -m unittest discover -s tests -v` 得到 `1 error`，
   `ModuleNotFoundError: No module named 'module'`。这是 test-first 未实现红灯，不是
   CE-001 机制负结果。
2. 首个完整实现运行 `10/10 OK`，但 runner 未关闭 worker stdout/stderr，产生多条
   `ResourceWarning: unclosed file`。补充显式 close 后同一命令 `10/10 OK` 且无 warning。
3. 修复后 `runner.py --self-test` 为 `SELF_TEST_PASS`，四个 Python 文件
   `py_compile` 通过。
4. 根会话独立复核发现 `WrongObjectReliance` 曾读取 worker 自报的
   `wrong_object_rejected`。即使主 worker 同时执行 exact reconciliation，这仍留下
   solver 自造评价事实的接口。现已改为只由 service 观察到的 wrong-object readback 与
   exact reconciliation 状态推导，并加入 worker 正反撒谎均不能改变 outcome 的测试。
5. cohort 003 根复跑发现两个根红灯：
   - Effect 的同一个 service 曾直接按 `acceptance_owners` 生成两条 Acceptance，
     `len(records)==2` 使 `["O_Q","O_Q"]` 也错误闭包；
   - 四个 private case 的 P1 `Y_resolution` 全为 true，worker 一律 `YES` 的 `TP=4`
     是 one-class 结果。
   这两个红灯使旧版独立 Acceptance 与 resolution calibration 结论均不成立。
6. 第二轮第一版结构修复后，旧测试实跑为 `9 pass / 1 failure / 1 error`：
   旧 world-change 断言仍写 `3/3`，且直接 service 测试未携带新增 exact `episode_id`。
   这是测试接口迁移红灯；随后更新为真实 10-case 分母和完整 binding。
7. Agent C 的首轮盲审发现 provenance 只绑定 owner state 与 Effect receipt，没有绑定 act
   payload；篡改 decision、episode、Q 或 effect occurrence 后，单独 provenance 校验仍返回
   true。虽然 closure 的字段检查仍会拒绝这些 act，但 provenance 主张本身不成立。现已把
   完整 act payload 纳入 hash，并加入逐字段篡改回归。
8. Agent C 继续构造 `tick > expires_tick/valid_through_tick` 的直接 mutation，发现旧
   `_valid_attempt()` 只检查 decision 与 revision，过期 reservation/commit 仍能产生 Effect。
   现已在 attempt 时检查两个有效期，并单独保存 Effect 发生时的授权状态，避免用事后时钟
   反向改写 `UnsafeEffect`。
9. 当前定向回归为 `19/19 PASS`，`runner.py --self-test` 为 `SELF_TEST_PASS`。它覆盖：
   Effect path 零 Acceptance act、O_Q/O_V 独立 act、exact owner closure、拒绝、
   wrong episode/Q/effect、stale、duplicate owner、PENDING resolution 负例，以及原有
   E3A/E3B、wrong-object、double-submit、revoke。

10. 第三轮根审计证明上述 `19/19` 仍不能支持独立 owner 来源或进入 integration：
    - O_Q/O_V 仍是一个父进程里的两个对象，相同 service id 可闭合；
    - provenance 是 controller 可公开重算的 SHA-256，不调用 `issue_act` 也能伪造；
    - `PENDING/0kW/wrong circuit/other circuit/exact_reconciliation=false` 未在 owner
      request 前 fail closed；
    - runner/worker 仍输出 `Y_*` 与合同级 alias；
    - G4 的 `Venue-V/Circuit-C7` 与 integration 的 `VenueV:CircuitC7` 不一致。
    所以旧 `19/19` 被保留为失败历史，不能作为第三轮 closure。
11. B 的第三轮首次实现真实运行在 READY 前失败：owner child 使用 `python3 -I`，无法加载
    已安装的 `cryptography`，并暴露初始化异常时 pipe/process 未回收。现改为绝对 actor
    script、净化环境但不屏蔽 site package，并在 startup exception 中 force-close child。
12. 修复运行环境后，原 19 项和新增 root mutations 合计 `35/35 PASS`。新增覆盖实际 child
    PID/process/service/state/act source 唯一性、duplicate service、source/PID tamper、公开
    digest forgery、signature replay、PENDING、0kW、C8、other circuit、short duration、
    deadline、wrong O_E signature、未 reconciliation、adapter 偷换和 contract field
    passthrough。当前绿灯仍仅为本地 cooperative process/component 证据。

这些绿灯只覆盖本目录的本地状态机与接口约束，不能擦除 blind isolation、现实 Authority、
现实供电 Effect、真人 Acceptance 和产品运行均未验证的边界；它们仍为 `NOT_RUN`。
