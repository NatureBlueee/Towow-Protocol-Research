# Wave 003-B — T2 bounded probe simulator

这是 T2 的合成执行真值层。它把 Wave 002 的
`probe=NOT_RUN / capability=UNKNOWN` 推进为可重复运行的五个合成分支，但不替 relation
solver 判断 capability、Effect、Adoption、Acceptance 或 formation。

本目录没有现实企业数据、凭证或真实容器。`fixed_container`、buyer sandbox、permission、
resource、三条聚合查询和所有 witness 都是冻结测试夹具。即使 `success` 分支通过，也只能
说明 runner 在该合成输入下产生了预定的 ActionAttempt 与 buyer-domain witness。

## 公开 runner contract

输入固定在 `probe_input.json`，同时绑定：

- executor 身份；
- buyer-controlled environment 及版本；
- synthetic container digest；
- 当前 permission、临时 credential、用途和允许查询；
- duration、query budget、CPU、内存和审计资源；
- 恰好三条预批准聚合只读 query；
- idempotency key 与恢复规则。

`scenario_truth.json` 冻结五个执行世界：

1. `success`：三条 query 完成，buyer audit witness 存在；
2. `environment_mismatch`：preflight 读回环境版本不一致，零 query、零新 operation 执行，
   但保留买方审计域中的阻断 witness；
3. `credential_revoked_mid_run`：第二条 query 后 credential 撤销，第三条不执行；
4. `audit_witness_missing`：执行域完成三条 query，但 buyer-domain witness 缺失；
5. `duplicate_retry`：同一 idempotency key 已有成功 receipt，返回旧 receipt，不产生新执行
   或新 witness。

每次运行输出：

- `action_attempt`：执行域观察，不能建立 buyer-domain Effect；
- `buyer_domain_witness`：独立审计域观察，可为 `PRESENT`、`MISSING` 或
  `REUSED_PRIOR_WITNESS`；
- `idempotency`：本次是否产生新执行；
- `recovery`：停止、重绑、重新授权或修复审计所需条件；
- `hash_receipt`：输入、scenario、ActionAttempt、buyer witness 和前序 receipt 的哈希绑定；
- `evidence_boundary`：明确这是本地合成运行。

runner 不输出 capability 结论，也不把 producer exit code、日志或 output hash 当作买方
witness。

## 命令

单分支运行：

```bash
python3 simulator.py --scenario success --output /tmp/t2-probe-success.json
```

全部分支：

```bash
python3 simulator.py --all --output-dir /tmp/t2-probe-wave-003-b
```

验证：

```bash
python3 -m unittest discover -s tests -v
```

## 证据边界

本模拟器可以检验状态分离、输入绑定、确定性、幂等、撤销停止、审计缺失和恢复逻辑。它不能
支持现实 capability、真实权限、法律充分性、生产安全性、商业价值、现实 Effect 或协议
独占性。
