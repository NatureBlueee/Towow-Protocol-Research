# Cohort 003 共同执行约束

1. 完整读取根 `AGENTS.md`、CE-001 contract、cohort 002 的
   `ROOT-ADVERSARIAL-AUDIT.md` 与 `SYNTHESIS.md`。
2. 只写自己的 line 目录和本 cohort 自己的 `Gx-final.md`；不修改 contract、NOW、PROGRAM、
   Problem、LineContract 或机制状态。
3. 实际建立三个内部 Agent：
   - A 独立重建本线原始问题与 CE-001 接口；
   - B 实现最小可运行模块；
   - C 在不知道期待赢家的前提下攻击 truth-copy、alias、目标偷换和伪成功。
4. 强中心、成熟组合、通用模型、人工制度、平台直达完整解决都是正结果；不为新机制制造
   residual。
5. 不得共享一个 `_common_candidate`、`choose(packet)` 或 decision root 后比较 arms。
   本轮是 line module，不需要虚构 arm 比较。
6. solver 不读 private expected label；owner truth、Authority、Effect 和 Acceptance 由各自
   owner/service 产生。
7. 把真实产品运行与 local component model 分开。产品未安装就写 `NOT_RUN`。
8. 实现必须有 raw trace、failure injection、最接近风险的 tests 和诚实证据边界。
9. 若 contract 有缺陷，先构造能区分缺陷的反例并在 final 标为 `CONTRACT_REOPEN_CANDIDATE`；
   不擅自改写合同。
10. 完成后写 `external/codex-cli-cohort-003/Gx-final.md`，包含实际内部 Agent identity、
    运行命令、数字、红灯历史、能支持/不能支持和下一接口。
