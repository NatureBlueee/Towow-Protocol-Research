---
derived_view: true
source_path: research/projects/a2a-reconstruction/02_derived/zip-text-search-corpus/files/31/31403fde5285ce077dc0601738d48bf56872406b14145684d8a6bf0395cda536.md
source_sha256: 31403fde5285ce077dc0601738d48bf56872406b14145684d8a6bf0395cda536
source_line_start: 2716
source_line_end: 2813
source_heading: "Flowness 认知编译层建设路线"
---

> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。

# Flowness 认知编译层建设路线

## 北极星

用一个真实、非平凡软件子系统证明：

```text
模糊意图
→ Problem
→ Design
→ Engineering
→ Consensus
→ Plan
→ Execution
→ Independent Validation
→ Evidence Closure
```

整个过程比旧管线更早发现关键错误，减少执行阶段返工，并且没有因文档和流程复杂度显著拖慢交付。

## Phase 0 · 冻结范围

- 接受本知识包为研究基线；
- 选定一个 dogfood 项目；
- 冻结“不做清单”；
- 建基线指标；
- 指定 Owner 与工程负责人。

## Phase 1 · 对象与 Schema

- Problem IR；
- Requirement IR；
- Design IR；
- Engineering IR；
- Decision 和 Evidence；
- Reflow 分类；
- 与现有 Concept/Event/Task 的映射。

产出：Schema、示例、状态机、迁移说明。

## Phase 2 · 手动流程

- 使用现有 Investigation 和 Interview；
- 手动产出 Problem、Design、Engineering；
- 人工触发现有 Engineering Consensus；
- 不改 Orchestrator 自动接棒。

目标：验证阶段边界和产物是否真的能被下游消费。

## Phase 3 · 最小验证器

- Problem Evidence；
- Requirement Coverage；
- Design Alternative；
- Design Consistency；
- Engineering Mapping；
- Decision Evidence；
- Consensus Extraction；
- Traceability。

先 warning，收集误报和漏报，再选择承重门 fail-closed。

## Phase 4 · Capsule 接线

- 注入 accepted Design/Engineering 决定；
- 记录上下文来源；
- 运行静态与动态胶囊对照；
- 检查 token、遗漏和行为效果。

## Phase 5 · 自动接棒

- 新事件和状态进入 Orchestrator；
- 每段支持暂停、人工审批和重入；
- 出错能回到正确层级；
- 避免旧项目被强制迁移。

## Phase 6 · 生产试点

- 小流量；
- 完整审计；
- 观察真实返工、质量和成本；
- 与旧管线对照；
- 达到晋升门后冻结 v1。

## Evolution Backlog

- 实时文件/Symbol 语义空间；
- Trace 片段和策略优化；
- 跨项目知识；
- 大型遗留代码迁移；
- 多领域本体；
- 企业级控制台；
- 更强自动治理。

---

<!-- SOURCE: appendices/A-阶段合同与验收模板.md -->

