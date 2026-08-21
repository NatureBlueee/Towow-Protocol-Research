# G3 round-2 internal B implementation return

日期：2026-07-30  
canonical identity：`/root/g3_round2_b_impl`  
职责：B implementation  
可写范围：仅 `g3-formation/`

## 修改前观察

第二轮开始时，原 18 项测试虽通过，但三条 truth surface 没有形成可信边界：

- runner 直接构造 `OwnerService` 与 `FormationScorer`；
- `FormationExecutionService` 直接持有 owner object；
- scorer receipt 直接输出合同级 success/resolution/recovery fields。

owner response 只有局部 proposal receipt，没有统一绑定 state/policy version、
episode/Q/object/operation、request nonce、issued-at deadline，也没有 owner-only
authenticator。worker 可从同一进程反射 private/scorer/runner。E2 remove 虽删 kernel
string，但 formation dispatch 仍是 hardcoded branch，closed executable registry 证据不足。

## 实际设计选择

1. 建立 runner broker、独立 owner endpoint、public worker capsule 与 transcript-frozen
   grader subprocess；owner/worker 终止后才启动 grader。
2. public worker 使用 workspace file allowlist capsule与最小环境；只允许六个 public
   runtime module、capsule及对应 pyc。
3. owner response 使用 private endpoint Ed25519 key 签发，public packet 固定 verification
   key；response 精确绑定 identity、state/policy versions/head、episode/Q/object/operation、
   request/proposal hashes、request/response nonces、issued-at/deadline。
4. broker 对 owner stdout 的 raw JSONL line 做逐字节原样转发；owner-emitted、
   broker-forwarded 与 worker-consumed 的逐行 wire hash/list 必须相等。不同
   whitespace/key-order 的合法 response 也保持 byte-exact。
5. scorer 只读取 transcript freeze 后的独立 grader input；输出删去合同 verdict 及同义
   labels，只保留 G3 coordinates、bounded witness、intervention 与 post-revoke observation。
6. E2 formation 使用 closed dispatch registry 的唯一 operator；remove 后 registry scan、
   proposal、sign request、token formed 与 target submit 全为零。
7. E4 保留 post-revoke rediscovery 与 operation/deadline/safety/owner-outcome observation，
   不在 G3 envelope 计算合同结果。

## 实际修改文件

- `worker_capsule.py`
- `formation/__init__.py`
- `formation/canonical.py`（读取复用，未改语义）
- `formation/models.py`
- `formation/protocol.py`
- `formation/owner_endpoint.py`
- `formation/owner_service.py`
- `formation/worker_process.py`
- `formation/execution_service.py`
- `formation/grader_process.py`
- `formation/scorer.py`
- `formation/runner.py`
- `fixtures/public_cases.json`
- `private/owner_truth.json`
- `tests/test_module.py`
- `README.md`
- `outputs/report.json`
- `outputs/traces.jsonl`
- `internal/B2-implementation-return.md`

没有修改 A/C internal 文件、cohort final、integration-preflight 或其他路径。

## 实际攻击覆盖

owner transport 单维 fault：

- wrong owner identity；
- stale state version、policy version、policy head、issued-at；
- transplanted episode、wrong Q、wrong target、wrong operation；
- wrong request hash、wrong request nonce、wrong proposal hash；
- payload tamper；
- payload tamper 后重算裸 response hash但无法重签 owner authenticator。
- 合法 payload 使用不同 whitespace/key-order 时仍逐字节原样转发与验证。

worker capsule probes：

- private owner truth；
- owner/scorer/runner source；
- runner pyc；
- outputs/report、tests、internal；
- 外部 cohort `G3-final.md`；
- owner/scorer/runner import。

private fixture 中原有 `resolution_requirement` 已全部删除；worker、owner 与 grader source
也不读取 expected path/resolution。

既有 18 项风险未删除或改弱；迁移到 line-local断言后继续覆盖 direct/old closure/new token/
kernel/task substitution/open Unknown、E2 exact-S0、E4 mutations、wrong object、neutral raw
readback、bounded refusal、raw output binding等。新增 process timing/bytes、capsule、owner
binding、preflight 与 synonym scan。

## 运行命令与原始结论

```text
PYTHONPYCACHEPREFIX=/tmp/ce001-g3-b2-final-pycache \
  python3 -m py_compile run.py worker_capsule.py formation/*.py tests/*.py
=> PASS

PYTHONDONTWRITEBYTECODE=1 \
  python3 -W error::ResourceWarning -m unittest discover -s tests -v
=> Ran 26 tests
=> OK

qualified-e1 integration envelope with components.G3 replaced by report body
=> preflight_status=QUALIFIED_COMPONENT_OUTPUTS
=> contract_score_status=CONTRACT_SCORE_NOT_COMPUTED
=> rejections=[]
```

`outputs/report.json` 的合同词与预注册同义 verdict recursive scan 无命中。输出为 11 个
line receipt、16 个 raw run。

## 限制

- capsule 是 Python audit-hook file allowlist；它能实际拒绝本轮 reflection probes，但不是
  抵抗任意 native syscall/恶意本机进程的通用安全沙箱。
- Ed25519 key 是本地 fixture owner endpoint key，不证明现实 owner identity 或法律权限。
- physical/measurable 是独立 grader process 内的 local scan，尚非现实 oracle witness。
- branch/safety/terminal robustness 全为 `UNKNOWN`，完整 response tree 未冻结/穷举。
- raw trace 中有 owner outcome/readback 观察；integration-facing G3 body 才是严格
  line-local envelope。未来 evaluator 必须独立重算合同结果。
- 真实产品、真人 Principal、法律 Authority、物理 Effect、合同 Acceptance/Settlement 与
  CE-001 完整解均为 `NOT_RUN / NOT_ESTABLISHED`。
