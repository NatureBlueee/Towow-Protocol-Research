已完成第二批 G4 cohort，所有新增内容仅位于指定实验目录，未修改 NOW、PROGRAM、LineContract 或正式状态。

核心交付：

- [G4-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g4-dual-outcome-discriminator/G4-final.md)
- [README.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g4-dual-outcome-discriminator/README.md)
- [fixture.json](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g4-dual-outcome-discriminator/fixture.json)：14 worlds / 7 paired cases
- [results-summary.json](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g4-dual-outcome-discriminator/results-summary.json)
- [runner.py](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g4-dual-outcome-discriminator/runner.py)
- [primitive_services.py](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g4-dual-outcome-discriminator/primitive_services.py)

实际并行创建并收到 A/B/C 三名内部研究者返回。主实现包含四个不同源码 worker：static、mature composite、same-permission strong center、legitimately delegated center；method sabotage 测试确认不是函数 alias。

主要结果：

| 方法 | P1 success false reliance | Safe recall | Abstention |
|---|---:|---:|---:|
| Static | 0.500 | 0.625 | 0.286 |
| Mature composite | 0.375 | 0.714 | 0.286 |
| Same-permission center | 0.375 | 0.714 | 0.286 |
| Delegated center | 0.000 | 0.143 | 0.429 |

这说明合法委托中心的零 FP 来自低 recall，不是总体胜出；成熟组合和强中心在此有限分母结果相同，但仍有 3 个 success FP，不能宣称 G4 已闭合。

验证结果：

- 主实现：13/13 tests PASS
- 研究者 B 独立原型：6/6 PASS
- Pair audit：7/7 PASS
- 两个 hard pairs：各枚举 73 条、深度 ≤2 的合法 action sequence，无 transcript 分流
- `runner --self-test`、`py_compile`、三个 JSON 校验全部通过
- response-lost 实际执行 submit/readback；wrong-object 不计 resolution；重复 Effect 为 0

当前结论严格保持为本地合成 discriminator pilot。hard-pair 全称只适用于冻结的有限动作字母表和深度；尚未获得独立 blind truth owner、真实 X1 output、现实 Authority/Effect/Acceptance，因此没有扩至 2160/17280。

