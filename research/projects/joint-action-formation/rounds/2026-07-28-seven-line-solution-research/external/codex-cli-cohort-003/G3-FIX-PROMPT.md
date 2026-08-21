# G3 CE-001 根红灯修复任务

你是 G3 独立 Codex CLI 主会话的第二轮。完整读取 `COMMON.md`、`G3-PROMPT.md`、
`ROOT-LIVE-AUDIT.md`、`G3-final.md`、`g3-formation/README.md`、
`g3-formation/internal/C-adversarial-audit.md` 以及
`../../experiments/wave-012-ce001-power-restoration/integration-preflight/README.md`。

先实际建立 A/B/C：A 只重建本轮 G3 的证据权威与 line-local 输出边界；B 实现；C 在不知道
B 选择的前提下构造 reflection/closure、owner-response transplant、错误目标、伪移除、
伪 recovery 和合同字段直通攻击。三个内部 Agent 必须留下身份与原始结论，不能用人数代替
证据。

只可修改 `g3-formation/` 和本目录 `G3-fix-final.md`；不得修改其他路径。

当前 18/18 不是本轮完成条件。根审计已经确认这些承重红灯：

1. `FormationExecutionService`、`FormationScorer` 和 runner 都直接构造或引用
   `OwnerService`；owner truth 与 scorer truth 没有形成可信传输边界。
2. scorer 输出 `exact_task_success / recovery_to_value`，越过 G3 的 line-local
   reachability/formation 权限；这类字段会被 integration preflight 拒绝。
3. 不能用私有 fixture 中的 expected path/resolution 作为方法或 owner response。
4. E2/E4 的正例虽然变强，仍需要证明 worker 只消费实际 owner transmitted bytes，不能
   closure/reflection 到 `private/owner_truth.json`、scorer、runner 或预期答案。

必须：

- 将执行 worker 与 owner/scorer 置于真实 subprocess 或同等可检查的进程边界；public
  worker 输入只含公开 packet 与 owner endpoint response bytes；
- owner response 绑定 owner identity、state/policy version、episode/Q/object/operation、
  request/proposal hash 与签发时刻；transplant、stale、tamper、wrong target 必须失败；
- scorer 只在 transcript 冻结后读取独立 grader input，不能向 worker/owner反向泄露；
- G3 只输出 line-local 事实，例如 closure、new-token、kernel/task coordinates、
  bounded reachability witness、intervention trace 与 uncertainty；不得输出或透传
  `ExactTaskSuccess / CorrectResolution / RecoveryToValue / Authority / Effect /
  Acceptance / Settlement` 或同义合同结论；
- E2 remove 必须真正删除 executable operator，并证明没有通过另一路径调用同一动作；
- E4 保留 post-revoke rediscovery、完整 operation/deadline/safety/acceptance observation，
  但只能表述为 G3 可达性证据，合同成功由未来独立 evaluator重算；
- 保留 direct、old closure、new token、model/kernel change、task substitution、open
  inventory Unknown 以及完整 response tree 未冻结时 robust Unknown 的区分；
- 新增一次按 integration preflight 规则扫描 G3 envelope 的测试，确保不会被
  `CONTRACT_FIELD_PASSTHROUGH` 拒绝；
- 保留原 18 项测试的真实风险覆盖；可更新接口断言，不能删掉失败注入或把断言改弱。

真实产品、真人 Principal、法律 Authority、物理 Effect、完整 response-family robustness
和 CE-001 合同解仍为 `NOT_RUN/NOT_ESTABLISHED`。完成后写 `G3-fix-final.md`，列出红灯、
实际攻击、测试数字、残余边界与可进入 integration 的精确 envelope。
