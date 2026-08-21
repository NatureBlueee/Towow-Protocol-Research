已完成第二批 G1 独立研究与最小可运行候选。

- 实际创建并运行了 A/B/C 三名子 Agent，分别完成 evaluator 重建、独立实现和盲攻击规范。
- 主候选包含 10 个 worlds、独立 oracle、4 类基线、6 类回放及事件向量。
- 主候选 `19/19`、B 独立候选 `18/18` 测试通过。
- 已捕获 truth transplant、未来证据注入、wrong Authority、forbidden disclosure、同源 alias、分母污染和 candidate 自报成本/arm 等攻击。
- 未修改 `NOW.md`、`PROGRAM.md` 或任何正式状态。

关键负结果：两个实现仍是同一权限域内的接口纪律隔离，不能宣称可抵抗反射或恶意 worker 的 oracle 泄漏。因此当前是可运行 discriminator candidate，不是正式 leak-free evaluator，也没有方法或机制获得晋升。

交付入口：

- [G1-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-002/G1-final.md)
- [README.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g1-provenance-discriminator/README.md)
- [tests/test_discriminator.py](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g1-provenance-discriminator/tests/test_discriminator.py)