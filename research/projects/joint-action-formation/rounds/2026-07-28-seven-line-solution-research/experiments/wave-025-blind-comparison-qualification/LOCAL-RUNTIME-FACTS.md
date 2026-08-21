# Wave 025 local runtime facts

日期：2026-08-01  
状态：`DIRECT HOST OBSERVATION / V1.3 STRUCTURAL SMOKE CLOSED / NO QUALIFICATION`

## 实际环境

只读 daemon/image 检查得到：

```text
Docker client/server: 29.1.3
daemon OS: Docker Desktop
kernel: 6.12.54-linuxkit
storage driver: overlayfs
security options: seccomp=builtin, cgroupns
rootless: not reported
userns-remap: not reported
base image: node:20-slim
base resolved repo digest/image id:
  sha256:2cf067cfed83d5ea958367df9f966191a942351a2df77d6f0193e162b5febfc0
```

因此 threat model 依赖 Docker Desktop Linux VM/daemon/kernel。容器内 non-root uid 不得被写成
rootless daemon 或 host user-namespace remap。

本地用冻结 Dockerfile/source、`--pull=false` 构建：

```text
tag: wave025-leak-collector:bc18911c
initial diagnostic image id:
  sha256:1b9f1a69457e75161f98aee338ad569f24e57c18197818167a64deabf6ed717e
F bound final image id:
  sha256:1eb2f57e956518e9837000ce84e6b8239e405e4dba0a836d593e932e6f8c143d
image config user: node
entrypoint: ["node", "/app/collector.js"]
working dir: /app
```

正式 runner 仍必须用 `--user 65534:65534` 覆盖 image default，并把 actual image ID 与 source、
Dockerfile、base digest 一起写入 precommit/host receipt。

## 单槽结构 smoke

root 在 formal precommit 之前运行了一个不进入 evidence population 的临时容器，随后只删除该
明确命名、已退出容器。实际 inspect：

```text
exit=0, oom=false
image=sha256:1b9f1a...
user=65534:65534
network=none
readonly_rootfs=true
cap_drop=[ALL]
security_opt=[no-new-privileges=true]
pids_limit=64
memory=134217728
nano_cpus=500000000
ipc=private, cgroupns=private
/challenge bind readonly
/out tmpfs rw,noexec,nosuid,nodev,uid=65534,gid=65534,mode=0700
```

collector 返回 `WAVE025_LEAK_ONLY_FEATURES_V1`，自报 uid/euid/gid/egid=65534、pid=1、只有自身
process view、固定 public input hash，未见 canary。它也观察到每槽会变化的 hostname/container
ID、namespace/inode/pipe/timing 等高基数 feature；这些不能在 collector 内被静默归一化，而要由
fresh holdout 检验它们是否与 hidden role 关联。

## 不能从 smoke 得出的结论

该手工 smoke 没有保存 formal raw pre/post inspect、stdout/stderr/out 三份独立 bytes、precommit、
external anchor、private reveal 或 independent evaluation，所以只证明当前本机可以启动目标安全
配置并成功运行 collector。它不支持 detector sensitivity、prefix blindness、randomization closure
或任何 A1–A5 qualification claim。

后续 A–E 真实 smoke 进一步证明：Docker Desktop 的 archive/`docker cp` 在 stopped 和 running
两种状态都不能读取 `/out` tmpfs。失败批均终止，没有用空 out 或 stdout 代替第二通道。

V1.3 随后冻结 observation-cut-aware 路径：collector 退出后 supervisor 才发 ready；host 在 ready
前只读 logs/inspect，之后用五次精确 non-root `/bin/cat` 读取 tmpfs，TERM 后再从 daemon events
核对只出现这五组 exec。F batch 实际得到：

```text
12/12 COMPLETE; D0/D1/T each 4/4
19 daemon events/slot
5 registered exec groups/slot
0 extra exec
closed SHA = 26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e
reveal SHA = 7f698271d211441ad46b6851d8b219238f6e81b87f72afbdcf6de579adb70287
```

这支持 runner/evidence path 的结构闭合，不支持 blindness。旧独立 evaluator 因新 precommit 字段
与共享接口仍未规范化而 fail closed，正式输出 `NOT_QUALIFIED`；完整 profile 也尚未在 F 中执行。
