# Wave 025 LEAK-ONLY feature collector

状态：`IMPLEMENTED COLLECTOR / NO HOST RUNNER / NO LEAKAGE VERDICT`

## 作用

该 collector 只记录 candidate 在第一个 lawful truth response 前能够观察到的实验表面，用于后续
classifier、permutation test 和 positive-control leak challenge。它不调用 Authority/Target API，
不访问网络，不求解任务，不判断是否“无泄漏”，也不对 A1–A5 排名。

目标容器边界由外部 host runner 提供：

- image：`node:20-slim`；
- `--network none`；
- read-only root filesystem；
- runner 强制的非 root uid/gid（当前资格合同为 `65534:65534`）；
- 独立 PID/filesystem namespace；
- 只读 `/challenge`；
- `/out` 为 tmpfs。

本目录没有实现 host runner。`Dockerfile` 只冻结 collector 的 Node 版本、代码路径和非 root user；
network、namespace、mount 和 tmpfs 必须由调用方建立并留下原生 runtime receipt。
正式 batch 还必须把解析后的 `node:20-slim` image digest 写入 pre-run manifest；可变 tag 本身不构成
冻结证据。

## 唯一输入合同

`/challenge/collector-input.json` 必须逐项等于：

```json
{"schema":"WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}
```

只允许 `schema`。`role`、`expected`、`order`、`seed` 以及任何其他字段均 fail closed，进程退出
码为 `64`。collector 也拒绝任何额外 CLI 参数。

待分类的原始公共输入固定为 `/challenge/input.bin`。collector 不解析其语义，只记录 byte length
和 SHA-256。这样可以检测长度/内容身份是否成为 dictionary feature，但不会把该文件当作 lawful
truth API。

## 输出

成功时同时：

1. 以 exclusive-create 写入 `/out/leak-features.json`；
2. 将相同 canonical JSON 写到 stdout。

输出采用递归 key 排序、UTF-8、单行 JSON 加结尾换行。重复写同一路径会因 `EEXIST` 拒绝，避免
静默覆盖前一份观察。

特征覆盖：

- `argv`；
- env key、value byte length 与 value SHA-256（不复制任意 env value）；
- `cwd`；
- `/challenge`、cwd、`/out`、`/tmp`、`/proc/self/fd` 的有界 directory tree 和 metadata；
- hostname；
- `/proc` process/cmdline/namespace view；
- uid/euid/gid/egid/groups 与 user info；
- wall/monotonic/process/OS timing、立即采样 jitter、input-stat latency；
- `input.bin` byte length/hash；
- 三个固定只读 error-shape probe；
- `/challenge` 文件名、symlink target、64 KiB 以内文件内容及 env 中可见的
  `WAVE025_CANARY_*`。canary 只输出位置、长度和 hash，不复制 token 原文。

directory tree 最多 2048 条、深度 5；process view 最多 256 个 PID。截断会显式记录，不能把截断
后的“未发现”写成不存在。

## 安全与解释边界

- collector 不应被赋予任何 lawful truth endpoint 或凭据；
- env value 用 hash 表示，但 env key、argv、process cmdline、路径和 symlink target 是原始可分类
  特征，运行环境必须保证其中没有真实密钥；
- 输出出现 canary 只证明该 canary 对 collector 可见；未出现不证明所有 side channel 都不存在；
- classifier chance accuracy 还需要预冻结样本量、置信区间、held-out clones 和 injected-leak
  positive control；本 collector 不做这些判断；
- Docker 默认 hostname/container metadata 本身可能成为 feature。是否固定、随机化或保留测量，
  由后续 qualification experiment 决定，不能在 collector 内偷偷归一化。

## 本地测试

无需第三方依赖：

```bash
node --test test/collector.test.js
```

测试覆盖 canonical JSON、严格输入拒绝、全部特征族、canary hashing、symlink 不跟随、process
view、错误形状、exclusive output，以及源码无 network client。

## 容器调用形状（说明，不是 host runner）

调用方需要建立等价于以下边界的容器；stdout 可在 tmpfs 随容器销毁前保留同一份 canonical
结果：

```text
docker run --network none --read-only --user 65534:65534 --pids-limit 64 \
  --mount type=bind,src=<frozen-challenge>,dst=/challenge,readonly \
  --tmpfs /out:rw,noexec,nosuid,nodev,uid=65534,gid=65534,mode=0700 \
  <frozen-collector-image>
```

调用方不得追加 role/expected/order/seed 参数，也不得把 selector root、其他 arms、共享 provider
conversation 或 evaluator fixtures 挂进容器。
