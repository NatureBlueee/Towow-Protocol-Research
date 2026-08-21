# M01 freeze bundle — independent audit 001

日期：2026-07-29  
初审：`REVISE / NOT ACCEPTED AS SCOREABLE-PAIR FREEZE CANDIDATE`

初版虽然通过所有本地 raw/hash/equality 检查，独立只读攻击仍发现八个阻断：

1. public version 与 interface policy 暴露 M01 和唯一分支差异；
2. local expression state 也随分支变化，却被错误归因给 directory owner；
3. directory response 没有 exact bytes、head、owner/global event index 和时间闭包；
4. G1 只交接 calibration candidate，G2/G5 却无来源地增加第二 role filler；
5. 四个 G5 key 仍在同一个 truth assembly 中，单一 Commitment 可以穿门；
6. score mask 使用非正典的 conditional active，可能按方法到达情况缩分母；
7. G5 复合失败桶不能无损映射 X1Outcome reason registry；
8. G3 action-grammar/bound hash 没有可复算前像。

这证明 package hash 全绿只说明“声明与文件一致”，不能证明分母、因果入口、权威归属或评分
边界正确。

## 修复 001

- public 内容移除 motif、branch、expected route 与 M01-specific version；pair policy 只保留在
  private reviewer certificate；
- local expression state 两侧相同，唯一 delta 收敛为 directory snapshot presence；
- 冻结等长 directory response raw bytes、request/payload hash、head、owner-local/global
  index、effective time 与 expiry；
- Intent 公开携带 fixed prequalified witness，`T_G1_TO_G2` 只把该来源与 G1 calibration
  candidate 合成 two-role candidate，仍为 `CANDIDATE_NOT_COMMITMENT`；
- G5 拆成四份 owner-bound truth files/root candidates，assembly 只绑定 raw hashes；四域
  stance/Commitment/head receipts 与 delta resource-owner Reservation receipt 缺一不可；
- score mask 固定为正典枚举，所有 arm/episode 保留在 integration population；
- outcome registry 升级为精确 category/reason pairs，并冻结明确 canonical preimage；
- G3 combined hash 明确为 action grammar 与 transition bound 的二成员 canonical object；
- 删除 `T_G1_TO_G2 ↔ G2 file raw` 哈希环，改为 transition 单向绑定 G2 稳定语义坐标，
  G2 单向绑定 transition raw。

修复后本地验证重新通过。第二次独立只读复审尚未返回；在其接受前，bundle 状态保持
`ASSEMBLED_CANDIDATE_AWAITING_INDEPENDENT_REVIEW`，scoreable population 仍为 0。
