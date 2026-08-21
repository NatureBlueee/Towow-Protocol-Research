# Wave 025 host runner

状态：`IMPLEMENTED HOST EVIDENCE RUNNER / NO CLASSIFIER / NO VERDICT`

本目录只实现冻结合同中的 host runner。它不会 import 或启动 evaluator，不训练 classifier，不输出
blindness/qualification 判断，也不比较 A1–A5。

## 命令边界

```text
prepare -> anchor -> run -> close -> reveal
```

- `prepare` 先从六个公开 exact path 和一个 0600 私有 exact path 读取 canonical JSON，校验登记 schema，以
  exclusive create 逐字节复制到只读 `frozen-inputs/`；然后生成
  `public-plan.json`、0600 `runner-private-state.json` 和最后一个
  `precommit.json`，随后立即停止；
- `anchor` 只记录已经由外部产生的一个或多个 root receipt，不创建 commentary、Git object 或
  远端锚；
- `run` 按 sealed private order 调用 `docker create/inspect/start/logs/exec/kill/wait/events/rm`；
  ready 前只读 logs/inspect，ready 后按冻结顺序执行五次 non-root `/bin/cat`，并保存
  pre/post 原始 inspect、daemon events、supervisor control 与五份 extraction bytes；
- `close` 只在 exact population、全部文件/hash 和 D0 私有 predecessor provenance 完整时写
  `CLOSED`，否则永久写 `ABORTED`；
- `reveal` 只接受 `CLOSED`，公开三个 seed/nonce、完整 mapping/order、私有 control registry 和
  close 已绑定的 D0 exact provenance preimage，并重建全部 commitment。

任何已有正式文件都不会覆盖。candidate 只挂载 batch root 之外的精确 challenge template；batch
root、`runner-private-state.json`、Docker socket、其他 slot 和 evaluator material 不会挂载。

## 镜像准备

只使用本机已有 base，不在 runner 中隐式 pull：

```bash
docker build --pull=false -t wave025-leak-collector:local ../attackers/leak-only-collector
```

`prepare` 同时读取最终 content-addressed image ID、最终 RepoDigest（本地 build 可以为空）和
`node:20-slim` 已解析 RepoDigest。任何一项在 `run` 前漂移都会 fail closed。

## V1.4 自包含冻结输入与私有 control registry

`prepare` 不再接受 caller-supplied `feature_spec_sha256` 或
`evaluator_source_sha256`。它要求六份实际 JSON bytes：

| prepare 参数 | 登记 schema | batch 内文件 |
| --- | --- | --- |
| `--feature-spec-path` | `WAVE025_FEATURE_CLASSIFIER_SPEC_V1` | `frozen-inputs/feature-spec.json` |
| `--executable-attack-profile-path` | `WAVE025_EXECUTABLE_ATTACK_PROFILE_FULL_V1` | `frozen-inputs/executable-attack-profile.json` |
| `--shared-evidence-profile-path` | `WAVE025_SHARED_EVIDENCE_PROFILE_CANDIDATE_V1` | `frozen-inputs/shared-evidence-profile.json` |
| `--control-family-registration-path` | `WAVE025_PUBLIC_CONTROL_FAMILY_REGISTRATION_V1` | `frozen-inputs/control-family-registration.json` |
| `--host-only-inventory-path` | `WAVE025_HOST_ONLY_INVENTORY_V1` | `frozen-inputs/host-only-inventory.json` |
| `--independent-evaluator-source-manifest-path` | `WAVE025_INDEPENDENT_EVALUATOR_SOURCE_MANIFEST_V1` | `frozen-inputs/independent-evaluator-source-manifest.json` |

每份输入必须是普通非 symlink 文件、只包含一个 UTF-8 JSON value、无重复 key，
且已经是 runner canonical bytes（递归 key 排序、compact separators、UTF-8、末尾仅一个 LF）。
runner 不会在 prepare 时替输入改写或美化 JSON；非 canonical 材料需先在 batch
之外生成正式 canonical 发行 bytes。

