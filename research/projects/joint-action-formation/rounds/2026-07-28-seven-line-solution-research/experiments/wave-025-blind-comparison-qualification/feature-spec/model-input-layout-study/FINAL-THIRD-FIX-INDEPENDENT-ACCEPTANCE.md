# Wave025 model-input layout study V3 第三修复独立复核

状态：`ACCEPT_SCOPED_RETROSPECTIVE_SHAPE_AND_CURRENT_NO_DELETE / REJECT_PROOF_BEARING_DELETE_GATE / REJECT_MODEL_LAYOUT_DECISION_OR_FORMAL_PROMOTION`

本复核只检查 V3 相对上一份 `FINAL-INDEPENDENT-ACCEPTANCE.md` 的三个修复点，
并复跑冻结结果与定向测试。没有修改实现，没有读取 private role、outcome、
`runner-private-state.json`、`reveal.json` 或 private registry。

结论需要拆成两层：

1. **当前冻结包的行为可以接受**：重复 plan/closed 行不能再被 dict/set 去重掩盖；
   当前冻结 expected SHA 能发现 plan/closed 的共同改写；当前 result 没有任何 deletion
   evidence receipt，稳定返回 `UNKNOWN_DO_NOT_DELETE`。
2. **未来删除授权机制仍不能接受**：receipt gate 只验证调用者提供的 JSON 结构、raw-byte
   SHA、固定 scope 字符串和自报 status，没有验证 receipt 的外部发行权、证明内容，
   也没有把 `subject_sha256` 对到任何要求所需的冻结对象。独立构造八份自证
   `SATISFIED` receipt 后，gate 返回了 `DELETE_SIGNED_HASH`。所以它从“八个裸布尔值”
   升级成了“八个 byte-bound 自我声明”，还不是 proof-bearing evidence gate。

因此，本复核保留 V2 已接受的 `SCOPED_RETROSPECTIVE_SHAPE_ONLY`，接受当前不删除的
安全决定，但不接受“删除 gate 已闭合”、MODEL-INPUT 选择、power、C01 closure、G、
正式 3200、正式谱系或任何 hash/family 删除授权。

## 1. duplicate row / slot id：修复成立

`verify_f_lineage_documents` 在任何 dict/set 投影前依次检查：

- plan 与 closed 原始 `slots` 各恰为 12 行；
- 每行是 object；
- canonical row 不重复；
- plan 与 closed 的 slot id 非空且分别唯一；
- routed receipt 和 disk directory 各恰为 12 且唯一；
- 声明数量、list、disk、receipt 数量相同；
- 此后才构造 slot set 和 per-slot mapping。

亲自复跑的两个攻击均被拒绝：

- 向 plan/closed 同时追加完全相同的第十三行，即使把 recomputed SHA 作为测试输入，
  仍以 `plan/closed raw slot row count mismatch` 拒绝；
- 在十二行内部复制已有 slot id，即使重算 expected plan SHA，仍以
  `duplicate public plan slot id` 拒绝。

这足以关闭上一轮“list multiplicity 被 dict/set 隐去”的具体缺口。它仍只是当前 study
的观察性 F lineage verifier，不是 V1.1 semantic admission。

## 2. plan/closed common rewrite：当前冻结锚成立，权威边界诚实

当前执行入口固定：

- public plan SHA-256：
  `09a8fc8a57906bc3d4182af7f3b1f08cccf5c36b2a6c6a07c2ccf1a9033acf72`；
- closed SHA-256：
  `26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e`。

独立把 D0 与 D1 treatment 在 plan/closed 中成对交换、保持 4/4/4 数量与双方一致时，
冻结常量以 `public plan differs from exploratory expected SHA` 拒绝。若攻击者同时向
函数传入重新计算的 expected SHA，同一共同改写会通过 lineage verifier。这与 V3 的
声明一致：它是当前研究文件内的 local anchor，不是 controller seal；能够共同改写 study
与输入的 writer 不在其威胁模型内。

所以可以接受“当前冻结 V3 能检测输入共同改写”，不能升级为外部不可改写锚或正式 admission。

## 3. signed-hash deletion：当前决定安全，未来授权 gate 仍被反例击穿

当前 `RESULTS.candidate.json` 明确记录：

- `evidence_receipts_supplied = 0`；
- validation error 为 `MISSING_EVIDENCE_BUNDLE`；
- decision 为 `UNKNOWN_DO_NOT_DELETE`。

旧式八个全 `true` 的 dict 也因 bundle schema 不匹配而被拒绝。这两个当前行为可以接受。

但以下独立攻击无需任何真实外部证据即可得到删除授权：

