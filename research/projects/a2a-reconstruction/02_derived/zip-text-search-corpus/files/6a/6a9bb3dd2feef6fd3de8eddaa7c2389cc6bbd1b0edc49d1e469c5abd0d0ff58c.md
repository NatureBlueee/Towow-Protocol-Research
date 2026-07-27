# Round 05 — Recovery and Handoff Alignment

第二次开放复核后，两位主体均 `COUNTER`，并接受同一候选方向但拒绝仅凭设计冻结：

- 删除一次 HTTP response 等于 capability delivery；
- 删除 browser storage 作为 bearer authority；
- 删除 mutation response 等于 adopted postcondition；
- 删除 Playwright 页面进程冒充 World；
- 删除只有 class method、没有真实 route 的 revision/revocation。

共同要求：

1. authenticated session + client operationId 在执行前存在；prepare 重试收敛到同一 reference；
2. `prepared → artifact_persisted → decided` 不可偷换；
3. adoption/revision 与 stable World outbox event 在同一 atomic record；
4. World 独立凭证执行 claim → 自己持久化 → ack；ack 前崩溃可重取同一 eventId；
5. ProductShell mutation 后只信 independent canonical read-after-write；
6. revision 使用 expectedRevision CAS，update operationId replay 不增加 revision；
7. response loss、abort、World persist 前后 crash、ack loss 是冻结前 Witness；
8. bearer、正文、raw tenant、query 不进入 projection/evidence。

该轮形成的关键 Design Delta：联合能力的本体不只包括“状态和 authority 在哪里”，还包括
authority 如何可恢复地到达另一个主体并由它确认接手。
