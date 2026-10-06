# 全量线程 LLM 候选标注

用户在200线程试运行完成后授权处理全部34,822个已导出线程，继续使用 `gpt-5.6-luna` / `max`，取消16个并行子代理限制。当前工具环境最多提供32个子代理并发槽位；限流时允许降低实际并发，失败记录保持待重试。

运行目录为 `data/annotation/full-20260926/`。原始采集SQLite、samples.json、GitHub凭据和200线程试运行目录均不修改。

## 处理规则

遵循 [thread-annotation.md](thread-annotation.md) 的语义规则和结果schema。全量分类不增加LLM发现新问题的阶段，也不生成已确认缺陷或人工金标准。完整线程是最小判定单位；Done/Addressed不抹掉有效改进意见，质疑被代码和讨论证伪时不保留，证据不足时输出needs_context。

试运行结果仅在输入摘要和线程标识完全一致、结果结构校验通过时复用，包含已完成的模型复核修正。所有复用条目记录原始位置，不能仅凭线程ID认定输入相同。

全量输入按PR缓存原始材料，避免同一PR的每个线程重复读取完整diff。保存可验证的完整输入，任何失败不得静默少计总体任务。

## 任务领取与中断恢复

```bash
python scripts/prepare_thread_pilot.py --all --reuse-pilot data/annotation/pilot-200-20260926 --output data/annotation/full-20260926
python scripts/annotation_queue.py init --run-dir data/annotation/full-20260926
# 输入持续生成时，用增量导入只追加新任务，保留现有领取状态。
python scripts/annotation_queue.py init --incremental --run-dir data/annotation/full-20260926
python scripts/annotation_queue.py status --run-dir data/annotation/full-20260926
python scripts/assemble_thread_annotations.py --run-dir data/annotation/full-20260926
```

模型推理由子代理执行，不通过GitHub token或Python脚本直调模型网关。

模型worker从运行目录的独立SQLite队列领取线程，读完整当前线程和必要代码上下文，逐线程输出JSON并提交状态。不同worker不能同时领取同一任务。后续继续领取pending记录，不重新处理已完成条目。

worker中断后父代理释放其尚未完成任务；API限流和结构失败有单独状态及重试次数，不能用no_issue填补。过期租约只在显式恢复时重新派发，避免仍在推理的worker与新worker重复写结果。

最终统一验证所有行号、评论引用和输入摘要。该验证不等于语义正确性核验；最终人工验收状态继续为false。全量统计使用full分组，与此前150个随机/50个复杂试运行分组分开。

### 全量生成流水线（2026-09-26 调整）

按用户要求，生成期间不再逐条验证或模型复核，全部线程生成完后统一验证。每个子代理一次处理一个线程，写完立即提交并领取下一个，不等待其他子代理。模型仍为 `gpt-5.6-luna` / `max`。

```bash
python scripts/annotation_queue.py defer-validation --run-dir data/annotation/full-20260926
# 首次领取；返回一个任务。
python scripts/annotation_queue.py advance --run-dir data/annotation/full-20260926 --worker full01
# 原子写出结果后，提交当前任务并领取下一条。
python scripts/annotation_queue.py advance --run-dir data/annotation/full-20260926 --worker full01 --input-file inputs/0001.json
```

运行目录中的 `validation-deferred` 标记使领取、提交和恢复不再读取或校验输入/结果内容，只确认结果文件存在并保存队列进度。此模式下 `complete` 表示已产出，`unvalidated_output_count` 表示待统一验证数量；分类计数暂时只包含此前已验证的结果，不能用于推算全量分类比例。缺失的结果仍记录失败，不能算作已产出。已有结果保留，不因切换模式重做。

全部输入准备完成、所有任务产出后再运行 `assemble_thread_annotations.py`，统一检查摘要、引用、位置与结果结构。最终 `report.json` 的 `classification_complete` 仅在所有结果通过时为 true；有问题的条目列入 `needs_review.jsonl`，届时再集中修正。

## 验证与产物

新增测试覆盖全量任务分组、输入复用与恢复、队列互斥领取、过期恢复、输出验证和完整任务数。只有所有任务都有有效结果后，才能报告模型分类完成；pending、running和failed都必须保留明确数量。

运行目录保留完整manifest、queue.sqlite3、execution.json、逐线程inputs/results，以及离线汇总的thread_assessments.jsonl、candidate_issues.jsonl、needs_review.jsonl和report.json。不同状态分别报告，不把模型候选数量称为人工确认的适用数量。
