# Deterministic-math duel third-fix audit

状态：**第三轮定向修复完成 / 等待独立复核 / NOT CANON / NO G / NO FORMAL 3200**  
日期：2026-08-01  
触发材料：`FINAL-INDEPENDENT-ACCEPTANCE.md`，裁决
`PARTIAL_ACCEPT_SCOPED_WITH_BLOCKERS`，SHA-256
`d499f2ca509da78fce9a0e5a5431d83e1a37a446488b812da9601586463d312e`。

## 只修复三个剩余 blocker

### B1 external pin totality

`load_table_bytes` 现在先检查 pin 是 exact `str` 且匹配 64 位 lowercase hex，再调用 regex或读取
binding。`lookup_count_log1p(1, None|7|bytes)` 均返回：

```text
NOT_QUALIFIED_TABLE_BINDING / TABLE_EXPECTED_SHA_GRAMMAR / controller_pin
```

不再泄漏 `TypeError`。source 内仍没有默认 SHA；可信 pin 必须由caller/controller外部提供。

### B2 RFC JSON 与 metadata

- `json.loads(..., parse_constant=_reject_json_constant)` 拒绝 `NaN`、`Infinity`、`-Infinity`；
- canonical encoder使用 `allow_nan=False`；
- 六个 top metadata成员不仅检查 key set，还要求 exact string type与冻结常量值；
- caller即使给变异bytes提供匹配SHA，也不能让非法JSON或metadata drift通过。

最小回归复现了原红队的 exact-length nonfinite metadata变异，并覆盖同长度 `version=0.1.1`。
table数值证据仍是 `CORROBORATED_NOT_PROVEN`；结构修复没有升级正确舍入主张。

### B3 family producer/consumer admission

`evaluate_family_normalization` 在 norm之前逐 component执行：

1. 原有 rational leaf admission；
2. `abs(component) <= 8`，否则
   `NOT_QUALIFIED_NUMERIC_RANGE / FAMILY_INPUT_CLIP_BOUND`；
3. `bits_to_fraction(round_binary64(component)) == component`，否则
   `NOT_QUALIFIED_NUMERIC_DOMAIN / FAMILY_INPUT_BINARY64_EXACT`。

因此 `[100,0]` 和 `[1/3]` 在 A/B 都不再成功。合法 `+8/-8`、zero、minimum subnormal都有稳定
回归。minimum subnormal仍暴露 A/B不同语义：A 的per-square round得到zero norm，B exact-dyadic
norm得到1.0方向分量；两者都只是study result，不选择正式路径。

## 未改变的证据边界

- converter：`SCOPED_ACCEPT_KERNEL_ONLY`；
- sqrt：`SCOPED_ACCEPT_KERNEL_ONLY`；
- table correctly-rounded：`CORROBORATED_NOT_PROVEN`；
- formal reachability、task impact、wall/CPU/RSS、正式可达成本：`UNKNOWN`；
- minimal sufficient set：`UNKNOWN_NOT_CLAIMED`；
- G与formal 3200：`NOT_RUN`。

本轮没有增加新模型、正式算法选择或最小性主张。

## 验证

```bash
python3 deterministic_math_duel.py --expected-table-sha256 0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5 --check RESULTS.candidate.json
python3 -m unittest discover -s tests -v
```

- canonical result byte rebuild：PASS；
- tests：`27/27 PASS`；
- Python compile：PASS。

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `deterministic_math_duel.py` | 64,734 | `04fc6150f3323688ee01a73a6fb5c0f3807aedfa3872493f9187e9c107147aa2` |
| `COUNT-LOG1P-BINARY64.candidate.json` | 12,870 | `0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5` |
| `RESULTS.candidate.json` | 28,941 | `a9af8b9ea8e84b5c6f1f0d7dc1db9dd8e1e136e4e72c9721c71ee73ec5590787` |
| `tests/test_deterministic_math_duel.py` | 22,723 | `86d4d4e6ec90f3dbadfe456726b6948fae6dd09b5fe417464cd0498ce4cf2c32` |
| `README.md` | 9,354 | `5722b90a8b63223f9b3979625720001f8d9dd84825321e43a3be054a5f9cbaac` |
| `FINAL-INDEPENDENT-ACCEPTANCE.md` | 12,792 | `d499f2ca509da78fce9a0e5a5431d83e1a37a446488b812da9601586463d312e` |

本文件是实现者审计，不是独立验收。下一步只应由独立审查者重放三个 holdback blocker并裁决。

