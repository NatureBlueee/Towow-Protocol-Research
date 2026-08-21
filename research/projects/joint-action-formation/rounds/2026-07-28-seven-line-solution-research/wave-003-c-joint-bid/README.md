# Wave 003-C：T4 JOINT-BID 盲真值任务

状态：`TASK_TRUTH_V1`

用途：把 T2 已检验的通用责任链迁移到一个全新的三主体联合投标任务，为 G2–G7 提供
blind input、最小披露 controller、独立 oracle、负 mutation、迁移变体和评价契约。

这不是候选方法实现。任务不要求通爻术语、对象或机制；人工 broker、强中心模型、
CMMN/BPMN/DMN、commitment protocol、IAM/policy engine、成熟 workflow，以及其他能满足
同一冻结条件的组合都可以成为正确答案。

## 隔离边界

Solver 初始只允许读取：

- `blind/input.json`
- `evaluator/spec.json`
- `schemas/query-batch.schema.json`
- `schemas/final-submission.schema.json`

Controller-only：

- `controller.py`
- `oracle/truth.json`
- controller state 与 disclosure receipts

Independent-evaluator-only：

- `oracle/truth.json`
- `oracle/migration_variant.json`
- `mutations/negative_mutations.json`
- 冻结后的 candidate bytes

`manifest.json`、测试、validator 和本目录其余文件都不能进入 solver 权限域。分目录不是安全
边界；实际 blind run 必须建立文件白名单。

## 任务结构

三个独立 Agent Entity 需要在五天内形成一份联合投标。它们分别持有局部能力、容量、价格、
风险与 Authority，事前没有完整投标方案。城市采购方是外部目标 Authority，不是第四个联合
投标成员。

任务要求：

1. 从当前 tender version 重建目标、约束、角色、动作、证据与退出；
2. 以最小披露获得能力、容量/价格界、风险 countercondition 与必要 Authority stance；
3. 在 commitment 前对精确跨主体 operation 做有界 probe；
4. 分别管理签署 Authority、预算与稀缺资源 reservation；
5. 区分 submission、receipt/eligibility、Adoption、Acceptance、ActionAttempt、Effect 与
   Settlement；
6. 对 material change、撤销和重复事件做 dependency-scoped reopen；
7. 在 evaluator-only 的异行业迁移变体上检验是否只是硬编码当前主体与字段。

## Controller

```bash
python3 controller.py \
  --input /path/to/query-batch.json \
  --state /controller-only/path/state.json \
  --output /path/to/response.json
```

每轮 query 只允许携带：

`authority_id / request_type / purpose / relation_version_ref / retention_scope`

同一合法 query 的重复请求返回 `REPLAY`，不二次披露。`RUN_INTEROP_PROBE` 与实际 resource
reservation 有冻结前置条件；前置条件未满足时只返回 `DEFER`，不提示答案。Controller 不
求解、不评分，也不解释哪种机制应该被采用。

## 校验

```bash
python3 validate_task.py
python3 -m unittest discover -s tests -v
```

校验只证明结构、hash closure、blind isolation、controller determinism、前置条件和 mutation
闭包；不证明任何候选方法能通过任务，也不替代独立语义评价。

## 证据边界

本任务是全新构造的高保真合成 truth task。它可以检验三主体联合投标中的关系形成、条件创造、
前瞻资格化、Authority/Reservation、目标域 readback 与 scoped reopen；不能证明现实采购、
真实主体接受、法律充分性、商业频率、净价值或长期稳定性。