1. 对八个 requirement 各自生成一个唯一的 `caller-made-*` receipt id；
2. 使用 gate 公开的固定 scope；
3. 把 status 全写成 `SATISFIED`；
4. 把所有 `subject_sha256` 写成同一个任意合法值 `00...00`；
5. 对每份自制 JSON raw bytes 计算真实 SHA，并把 descriptor 与 raw bytes 一起传入。

实际返回：

`decision=DELETE_SIGNED_HASH, validation_errors=[]`。

根因不是 SHA 验证错误，而是 gate 没有要验证的外部事实：

- `study_issues_receipts=false` 只是输出字段，没有由权限、issuer registry、签名或
  controller provenance 强制；
- receipt 的 `SATISFIED` 是自报值，没有 requirement-specific verifier result 或 proof；
- `subject_sha256` 只检查 64 位十六进制格式，没有与 routing、primitives、split、C01、
  resource ceiling、fixture set 或 lost-pair audit 的冻结 SHA 闭包比较；
- 因而“raw bytes 存在且哈希匹配”只证明自我声明没有在传输后改变，不证明声明为真。

要成为可授权删除的 gate，至少需要由 study 无权发行/改写的 controller 或 trusted issuer
产生 receipt，并把每个 requirement 的 subject 闭包对到明确的 expected artifact hashes、
definition/version 和验证结果。也可以直接由八个 requirement-specific verifier 产生
不可由调用者替代的 receipt。无论采用成熟签名/权限域、append-only 外部账本，还是自持
controller，都应以能阻止上述自制 receipt 反例为验收条件。

当前不需要为了保留安全而删除此函数；只需要继续把它当作结构 schema 草案，并维持
`UNKNOWN_DO_NOT_DELETE`。它不能作为未来 deletion authorization。

## 4. public-treatment-aware 边界

result 与 README 使用的精确表述：

`PRIVATE_ROLE_AND_OUTCOME_BLIND__PUBLIC_TREATMENT_AWARE`

与实际读取相符：split 读取 public plan 的 D0/D1/T challenge assignment，但未读取 private
role 或 outcome。因此该核心边界可以接受。

仍有一处非计算性文字不一致：`layout_study.py` 顶部 docstring 说从不读取
“assignment”，未限定 private assignment，而实现确实读取 public challenge assignment。
这不改变 result 的数值或当前 scoped verdict，但后续修订应改成“never a private role or
outcome assignment”，避免有人只读模块说明时误解为广义 treatment-blind。

## 5. 结果重建与定向验证

- `layout_study.py --check RESULTS.candidate.json`：`RESULT_MATCH`；
- V3 tests：17/17 pass；
- 使用隔离的 bytecode cache 重新 compile：pass；
- duplicate append：reject；
- duplicate slot id：reject；
- 冻结 expected SHA 下 plan/closed common rewrite：reject；
- recomputed local expected SHA 下同一 rewrite：pass，确认 local-anchor 边界；
- 旧 all-true Boolean dict：`UNKNOWN_DO_NOT_DELETE`；
- 八份 caller-made byte-bound self-asserted receipts：`DELETE_SIGNED_HASH`，确认未来授权缺口；
- 当前 frozen result：0 receipt、`MISSING_EVIDENCE_BUNDLE`、`UNKNOWN_DO_NOT_DELETE`。

复核冻结输入 SHA-256：

- `layout_study.py`：
  `493fcb42f90b6e9a6e655e39704aada05e142e9b18a5fed9f5d2a5e2dc523680`；
- `RESULTS.candidate.json`：
  `6900465b3719e53f9d63610726333f85e607935b5e612b120c0a77f7278abab2`；
- `README.md`：
  `c622fffc2bf1adc05760644053da291bb04693cb596f67b551c50b0e04dbebf4`；
- `tests/test_layout_study.py`：
  `052262e15afd50a0d33e07dae6ec2f09db65f3890a0220e02fe4bfe5aa29e3a8`；
- `THIRD-FIX-AUDIT.md`：
  `622d982ced55fcc1b2222b96d39a01ceaae2d5f1a5ae220af86f072cbe5b899e`。

## 6. 最终可用范围

V3 可以继续作为：

> 当前 exact routing 与十二份公开 F receipt 的后验结构/资源账本，并带有更严格的当前
> plan/closed multiplicity 与本地冻结字节检查；当前 signed hash 保持不删除。

它仍不能回答：

> 哪种 layout 能解决 C01；hash width、OTHER、normalization 或 learner 应如何选择；
> singleton 是否有任务价值；signed hash 是否可以删除；任何 detector power、迁移、
> 净价值、G 或正式 3200 结果。

下一步不应再扩大 shape 统计。删除 gate 若要继续，只需对上述 self-issued receipt 反例做
最小而完整的权威来源与 subject-closure 修复；MODEL-INPUT 的主研究资源仍应投向真实 C01
phase boundary、冻结任务和竞争 layout 的独立 probe 比较。
