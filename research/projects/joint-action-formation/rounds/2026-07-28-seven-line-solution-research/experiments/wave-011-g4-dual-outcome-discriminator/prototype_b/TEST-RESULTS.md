# Prototype B 定向验证

日期：2026-07-29  
状态：`LOCAL TEST PASS / PROTOTYPE ONLY`

执行命令：

```bash
PYTHONPYCACHEPREFIX=/tmp/wave011-g4-prototype-b-pycache \
python3 -m unittest -v test_runner.py
```

实际结果：

```text
test_active_pair_is_identical_until_reservation_response ... ok
test_hard_pair_has_same_allowed_interaction_transcript ... ok
test_passive_pair_keeps_same_predictions ... ok
test_raw_responses_have_no_pre_adjudicated_keys ... ok
test_response_loss_runs_readback_and_reconciliation_once ... ok
test_service_rejects_unavailable_primitive ... ok

Ran 6 tests
OK
```

另行实际运行 `python3 runner.py`，6 个 world 均由独立 worker 进程完成，输出可解析 JSON。
`ACTIVE-RESERVATION-GRANTED` 的实际轨迹为：

```text
read_revision
read_policy
request_authority
request_reservation
submit_operation                 -> delivery LOST
read_operation_status            -> APPLIED / effect_count 1
reconcile_operation              -> CONFIRMED_APPLIED_NO_RETRY
read_operation_status            -> APPLIED / effect_count 1 + reconciliation
```

broker 对该轨迹记录 `8` 次调用、`54 ms` fixture latency、`1725` response bytes。这里的
latency 是固定测试成本，不是现实测量。结果不含 private oracle 或 G4 confusion score。
