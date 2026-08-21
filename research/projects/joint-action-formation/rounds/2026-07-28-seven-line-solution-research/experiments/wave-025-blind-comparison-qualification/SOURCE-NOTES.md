# Wave 025 source notes

日期：2026-08-01  
状态：`PRIMARY-SOURCE NOTES / NO VALIDITY CLAIM`

这些资料只说明可复用技术与正确的结论边界，不替代本地 qualification evidence。

## 容器隔离

1. NIST SP 800-190 把 application container 定义为 OS virtualization + software packaging，
   同时明确其建议假定 supporting hardware、hypervisor、OS、管理工具与管理员端点另行得到
   安全保护。设计含义：OCI cell 是登记威胁模型中的成熟隔离组件，不是对 host administrator、
   hypervisor、kernel 或物理侧信道的普遍 noninterference 证明。
   - https://csrc.nist.gov/pubs/sp/800/190/final
   - https://doi.org/10.6028/NIST.SP.800-190
2. Docker 官方运行文档提供 `--network none`、read-only root filesystem、non-root user、
   capability drop、`no-new-privileges`、resource limits、bind/tmpfs mount 等现成控制面。设计含义：
   Wave025 不需要自研容器内核，但必须保存 daemon actual inspect；命令期望值不是运行证据。
   - https://docs.docker.com/reference/cli/docker/container/run/
   - https://docs.docker.com/engine/containers/run/
3. Docker 官方安全文档说明 namespaces/cgroups/capabilities 等边界，并单独说明 rootless 与
   `userns-remap`。设计含义：容器内 `uid=65534` 不等于 daemon rootless 或 host user-namespace
   remap；本轮必须把它们作为不同事实记录，不能用“non-root”覆盖整个宿主威胁面。
   - https://docs.docker.com/engine/security/
   - https://docs.docker.com/engine/security/rootless/
   - https://docs.docker.com/engine/security/userns-remap/

## “未检出”与经验等价

1. Lopez-Paz 与 Oquab 的 classifier two-sample test 工作说明：分类器若能在独立数据上持续优于
   chance，可以形成分布差异检验，并可使用 label permutation；它没有说明分类器未检出即可
   证明分布相同。设计含义：Wave025 必须先用植入泄漏证明 detector sensitivity，并把通过表述
   为对冻结攻击族、样本和 observation cut 的有界经验资格。
   - https://arxiv.org/abs/1602.02210
2. 等价性文献区分“没有显著差异”和“置信区间进入预先定义的等价边界”。设计含义：普通
   `p>0.05` 不能支持 blindness；需要在 fresh holdout 前冻结可接受的最大攻击优势，并用
   one-sided bound/TOST 逻辑拒绝大于该界的效果。
   - https://doi.org/10.1016/j.rse.2009.03.014
   - https://pmc.ncbi.nlm.nih.gov/articles/PMC3019319/

## 仍需本轮自己回答

上述来源均不能回答：本机实际 image/config 是否等价、hidden role 是否进入 candidate transcript、
assignment 是否可重建、positive control 是否真的可检出、precommit 是否在运行前外部锚定，或
400 个 fresh holdout 是否足以把攻击优势上界压到 0.55。只有冻结实现、真实 batch 与独立
evaluator 可以回答这些局部问题；动态 lawful divergence 与 A1–A5 原生比较仍保持未测试。
