# Wave 021：CE-001 公平基线

本目录冻结 A1–A5 的比较准入，不运行 arm，也不选择胜者。

## 文件

- `AUDIT.md`：公平定义、关键判断与仍缺输入；
- `BASELINE-CONTRACT.json`：内容寻址的正式合同；
- `fairness_validator.py`：合同和 batch plan 的机器准入；
- `fixtures/FAIR-BATCH-TEMPLATE.json`：通过准入、但尚未执行的五臂模板；
- `fixtures/UNFAIR-TOWOW-EXTRA-ORACLE.json`：只给 A4 oracle、额外 retry 和额外预算的反例；
- `fixtures/FAIR-FAILURE-TRIGGER.json`：semantic native boundary 的故障触发模板；
- `fixtures/UNFAIR-RAW-ORDINAL-FAILURE-TRIGGER.json`：按 trace ordinal 注入并泄漏触发点的反例；
- `tests/test_fairness_contract.py`：来源、合同、A1 applicability 与不公平攻击测试。

正式合同哈希：

`8fe94be48d8d2bc506af292ac6b0015160d8d2eaab059c619e930ce0f77f8362`

机器状态：

```text
FAIRNESS_CONTRACT_ACCEPTED_NO_RUN_NO_WINNER
```

本轮没有对 `research/NOW.md` 作任何修改。
