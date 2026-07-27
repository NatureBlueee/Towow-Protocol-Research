# 通爻协议长期研究实验室

这个工作区用于持续研究通爻及其相邻问题，不限定某一轮、某一种 Agent、某个工具或某套
既有理论。当前环境的设计原则是：

> 高自主、低官僚；允许大胆探索，用事实和可追溯性兜底。

## 从这里开始

1. 读 [`AGENTS.md`](AGENTS.md)，了解研究自由与少量硬边界。
2. 读 [`research/NOW.md`](research/NOW.md)，恢复当前研究现场。
3. 按问题选择相关来源、项目和实验，不必遍历整个仓库。
4. 需要时运行：

```bash
make check
make env
make new-study STUDY=<short-name>
```

这些命令只帮助检查环境和创建空白研究空间，不规定研究方法。

## 工作区

```text
.
├── AGENTS.md        # 唯一长期 Agent 宪章
├── research/
│   ├── NOW.md       # 当前现场和接续点
│   ├── DECISIONS.md # 只记录真正改变方向的决定
│   ├── questions/   # 值得长期保留的问题地图
│   ├── library/     # 来源、阅读笔记和语料索引
│   ├── projects/    # 任意研究线；可以跨轮、跨方法
│   ├── experiments/ # 可独立复用的实验或工具
│   ├── syntheses/   # 跨项目综合与理论演化
│   ├── artifacts/   # 图、数据、代码、论文和演示制品
│   ├── archive/     # 已退出当前现场但需保留的材料
│   └── templates/   # 可选起点，不是必填表
├── Towow_Complete_Research_Archive_v1.2_2026-07-27/
│                      # 截至 2026-07-27 的唯一最新完整源包
├── docs/
│   └── RESEARCH_PLAYBOOK.md
└── towow_a2a_round5_codex_local_research_packet_v1.1/
                       # 当前一条研究线的种子材料
```

## 当前完整研究入口

当前唯一最新源包是：

`Towow_Complete_Research_Archive_v1.2_2026-07-27/`

可工作的研究视图是：

[`research/projects/a2a-reconstruction/`](research/projects/a2a-reconstruction/README.md)

原始包保持不变；工作视图提供文件目录、ZIP 内部索引、长文拆分、研究进程、成果、方法、
证据和方向转折。根目录的 R5 v1.1 packet 仍是重要历史材料，但不是当前总入口。

## 什么值得保存

保存未来研究者无法轻易重建的内容：关键来源、原始实验、反例、方向改变、重要分歧和接续
点。临时思考可以临时存在，不必把每一步都制度化。

当前状态是“环境已准备”，不是理论完成、第五轮完成或任何生产验证。
