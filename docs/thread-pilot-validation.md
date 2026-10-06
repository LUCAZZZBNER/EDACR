# 200 个线程候选标注试运行

本轮由用户明确指定 `gpt-5.6-luna`、`max`，范围限于200个线程，后续并发上限改为16个子代理。模型推理由 Codex 子代理执行；下面的 Python 脚本只准备材料和汇总校验，不调用模型网关，也不读取 GitHub token 作为模型凭据。

## 范围与来源

原始数据集为10,727个PR、67,556条评论，归并后有34,822个线程，其中31,783个线程有已验证位置，3,039个暂未定位。

从全部线程以种子20260926均匀、不放回抽150个，再从剩余线程按未定位、多轮讨论、短回复、跨线程引用、多行范围各抽10个。200个线程互不重复，覆盖16个仓库。定向复杂样本不参与随机样本的比例估计。

输入使用SQLite只读连接，包含PR元信息、source/target SHA、原始线程和回复、原始hunk、选中版本文件patch、附近代码及最多4个同文件同revision的相邻线程。原始评论不截断；未提供的仓库语境不能凭模型猜测。

数据集SHA256：`02643c183771086b6f2cc1474dd08dc773864d34c2edfa45bb9550fbc388de28`。
标注口径和输出schema见 [thread-annotation.md](thread-annotation.md)。

## 准备、恢复与汇总

```bash
# 只在新目录首次准备。已有manifest则拒绝覆盖。
python scripts/prepare_thread_pilot.py --output data/annotation/pilot-200-20260926

# 模型子代理读取 assignments/worker-*.json，逐线程写 results/ 同名JSON。
# 只重试缺失或验证失败项，完整结果不重复调用。
# assignments 中30个 worker_id 是逻辑任务分片，不代表同时运行30个代理。
# 本轮用户调整后限制同时运行子代理数 <= 16，遇429进一步降低并发。

# 完全离线重建汇总，不重新调用模型。
python scripts/assemble_thread_annotations.py --run-dir data/annotation/pilot-200-20260926
python -m pytest -q
```

模型失败必须保留为缺失/待重试，不得归为no_issue。程序严格检查输入SHA、thread key、评论引用、candidate/issues关系、分类枚举及位置与输入一致性；不合格输出不会进入候选。

## 本地产物

运行目录：`data/annotation/pilot-200-20260926/`（不提交Git）。

- `manifest.json`：抽样、输入摘要、模型和任务分片。
- `execution.json`：限流、并发上限及重试记录。
- `inputs/`、`results/`：单线程完整输入与最终模型输出，作为断点。
- `thread_assessments.jsonl`：通过结构校验的线程判断。
- `candidate_issues.jsonl`：有验证位置的候选问题，一线程可提炼多个问题。
- `needs_review.jsonl`：上下文不足、未定位候选或失败记录。
- `report.json`：随机组、复杂组分开统计。
- `reviews/`、`initial_results/`：独立模型复核及修改前结果。模型复核不是人工标注。
- `README.md`、`review_table.csv`：本轮最终结果与便于逐条检查的表格。

程序测试覆盖均匀抽样与挑战组不重复、伪造证据ID/行号、输入摘要不匹配、模型枚举输出类型错误、缺失结果不计no_issue以及未定位候选不进入可定位候选集。

本轮没有人工验收。candidate_issue表示候选审查意见，允许功能、安全、性能、可维护性和可读性问题；no_issue只描述这个线程的讨论，不意味着PR或代码没有缺陷。保留Done/Addressed之前仍有效的原始诉求，排除被代码和讨论证伪的意见，将不足以判断的争议标为needs_context。没有生成评测金标准或正负样本标签，没有修改原始 `data/dataset/samples.json`。
