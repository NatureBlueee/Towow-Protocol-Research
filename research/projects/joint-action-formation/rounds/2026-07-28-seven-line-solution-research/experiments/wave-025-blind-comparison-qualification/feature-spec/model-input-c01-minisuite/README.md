# C01 control compatibility minisuite V3

状态：`SCOPED SYNTHETIC MINISUITE CANDIDATE / NOT MODEL-INPUT CANON / ACTUAL D0/D1 UNKNOWN / G AND 3200 NOT RUN`

V3 回应 `FINAL-INDEPENDENT-ACCEPTANCE.md` 剩余的能力边界、递归 closure、外部 seal、source
binding 与 row-ID oracle 问题。它没有修改 proposal、redteam、routing、primitives、admission、
旧 engine/reference，也没有把任何 actual control、MODEL-INPUT、G 或 3200 描述成已完成。

## Freeze 的最小 capability surface

每个 case 的 freeze 不再从工作区直接运行主脚本。outer wrapper 创建一个 mode `0700` 的随机临时
目录，只放四个文件：

- mode `0500` 的当前 worker code copy；
- mode `0400` 的 exact canonical contract；
- mode `0400` 的单个 feature case；
- mode `0400` 的 calibration-only join。

完整 `CASES-LABELS.candidate.json`、membership source、其他 case、holdout join、private registry、
workspace 路径和其他研究材料都不进入这个 root。worker 用 `python3 -I -S -B`、最小 environment
和该临时目录作为 cwd 启动；Python audit hook 在读取任务文件前安装，允许系统 runtime 与临时
root，拒绝其他 filesystem read。每次 freeze 都实际尝试打开工作区 full-label artifact；该操作
必须得到 `PermissionError`，否则 worker 失败。

receipt 保存：临时 root 初始文件名、mode、bytes/hash；worker 的实际 `$CAP` read/write set；被拒
external read 的 path digest；outer 对 worker output exact bytes 独立计算的 SHA/length。正常 freeze
read set 必须严格为 contract、case、calibration join；write set严格为 frozen output。

这是受信任 Python worker 的可检查 capability surface，不是抵抗任意 native code、拥有 controller
权限的恶意进程或内核攻击的密码学隔离声明。

## 两阶段与独立外部 seal

freeze 在不可读 holdout labels 时完成 universe、rule、calibration/holdout predictions，并写出
canonical frozen package。outer wrapper 在 worker 退出后读取 exact bytes、独立计算 hash，再将
package复制到另一个新的 score capability root。expected frozen hash通过 wrapper environment提供，
不在 package/payload 中自报。score 只有 contract、frozen package、holdout-only join；没有 feature
rows，也没有 selection 所需 calibration feature rows/labels。

因此：

- package 与“同步修改后的自报 hash”不再是一个可共同替换的输入；
- exact bytes 不等于 wrapper 的先验 expected hash时，在 parse/score 前失败；
- score 即使收到攻击者按变异 package重算的 hash，也会由递归 schema closure拒绝任何
  `feature_rows` 或其他未声明字段。

contract、case、calibration join、frozen package、holdout join的 expected binding 都必须是非空、
非全零 lowercase SHA-256，并逐字节核对。contract还必须逐字段等于 worker当前构造的 V3 contract；
错误、全零或只改 hash不改 bytes都 fail closed。

## 递归 closed，不只检查顶层

freeze 对 case、rows、categories、numeric value和 calibration join逐层核对 exact keys，并递归拒绝
label-like key。`case.holdout_labels`、`row.metadata.role` 等嵌套绕过均失败。

score 对 frozen package、source bindings、universe、每个 family freeze、metrics、predictions、rule、
selector与 numeric value逐层 exact-key 校验，并复算内部 hash。`frozen_package.feature_rows`、rule
extra、prediction extra或任一未声明嵌套字段均失败。结果中的 false/true 字段不再承担 admission
证明；receipt 与攻击回归承担。

## Independent opaque membership

`OPAQUE-MEMBERSHIP.candidate.json` 是一次性 OS CSPRNG 生成的 640 个固定 opaque row IDs。生成 seed、
slot号和 row-ID 映射没有保存。`CASES-LABELS` 是独立的 row_id→synthetic class source；正常 `--write`
只读取并验证这两份固定 source，不再从 `(case, phase, slot)` 重生。

`initialize_membership_sources.py` 只用于显式的一次性初始化；正常 build不调用它。公开 worker code中
不存在 `opaque_row_id` 或 `label_assignments`。旧 V2 枚举攻击对新 640 IDs 命中为 0/640。

这不声称 intended predictor 无法预测 label：P1/P4/P5 本来就是正控。边界是 metadata-only：移除
categories/numerics后，P3/P7 的 F1/F2/F3 calibration/holdout BA 都为 0.5、没有 rule、没有 stable；
row ID、case/phase、membership metadata不能救回负控。full label source不在 freeze capability root，
且实际 read probe被阻止。

## C01 局部语义保持

- F1：一个 calibration-universe `context+token` selector；unknown token被忽略，只应用
  selector presence/absence branch。P8固定其 OOV真值。
- F2：一个 context 的 exact `sum(count)`/`MISSING` mapping；未见 state frozen fallback R。
- F3：一个 numeric identity 的 exact rational/`MISSING` mapping；未见 state fallback R。
- F4：继续 `REJECTED_UNDERDETERMINED_NOT_EXECUTED`。不以 `00/01/10/11` lookup冒充登记的
  two-token conjunction。

三个可执行 family的 calibration support、balanced accuracy、complexity和 canonical UTF-8 tie保持
V2 定义。stable同时要求同一冻结 rule 在 calibration 与 holdout 的 R/S recall全部精确为 1。

## 合成结果和来源边界

P1 中 F1 恢复，只说明公开 D0 design 的理想 stable atom与 F1机制兼容；actual D0 未运行。P2 继续
是 conditional：当前公开 D1 registration没有绑定 cross-phase stable atom，actual D1为 Unknown。
P3不恢复；P4仅 F2；P5仅 F3；P6的 F4不执行；P7保持 OOV负结果；P8保持 F1 truth table。

V3 不裁决四族最终保留集合，不把 synthetic recovery外推为 actual sensitivity、CI或现实功效。

## 文件与复现

- `OPAQUE-MEMBERSHIP.candidate.json`：独立固定 membership source；
- `CASES-LABELS.candidate.json`：独立 synthetic controller label source；
- `CASES-FEATURES.candidate.json`：由上述 source 构造的 role-free predictor fixtures；
- `C01-MINISUITE-CONTRACT.candidate.json`：V3 semantics/capability/binding contract；
- `FROZEN-SELECTIONS.candidate.json`：外部 sealed frozen packages与 actual read-set receipts；
- `RESULTS.candidate.json`：holdout-only score process结果与 bindings；
- `THIRD-FIX-AUDIT.md`：第三轮修复、攻击回归和仍存边界。

```bash
python3 c01_minisuite.py --check
python3 -m pytest -q tests
```

`RESULTS` 绑定 membership、features、labels、contract、frozen selections、generator、initializer、
tests、README及两个公开 control sources。正常 build不会刷新 opaque membership或 label mapping。

## 不能说明什么

V3 仍不证明 actual V2S receipt、fresh formal registry、actual D0/D1 sensitivity、class-wise CI、T
role-null/zero-ingress、model-input matrix bytes、双 clean-room provider、真实 Docker G、actual-shape
成本或 formal 3200。F4 仍未闭合。即使同一 reviewer接受本 minisuite的 scoped内部语义，也不会自动
解锁这些外层 gate。
