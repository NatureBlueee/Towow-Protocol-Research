# Wave 004-B — HW-B controller development integration

状态：`LOCAL_SYNTHETIC_THREE_ACTION_EXECUTION_COMPLETE`  
评价标签：`DEVELOPMENT_POST_FEEDBACK_NOT_BLIND`

本目录把 HW-B 四份原始 holder receipt 接到 Wave-004-A controller executor。它不读取
oracle，不修改 Wave-004-A，也不把授权写成已经执行。

## 当前真实结果

- HELIOS：原始文件字节哈希冻结后，经显式 normalization 执行
  `HELIOS-44 → NODE-COPPER-ROUTER`，controller 写入 recipient store、磁盘读回并签发
  execution receipt。
- ION：原始 receipt 明确要求 `derived_receipt_required` 且状态为 `NOT_FORWARDED`。
  controller 先执行 `ION-06 → NODE-SILVER-RELAY`，再签发绑定首跳的 derived
  authorization，最后执行 `NODE-SILVER-RELAY → NODE-COPPER-ROUTER`。
- JUNIPER/KITE：使用 `COUNTERPARTY_EXCHANGE` 的 per-side delivery，在一个原子 transaction
  中执行 `JUNIPER-28 → KITE-15` 与 `KITE-15 → JUNIPER-28`，分别写入双方 recipient
  store，并在读回后签发 reciprocal execution receipt。

这不是主体独立 ACK。所有 recipient store 仍由同一受信 controller 写入和读回。

## 来源与适配边界

`source-bindings.json` 冻结四份 `candidate-local` 原始文件的 byte SHA-256。每个 normalized
holder payload 再嵌入同一个 source hash，contract 同时冻结 normalized canonical payload
hash 与 source hash。adapter 新增的 schema/policy 字段只用于满足 executor 的显式输入；
它不增加新的 holder 授权。

当前 source authentication 仍是受信本地 registry 模拟：没有 holder 签名、recipient
独立 ACK、外部 append-only anchor，也不是新的盲测。

ION 第二跳还依赖 `TRUSTED_CONTROLLER_DELEGATION_SIMULATION`：controller 被 contract
明确视为可代表 `NODE-SILVER-RELAY` 执行已授权 onward。它不证明 relay 自主行动、签名委托
或确认收件。

## 运行

```bash
python3 adapter.py
python3 run_integration.py
python3 export_candidate_controller.py
python3 -m unittest discover -s tests -v
python3 score_development.py
```

三个 coordinator-visible 文件只由 `export_candidate_controller.py` 从上述执行结果导出，
不得手写 completion。随后产生的 V2 与分数均标为 `DEVELOPMENT_POST_FEEDBACK_NOT_BLIND`。

公开 scorer 调用为
`python3 scorer.py --submission candidate-submission-v2.json`。当前真实开发候选结果为
`FAIL / 4 of 8 / 0.50`：R2、R5、R6、R8 通过，R1、R3、R4、R7 失败；机会召回 3/3，
false wakeup 为 0。它不是新盲测结论，也没有证明现实效果。

开发候选的公开 scorer 初次结果必须原样保留。若真实 controller event ID 与 evaluator
预设 ID 发生等价性冲突，`diagnose_scorer_id_sensitivity.py` 只能产生
`INVALID_EVALUATOR_DIAGNOSTIC_NOT_CANDIDATE` 反例；其输出不得替换开发候选或执行证据。
