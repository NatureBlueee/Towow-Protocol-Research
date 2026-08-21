# T1-HW-C independent held-out world

状态：`TRUTH_EVALUATOR_FROZEN_NO_CANDIDATE`

这是依据 HW-B 暴露的真实失败重新构造的全新留出世界。它不是 HW-B 实体或事实的改名版：
任务领域、拓扑、动态翻转、受限披露路径、reciprocal 交换和负状态人口均重新构造。

## 隔离边界

候选方法在提交前只可读取：

- `method-visible/README.md`
- `method-visible/submission_schema.json`
- controller 按运行身份单独投递的一个 `delivery-packets/coordinator.json` 或一个
  `delivery-packets/local/*.json`
- 真实执行后由受信 controller、recipient 和外部锚域返回的相应 receipt

候选方法和 root solver 在提交前禁止读取：

- `controller_input.json`
- `delivery-packets/controller-index.json`
- `private/oracle_truth.json`
- `private/scorer.py`
- `private/fixtures/`
- `private/mutations/`
- `tests/`

truth/evaluator owner 可读取全部材料。scorer 只评价冻结提交，不生成、修复或补全候选。

## 运行

```bash
python3 -m unittest discover -s tests -v
python3 private/scorer.py candidate.json
```

测试命令可由 root 运行；为保持真正留出，root 不应打开测试或 private source。