`precommit.json#/frozen_inputs` 以固定顺序逐项绑定 `name`、相对路径、`schema`、
exact SHA-256 和 byte length。`anchor/run/close/reveal` 每次入口都会重读六份
batch-local bytes，并同时复核 canonical framing、schema、文件模式、长度和哈希。未知、
缺失、重复、重排或任一字节变化都 fail closed。

public registry 的 `feature_spec_sha256` 必须逐字等于本批 frozen feature-spec 的 raw
SHA-256；frozen executable profile 的内部 `profile_id` 必须与 public/private registry 一致，
其 `feature_spec_binding` 还必须逐项匹配同一 frozen feature 的 raw hash、byte length 和 schema。
这些交叉检查发生在写 batch root 和调用 Docker 之前。precommit 中 frozen profile 的 exact
entry hash负责绑定实际 profile bytes；标识符一致或几个哈希各自合法不能代替这条交叉链。

第七项 `--private-control-registry-path` 必须是 canonical、普通非 symlink、exact mode `0600`
的 `WAVE025_PRIVATE_CONTROL_REGISTRY_V1`。runner 严格按已落盘 registry 结构读取
`role_labels`、`families[].role_mappings`、`material_provenance` 和
`per_family_canonical_sha256`，不从 assignment seed 另造 D0/D1 值。它同时要求：

- `public_registration_sha256` 精确等于冻结的公开 registration bytes；
- public/private `profile_id`、family ID、challenge 与两个 role mapping 一致；
- D0 tag 与 `candidate_visible_basename` 逐字节绑定，D1 token 长度与两个 visible source 一致；
- 每个 private family 的 canonical SHA-256 能从实际 family object 重算；
- 当前 preformal registry 只允许显式复用已揭示的 D1，并要求 D0 是本候选新生成的 CSPRNG 材料；
  同一份 registry 进入 formal 会 fail closed。

私有 registry 不复制进公开 `frozen-inputs/`。其 exact 解析值只进入 0600 private state；
precommit 只公开绑定 raw SHA-256、byte length、schema、状态、role labels 与逐 family hash。
只有成功 close 后，reveal 才公开原 registry。

V1.4 precommit schema 是 `WAVE025_BATCH_PRECOMMIT_V1_4`；新 runner 不会继续旧 V1
precommit。旧 F 保持历史不变，不会被自动升级或改写。

## 非资格 smoke

```bash
python3 runner.py prepare \
  --batch-dir /absolute/host-only/w025-smoke-001 \
  --batch-id w025-smoke-001 \
  --mode smoke \
  --feature-spec-path /absolute/frozen-sources/feature-spec.json \
  --executable-attack-profile-path /absolute/frozen-sources/executable-attack-profile.json \
  --shared-evidence-profile-path /absolute/frozen-sources/shared-evidence-profile.json \
  --control-family-registration-path /absolute/frozen-sources/control-family-registration.json \
  --private-control-registry-path /absolute/private/control-registry.json \
  --host-only-inventory-path /absolute/frozen-sources/host-only-inventory.json \
  --independent-evaluator-source-manifest-path /absolute/frozen-sources/independent-evaluator-source-manifest.json
```

将 prepare 输出的精确 precommit SHA 写到 runner/candidate 无法改写的位置后，准备一个或多个
严格四字段 receipt：

```json
{"kind":"USER_VISIBLE_COMMENTARY","reference":"thread:<message>","anchored_at":"<UTC RFC3339>","precommit_sha256":"<exact sha256>"}
```

然后只记录 receipt 并继续：

```bash
python3 runner.py anchor --batch-dir /absolute/host-only/w025-smoke-001 \
  --receipt-file /absolute/already-created-root-receipt.json
python3 runner.py run --batch-dir /absolute/host-only/w025-smoke-001
python3 runner.py close --batch-dir /absolute/host-only/w025-smoke-001
python3 runner.py reveal --batch-dir /absolute/host-only/w025-smoke-001
```

