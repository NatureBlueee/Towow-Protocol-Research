# Wave 025 frozen feature/classifier plan

状态：`FROZEN PLAN + REFERENCE EXTRACTOR / NO QUALIFICATION RESULT`

## 这份产物解决什么

本目录把 `collector-features.json` 中 candidate 在 `T0→T1` 实际可见的原始观察，确定性地转成
七组 numeric/categorical predictor。它冻结后续 D0、D1、T 的攻击模型、预处理、置信区间、
permutation 与 Holm 规则，但不读取 batch、role、host receipt，不运行 evaluator，也不产生
资格结论或方案排名。

同一个 formal batch 必须同时含：

- D0 predecessor/shared-state contamination：100 calibration + 100 fresh holdout；
- D1 current-run canary：100 calibration + 100 fresh holdout；
- T isolated：400 calibration + 800 fresh holdout；
- 总计 1600 slots，共用一次 precommit、close 与 reveal。

`challenge` 只允许选择 D0/D1/T stratum；private canary family 只允许在 reveal 后选择已预登记的
control subgroup。两者都不是 predictor。role、block、phase、execution order、opaque slot ID、
container ID、host timestamp/config、seed/nonce 与 evaluator material 不能进入 extractor。

## 文件

- `FEATURE-SPEC.json`：冻结的机器可读 plan。包括七类 raw feature、五个预登记 classifier、
  确定性预处理/tie-break、精确 CI、9999 次 block-preserving permutation、Holm family 和限制。
- `reference_extractor.py`：Python 标准库实现。它只接受一个成功的
  `WAVE025_LEAK_ONLY_FEATURES_V1` receipt；未知/缺失/role/host-only 结构字段 fail closed。
- `tests/test_reference_extractor.py`：schema、隔离边界、确定性、逐叶审计、D0/D1 可见面、时间面、
  canonical output 和无科学计算依赖测试。

## predictor 与审计边界

输出中只有以下两个成员可进入 classifier：

```text
features.numeric
features.categorical
```

raw string 不直接复制到 feature vector；保留 exact SHA-256 category、字符串形状与有界 UTF-8
n-gram hash。因此 role-coded cwd/path/process/canary 仍可分类，但输出不扩散原 token。SHA-256
叶只做 exact category，不对十六进制字符做无意义 n-gram 学习。

每个原始 scalar leaf 必须恰好属于 included 或 excluded。允许排除的只有经精确校验的固定常量：
collector schema/version、自述 contract、公共输入 schema 与固定 subject path。每份输出都列出
excluded path、理由和值哈希，并保存 included path-set hash；出现 unclassified leaf 直接拒绝。

同名但不同权限域的字段必须分开理解：collector 自己看到的 PID、hostname、wall clock、目录和
namespace 是合法 predictor；Docker inspect 的 container ID、host clock、执行序号和 slot path
是 host-only，只能在 predictor 外做 role/order association audit。

## 冻结攻击

每个 challenge 独立在 calibration 上拟合，再原样作用于 fresh holdout，禁止跨 challenge pooling
和 holdout reselection：

1. exact/categorical rule scan；
2. L2 logistic；
3. depth-1 decision stump；
4. depth-3 bounded tree；
5. k=11 nearest neighbours。

D0 与 D1 是两个不同的 learned control family，不能互相替代。每个 family 必须在 anchor 前冻结
自己的 primary detector、注入面、预期 collector feature family 和逐 role 人口；该 primary 的
holdout balanced-accuracy 保守 one-sided 95% 下界必须达到 0.90，事后不能用 secondary rescue。
T 的每个预登记 classifier 使用同一 exact bound；普通 `p>0.05` 不构成等价。

CI 先对两个 class recall 分别做 Clopper–Pearson one-sided bound，并用 Bonferroni 将每个 class
tail 设为 0.025，再平均两端。Permutation 在 `challenge × phase × block` 内进行，预测攻击与
host-only role/order association 分开形成 Holm family。

## 运行

```bash
python3 reference_extractor.py /absolute/path/to/collector-features.json > /tmp/features.json
python3 -m unittest discover -s tests -v
```

实现不 import runner、collector 或 evaluator，也不依赖 numpy/scipy/sklearn。reference extractor
不是 classifier 实现；independent evaluator 必须按 `FEATURE-SPEC.json` 独立重建模型和统计量。

## 最强误判方式

最强 false-green 不是“模型碰巧没学到”，而是 observation 本身不完整：未登记的 syscall/cache/
socket，collector 的深度/数量/文件大小上限，fresh unique codebook，高阶 parity 或 candidate 私有
decoder，低频/≤0.55 优势，以及只在多次调用、反馈或 lawful divergence 后出现的泄漏。这一批
对它们仍是 `UNTESTED`，D0/D1 通过不能外推。

最强 false-fail 是有限随机顺序碰上 host/thermal/filesystem drift，或在 holdout 上继续挑模型。
block balance、独立 holdout、support floor、role/order permutation 与 Holm 能压低但不能消灭前者；
任何人工 peek 或事后添加规则会直接使本冻结计划失效。D0/D1 intervention 也可能同时改变 timing/
resource surface，所以控制检出证明的是 detector sensitivity，不证明命中的恰好只有注入通道。

本目录不检验 dynamic broker、earliest lawful divergence、provider/human 跨 run 记忆、evaluator
truth、Authority/Effect/Acceptance、真实 treatment、公平成本、host admin/hypervisor 合谋、
微架构/物理侧信道或生产长期有效性。
