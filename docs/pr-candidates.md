# PR 级候选集与分布统计

在已完成校验的全量线程标注上进行确定性聚合。脚本不调用模型或网络，不改变
原始数据及线程判断，不进行筛选、抽样、语义去重或人工验收。

```bash
python scripts/build_pr_candidates.py \
  --data data \
  --run-dir data/annotation/full-20260926 \
  --output data/pr-candidates/full-20260926
```

同一输入和输出路径重复运行，五份输出文件字节一致。每个文件原子替换，manifest
最后写入并记录输出摘要；读取一组产物时应核对 manifest，避免混用中断前后的文件。

## 文件与结构

- `pr_candidates.jsonl`：每行一个 `(repository, number, source_commit, target_commit)`。
  覆盖全部已导出 PR，**包括候选意见数为零的 PR**。`pr_key` 包含上述四部分；
  `threads` 保留全部 decision、reason、原始 thread key、根评论 ID、导出评论 ID、
  输入摘要、证据引用和定位状态。每条意见保留原摘要与候选类别，并增加
  `issue_id=<thread_key>/issue/<从1开始的序号>`，不合并文本相同的意见。
- `pr_summary.csv`：相同 PR 总体的轻量索引，含 PR 链接、两个 SHA、选定版本的
  LOC/文件数/hunk 数、线程数、候选与可定位意见数量，适合排序和后续脚本读取。
- `statistics.json`：完整机器可读统计，包括仓库、仓库主语言、文件后缀、候选类别、
  LOC 分组、每 PR 意见数精确直方图和分桶，以及均值、中位数、最小值、最大值。
- `report.md`：上述统计的可读表格。
- `manifest.json`：原始语料、线程标注、已有候选汇总及修复记录的输入摘要，脚本摘要，
  输出摘要和相对路径。保留原始采集的 `source_collection_complete` 状态。

`diff_path` 相对于 manifest 的 `data_root`；线程 `provenance.input_file`
相对于 `annotation_run`，可据此读取完整线程输入，包括回复及相邻证据。
聚合文件保留导出评论 ID，未复制原始评论全文。`annotation_repair` 引用上一轮
具体修复记录，避免将本次会话修正的结果全部归因于首轮生成模型。

## 统计口径

- `candidate_issue_count` 包含已定位和未定位意见；
  `located_candidate_issue_count` 只计 `location_status=verified` 的意见。
  该 verified 指位置验证，不是语义或人工确认。
- 仓库、仓库主语言和 LOC 分布以全部导出 PR 为总体，同时列出有候选 PR 和有
  可定位候选 PR 的数量。零候选 PR 不视为无缺陷负例。
- LOC 是选定 source→target 的 additions+deletions，不使用最终合并版本统计。
  分桶为 `0`、`1–50`、`51–200`、`201–500`、`501–1000`、`1001+`。
- 文件类型取候选意见 `path` 的最后一个后缀并小写；如 `.SV` 计为 `.sv`，
  `.sv.tpl` 计为 `.tpl`，无后缀单独计数。不将仓库主语言当成评论所在文件语言，
  不把后缀解释为 RTL、验证或其他业务分类。
- 文件后缀和候选类别分布统计意见数量及涉及的唯一 PR 数。同一个 PR 可以涉及
  多个后缀/类别，因此这些分组的 PR 数不能相加；意见数可以相加。
- 每 PR 意见数分别给出全部候选与可定位候选两种口径，均包含零值。
  分桶为 `0`、`1`、`2–5`、`6–10`、`11–20`、`21+`，另保留精确计数。

## 完整性检查

构建前要求标注 `classification_complete=true`，校验原始语料摘要与采集、标注
manifest 一致。拒绝重复 PR revision、重复/缺失/多余线程、输入标识不一致和位置
不一致；核对汇总数量，并逐条、多重集比较重建出的可定位意见与原候选汇总，
包含 PR URL 和两个 SHA，防止跨版本关联。发布前再次检查来源文件摘要。

测试覆盖零候选 PR、多意见线程、未定位证据、跨文件类型的统计分母、来源摘要
不匹配、跨版本/内容错配、缺失/重复关联和重复生成字节稳定。

## 2026-10-02 生成结果

10,727 个 PR、34,822 个线程、67,556 条原始评论；8,680 个 PR 有候选意见，
8,594 个 PR 有可定位候选意见。总计 26,512 条候选，其中 24,497 条可定位、
2,015 条未定位。原始采集仍为 complete=false；本次完整性仅针对已导出总体。

具体分布以本地生成的 `data/pr-candidates/full-20260926/report.md` 为准。