本地 smoke 默认每个 challenge 的 calibration/holdout 各 2 个 slot，共 12 个，不具资格效力。
formal 默认严格生成 3200 个 slot：D0 100+100、D1 100+100、T 400+2400；测试不会运行它。

## D0、D1 与 T

- D0：每 slot 先验证 host residue 是空目录，再由同 UID sacrificial predecessor 只创建 registry
  为该 role 选择的 `d0-residue-v1-<32 lowercase hex>` 空普通文件，mode 固定 `0400`；host 随后
  把目录固定为 `0555`，candidate 以只读 mount 将其作为 cwd。host 在 candidate 前后都验证
  basename/content/数量/mode，collector receipt 还必须在实际 cwd tree 中返回同一 marker；
- D1：与 T 使用同一强 OCI profile，但 `/challenge` 内加入 current-run canary file；
- T：所有 slot 共享同一个只读 challenge template，没有 D0 residue 或 D1 canary，container name、
  hostname、argv/env/cwd 不由 role 派生；runner 额外拒绝 `/shared-residue` mount/cwd 或 collector
  receipt 中任何已登记 D0/D1 private instance 及其派生表示。T receipt 的 challenge tree 必须
  可用、未截断、无错误，并且 closed inventory 恰为 `.`、`collector-input.json`、`input.bin`；
  `visible_canaries` 必须严格为空。派生拒绝集至少覆盖 D0 basename/tag/hash，以及 D1 token、
  token filename、token hash、filename hash 和 exact file-content hash。

runtime `templates/` 本身也不是可信输入。runner 在首次 run 建立或接管它时，要求 templates root
和每个 template 都是真目录、固定 mode、无未知项；每个文件必须是普通非 symlink、mode `0444`
且 exact bytes 匹配。T/D0 只允许两个固定文件，D1 只多出该 slot registry token 的 exact file。
同一检查还会在每个未完成 slot 启动前再次执行，因此 resume 不能沿用被 between-slot 污染的
template。预置一个包含已登记 D1 token 的 `t-isolated` 会在任何 slot 启动前 fail closed。

D0/D1/T 的上述检查是 `registered_control_integrity`，失败归类为
`CONTROL_INTEGRITY_MISMATCH`，不参与 classifier scoring。包含私有 D0 basename 的 predecessor
exact command/inspect/tree receipts 只保存在 0600 runtime journal；pre-reveal shared
`host-launch.json` 只保留 role-free hash/length/count/前后数量摘要，不包含 predecessor command。
`close.json` 绑定全体私有 provenance manifest 与 Merkle root，`reveal.json` 再嵌入 exact canonical
preimage，因此独立 evaluator 能复核“前空 → predecessor 创建 → candidate 后仍恰一 marker”。
close 不只计算 preimage hash：它要求恰好六份 command receipt，并逐份验证 exact schema、顺序、
argv、returncode、stdout/stderr 和不重叠的 monotonic interval；三次 inspect 必须绑定同一
container ID/name、batch/slot/owner labels、image、non-root user、可写 residue mount、隔离参数和
pre-start/completed exit state，create/start/rm stdout 与 runtime 前后 snapshots 也必须相符。
六个包含 marker 的任意对象即使重算全部外围 hash，仍会使 close `ABORTED`。

三个 challenge 使用逐字节同一的 frozen PID1 supervisor script。它把 collector
stdout/stderr 写入独占 `/out` tmpfs，collector 退出且 ready/exit-code 写好后，才向
daemon log 发出精确的 role-free ready frame。host 在此之前不启动任何 container exec；
之后只按 precommit 中的固定顺序使用
`docker exec --user 65534:65534 <name> /bin/cat <exact-path>` 读取 ready、exit-code、
collector stdout、collector stderr 和 features。

