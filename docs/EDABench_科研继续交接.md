# EDABench 科研继续交接

日期：2026-10-06。面向接手的 LLM、学长和人工标注者。

**当前代码修复、抽查标签修订和小规模 diff-only 试跑已完成。下一阶段先确认真实参考答案与评测政策，再开展整仓库上下文实验或扩大样本。** 本轮证据可以直接阅读，不必重做已完成的独立结构核查；需要完整原始数据时，再从学长云盘恢复。

## 1. 接手先读这些文件

1. [本轮结果](EDABench_修正与试跑结果.md)：具体改动、测试、模型真实输出和结论边界。
2. [旧核查结论](EDABench_核查结论与下一步.md)：完整语料规模、缺失源码、优先级。
3. [15例独立审阅](EDABench_15例独立审阅.md)：37 个线程的原文、初判及技术 unknown。
4. [AACR方法对照](EDABench_AACR方法对照.md)：不要把当前采集/标签阶段当作完整 AACR benchmark 复现。

工作目录为 `D:/Projects/researches/EDACR`。当前批次根目录：

```text
data/audit/20261006_c/
```

当前开发与 Git 根目录：`D:/Projects/researches/EDACR/`，代码修复已合入并上传 GitHub。2026-10-07 已归并外部独有记录、移除旧 `extracted` 层级，并按要求删除原始压缩包。原始数据后续从学长云盘恢复；来源记录见本地 `data/provenance/layout_20261007/download/source_metadata.json`。旧核查证据位于本批次的 `previous_audits/`，下载、迁移记录位于 `data/provenance/`。这些新增结果不在学长原包和 Git 中，需要单独备份；冻结文件中的历史绝对路径通过 `data/provenance/layout_20261007/path_mapping.json` 对照当前位置。恢复数据避免覆盖修复代码和新增记录。原包中的 GitHub 配置含旧凭证，不要打印、读取用于请求或复制进新项目；如要重新采集，使用另行配置的凭证。

## 2. 已完成，不要重复宣称未做

- 三项代码问题已在独立副本修复：换行/摘要、重复 manifest/完整性、未知字段。
- Linux 全套 80 项通过；Windows 新回归 8 项通过；试跑规则 11 项通过。
- 37 个抽查线程已发布独立标签层，5 个线程修改；原始标签未覆盖。
- 全部 34,822 个历史结果已检查封闭字段兼容性，1 个 `input_file` 附加字段已在独立副本迁移。
- 6 PR/8 参考问题已冻结；真实模型完成 6 次 reviewer 和 1 次 judge，没有 Mock 或工具调用。
- 严格匹配 2/8，micro P/R/F1 为 25%；这是暂定参考集的协议试跑，不是可靠模型排名。

## 3. 下一步一：人工确认参考答案

在批次的 `human_review/worksheet.json` 工作，为 37 个线程填写 `reviewer_a`、`reviewer_b` 和 `adjudication`。这里是空表，LLM 不能替真人填写身份或将 `human_verified` 改为 true。

建议每名专家独立填写如下内容，再对分歧裁决：

```json
{
  "annotator_id": "真实标注者标识",
  "expertise": "相关项目/语言/EDA经历",
  "decision": "candidate_issue / no_issue / needs_context",
  "issues": [],
  "evidence": ["固定版本代码、规范章节或测试记录"],
  "context_requirement": "Diff / File / Repo / ExternalSpec / unresolved",
  "technical_validity": "confirmed / rejected / unresolved",
  "reason": "采纳、排除或暂缓理由",
  "reviewed_at": "实际时间"
}
```

特别核对两项 decision 修订、两项类别收敛、ORFS 短问句的指代，以及 Rocket-chip 复位、VUnit 库兼容、HDL signed/range/clamping 等技术 unknown。OpenTitan #28260:3207246034 的跨文件正文在 `context_addendum.json`，原 packet 只有链接，不能把链接等同于已经提供完整正文。

