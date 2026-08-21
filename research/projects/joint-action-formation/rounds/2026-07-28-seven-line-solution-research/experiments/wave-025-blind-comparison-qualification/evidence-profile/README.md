# Wave 025 Shared Evidence Profile Candidate

本目录把 runner 与共享 evaluator 之间此前依赖实现细节的证据接口，收敛为一个可机读、可独立复算、且不改写 F 的候选 profile。

## 文件

- `SHARED-EVIDENCE-PROFILE.candidate.json`：字节语义、对象注册表、控制面、随机化、Merkle、feature/profile bytes 与 post-cut 事件接口。
- `SHARED-EVIDENCE-PROFILE.schema.json`：候选 profile 自身的闭合 JSON Schema。
- `RUNNER-EVIDENCE-OBJECTS.schema.json`：八类 runner-owned JSON 的递归闭合 Schema；另含 raw inspect、F-observed raw event 与冻结 event projection 的辅助定义。
- `test_shared_evidence_profile.py`：不导入 runner 或 evaluator 的独立一致性测试。

## 当前证据边界

测试逐一验证 F 的 6 个 root runner 对象、12 个 `host-launch.json`、12 个 `slot-receipt.json`、12 组 raw inspect、228 条 daemon event，以及所有 command receipts、文件哈希、feature bytes、三随机域 commitment、assignment/order/public ID/padding/token 重建和当前 Merkle root。

当前真正的 blocker 只有两项，而且均有明确作用域：

1. F 没有 precommit 任何 executable attack profile bytes，因此不能声称某一份 attack profile 已在运行前冻结。
2. F 只绑定了外部 `FEATURE-SPEC.json` 的哈希，batch 目录内没有对应 bytes，因此不能只凭 F 目录完成自包含离线转移。

Merkle V1 的 leaf/node 没有 domain separation，但当前 evaluator 使用整批全量验证：它独立固定 expected slot IDs/count、每份 receipt bytes 与 closed 全清单，再重算 root；root 不是独立 membership proof。在这个消费模型内，没有发现可行的 receipt 替换或 slot 重排攻击。因此它不是 F/formal blocker；若未来将 root 用作 standalone membership、consistency 或 partial-set proof，则必须采用 profile 中的 versioned V2 或等价的域分离、树形绑定设计。

Docker `Actor.Attributes` 是 daemon-owned open world。当前接口保留 exact raw bytes，只冻结并校验消费到的 semantic projection，未知 attributes 不影响投影结果，所以也不是当前验证 blocker；只有声称跨 daemon 的 exact raw schema 时才会阻断。

## 复现

从本目录运行：

```sh
PYTHONPYCACHEPREFIX=/tmp/wave025-pycache python3 -m unittest -v test_shared_evidence_profile.py
```

预期结果：12 项测试全部通过。测试只读取 F 与冻结来源，不读取 `evaluation.json`，也不修改 runner、evaluator、合同或 F。