读取完成后 host 只向 PID1 发 TERM；supervisor 必须以 collector 原退出码退出。post-inspect
后，runner 以 exact container ID 读取 create→die 时窗的 daemon JSONL，必须重建恰好五组
`exec_create/exec_start/exec_die`，且不存在额外 exec。script hash、ready frame、exact
command template、raw command receipts 与 event JSONL 都是证据。这个边界依赖受信任
Docker daemon，不声称能阻止 daemon/host admin 隐瞒行为。

cleanup 只对 exact generated name 执行，并在删除前从 daemon 复核 batch/slot ownership labels 和
`Running=false`；从不使用 glob、`docker rm -f` 或清理其他容器。

## 测试

```bash
PYTHONPYCACHEPREFIX=/tmp/wave025-pycache python3 -m unittest -v test_runner.py
```

17 项测试覆盖 12-slot 同批 smoke、D0 marker 实际可见、跨 split role mapping 稳定、T 零 ingress、
raw channel 字节相等、五次 exact exec、15 条 exec events、formal 3200-slot 计划、六项
exact/self-contained copy、私有 registry 0600/公开 hash/role mapping/formal reuse 拒绝、preformal
D1 显式复用允许、任一 frozen input 字节篡改、预置 D1 token 的 T template 反例、template
bytes/mode/symlink/extra-entry 反例，以及篡改 T receipt 的 tree/canary/private-derivative 二次防线、
actual public registry/frozen feature 错配、profile 链错配、六对象伪造 predecessor provenance、
未知/重复 input、旧 precommit 拒绝、全生命周期重校验、exclusive create、错误 anchor、
缺失人口 ABORT 和 ABORT 后拒绝 reveal。它不替代真实 Docker smoke。

fake Docker 只模拟本测试需要的 container lifecycle、mount inventory、challenge/cwd tree 和
visible-canary receipt；它不模拟真实 bind-mount kernel enforcement、Docker Desktop/daemon
竞态、权限域或恶意 host。预置 template 反例使用真实 host filesystem 校验，mutated receipt
和伪造 predecessor 测试只证明 runner 的 defense-in-depth 语义判定；哈希与 receipt 结构闭合
不证明命令真实执行，也不能抵抗能伪造可信 Docker daemon/host 证据的主体。这些测试都不是对
真实 Docker 隔离的资格证据。

## 当前限制

- runner 没有实现 evaluator、classifier 或 qualification verdict；
- **真实 release blocker：** 当前 public control registry 的
  `feature_spec_sha256=8398fb773dca1f7da1edd9a5dcef742f27db7ee954fc9f90de8de56713f1236a`
  绑定既有 pretty/non-canonical `feature-spec/FEATURE-SPEC.json` raw bytes，而 V1.4 runner
  对六个 frozen JSON 只接受 canonical bytes。因此现有 V1 feature spec 与现有 canonical
  public/private registries 不能共同组成一次真实 prepare。不得重写或改绑 F 已冻结的 V1；G
  必须等待未来 canonical V2 feature-spec release，并由其 exact hash 重新生成 public/private
  registries；runner 现在会在 prepare 阶段真实拒绝当前错配，而不只是记录限制。测试使用的
  自洽 canonical surrogate/profile/registries 只证明 runner 接口、执行路径与失败行为，不证明
  这组现实 V1 工件已经可运行。未来 V2 还需要显式升级 runner 接受的 frozen schema/registry
  ID 与状态，不会因文件出现而自动受理；
- 第一个实现是顺序 runner，不把吞吐量当资格主张；
- started candidate 不自动重跑；进程在 terminal receipt 前崩溃会保留 raw evidence，并使 close
  `ABORTED`；
- D0 是登记过的 weak-OCI contamination 正控，不是 macOS host `/challenge` 复现；
- Docker Desktop/kernel/hypervisor/host admin 仍在信任边界；
- formal 3200-slot 的成本、时长与功效由冻结合同负责，尚未执行；当前唯一 private registry 是
  preformal D1-reuse candidate，runner 会拒绝用它启动 formal，必须先生成并登记 fresh formal
  registry。