另核对 `pilot/unmatched_findings.json` 的 6 条新意见。它们是模型新候选，不是已验收的新缺陷。可以使用静态检查或有针对性的编译/仿真验证，但必须保存环境、触发条件与真实日志。确认后在新的 gold 版本中加入或排除，并保留理由，不能回写本轮冻结参考集。

交付物：独立双标记录、分歧裁决、去重 issue ID→所有来源线程/模型意见映射、固定版本证据、明确的上下文需求，以及新的 gold manifest/摘要。未确认项继续标 unresolved；null 不补造行号。

## 4. 下一步二：由科研负责人确定实验政策

需要下一轮要求明确以下事项：

- 研究目标是复现 AACR 全流程、验证 EDA 采集管线，还是比较 EDA reviewer 的上下文能力。
- 只评功能/安全/性能，还是同时评维护/可读性和纯排版；各类别是否分别报告。
- 被测模型、judge 模型、预算和独立验证方式；本轮同型号 judge 不能替代专家。
- Diff、File、Repo 输入模式；文件迁移、LEFT 与 RIGHT 的等价位置、null 和容差如何处理。
- 冻结的随机/分层抽样规模、项目分布及时间划分，避免沿用定向抽查作为总体统计。

如果尚无新增要求，优先开展上一节人工确认，不自行跑全量昂贵模型标注或更改研究方向。

## 5. 下一步三：若要求整仓库上下文实验

先从包内同时有 B/R2 的 808 PR 中选择，并逐样本核验文件树；旧核查只独立验证了 case-05/06 的四棵树，808 是存在数量，不是全部可运行的数量。不要拿当前 head 或最终修复版本代替 R2。

为 reviewer 建独立输入根目录，只提供固定 B/R2 代码和允许的元数据；去掉 `.git`、历史评论、标签、gold 和未来版本，并实际验证访问范围。查子模块、外部依赖和工程运行条件，保存无法恢复/无法运行清单。先做同一批 PR 的 NoContext 与 FullContext 对照，再扩大规模。

本轮没有完成这些源码恢复、依赖部署、编译或仿真工作，也没有完成官方 AACR 中独立模型补充问题与专家验收流程。

## 6. 脚本与重放

批次脚本全部从各自所在路径定位数据。

| 脚本 | 用途与重放注意 |
|---|---|
| `run_regression_tests.py` | Windows `--native` 只跑新回归；真实 Linux 默认跑全套 |
| `build_revision_layer.py` | 生成本轮抽查标签层；以后改标签应另开批次，保留本轮记录 |
| `prepare_pilot.py` | 冻结六例参考和输入；已冻结时拒绝覆盖 |
| `run_pilot.py` | 真实 CLI 推理；相同提示/Schema 已有输出时跳过，发生变化时拒绝复用 |
| `evaluate_pilot.py` | 校验 reviewer 输出、真实语义 judge 和计分；`--report-only` 不调用模型 |
| `test_pilot_metrics.py` | 一对一、LEFT/null/多行、失败分母、日志识别规则 |
| `check_schema_migration.py` | 历史结果封闭字段兼容性检查，不是全量语义验收 |
| `migrate_legacy_result.py` | 唯一历史来源字段移到单独记录，不修改原始文件 |
| `finalize_evidence.py` | 导出代码补丁、原文件保留检查和人工上下文补充 |

新的科研实验应复制相应脚本并使用新的批次目录、manifest 和提示版本，保留所有固定分母里的失败。严禁没有可用模型时静默使用 Mock，也不能把未匹配模型意见直接算作不存在的缺陷。

## 7. 可以等待下一轮要求的状态

自动化修复和小样本流程已可审阅、可重放；下一阶段需要人工专家与科研负责人给出金标准确认和实验政策。本轮没有完成全量语义校验、正式 gold、完整仓库评测或论文结论。接手者应从这些明确缺口继续，不必重新解释数据目录或重新完成此前 A—E 核查。
