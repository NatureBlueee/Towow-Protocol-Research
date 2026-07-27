# 历史设计能力恢复与研究审计

本目录回答一个有限问题：

> 历史上每套独立设计依靠什么具体决定解决了什么问题；经过 v0.4、v0.7、v1.1
> 三次整合后，这项能力被保留、转换、削弱、丢失、重复维护，还是尚未检验？

它不是新的统一理论，也不替代原始材料。

## 审计原则

1. 原始或最接近当轮的材料优先；后续长文只用于解释后续映射。
2. 名称相同不等于能力保留；必须重建正例、移除关键决定后的失败，以及当前行为。
3. `PRESERVED` 只用于差异、失败检测和行为影响三者均可人工重建的能力。
4. 用户纠正、证据驱动变化、实现修复和研究者后续综合分开记录。
5. v1.2 完整包保持不可变；本目录只保存派生审计判断。

## 入口

- [稳定来源注册](source_registry.csv)
- [能力保真矩阵](ledgers/capability_preservation_matrix.csv)
- [主张账本](ledgers/claim_ledger.csv)
- [证据账本](ledgers/evidence_ledger.csv)
- [设计决策时间线](ledgers/decision_timeline.csv)
- [当前组件—历史能力索引](ledgers/component_capability_index.csv)
- [正式事实唯一 owner](ledgers/formal_fact_ownership.csv)
- [当前系统能力图](current_system_capability_map.md)
- [审计发现与能力损失](AUDIT_FINDINGS.md)
- [审计后的研究排序](research_priority_after_audit.md)

## 七条原生研究线

1. [发现与边界](native_lines/01_discovery_and_boundary.md)
2. [问题与关系构成](native_lines/02_problem_and_relation_constitution.md)
3. [可能性形成](native_lines/03_possibility_formation.md)
4. [能力兑现](native_lines/04_capability_realization.md)
5. [权威与规范](native_lines/05_authority_and_norms.md)
6. [现实效力](native_lines/06_reality_effect.md)
7. [运行与演化](native_lines/07_runtime_and_evolution.md)

## 定位语法

`source_registry.csv` 为每个来源保存：

- 原包目录中的物理路径，或 `ZIP 路径::成员路径`；
- 原包目录或 ZIP 目录中的稳定记录 ID；
- SHA-256；
- 可读派生副本；
- 本次审计实际使用的行号范围；
- 来源在判断中的角色。

ZIP 内文本的可读副本按内容 SHA-256 命名。它只方便定位；权威位置仍是
`authoritative_locator` 所列 ZIP 成员。

## 自动检查

```bash
make research-audit-check
python3 tools/query_a2a_audit.py --capability CAP-EFF-001
python3 tools/query_a2a_audit.py --source SRC-R52-EFFECT
python3 tools/query_a2a_audit.py --component CMP-BOUNDARY
python3 tools/query_a2a_audit.py --claim CLM-015
python3 tools/query_a2a_audit.py --text "countercondition"
```

检查范围包括：

- 来源记录、文件散列、ZIP 成员散列与行号有效性；
- CSV 枚举、悬空引用和重复 ID；
- 每项能力的正例、移除失败与当前承担者；
- `PRESERVED` 的人工重建标记；
- 七条原生研究线与当前系统图的双向能力引用；
- R5、R5.2、R5.4、R5C 是否回到原始证据；
- 决策时间线是否区分用户改域、证据变化、预先决定和实现修复。
