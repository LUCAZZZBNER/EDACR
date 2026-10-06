# EDABench 修正与试跑结果

日期：2026-10-06。批次：`next_steps/20261006_c`。

**本轮已把独立核查的建议落实成隔离的代码修复、标签修订层和一次真实模型试跑。现在可以进入人工专家确认与下一轮实验设计。** 当前参考答案仍是暂定的模型整理结果，所有 `human_verified` 均为 false；本轮没有完成正式金标准或模型排名。

## 1. 文件放在哪里

项目根目录为 `D:/Projects/researches/EDACR`。下面路径均相对项目根目录。

| 路径 | 本轮用途 |
|---|---|
| `work/EDABench/` | 可继续开发的独立代码副本；不含原始数据和 GitHub 凭证 |
| `data/edabench_initial_2026-10-05/next_steps/20261006_c/` | 本轮所有脚本、补丁、测试记录、标签和评测证据 |
| 上述批次下的 `label_revision/` | 37 个抽查线程的修订层；包括 inputs、results、manifest、变化表和来源 |
| `human_review/worksheet.json` | 37 个线程的双人复核与裁决填写表，尚未填写真人验收 |
| `human_review/context_addendum.json` | OpenTitan #28260 缺失的跨文件引用评论正文及来源摘要 |
| `pilot/` | 冻结参考集、输入提示、真实输出、语义判断、指标和未匹配意见 |
| `legacy_schema_migration/` | 唯一历史附加字段的迁移副本与来源记录 |
| `implementation.patch` | 可以审阅和应用到其他工作副本的代码补丁 |

原始项目、原始标签和之前四份核查报告保持原样。新报告是后续执行记录，不改变旧报告在当时的结论。

## 2. 代码修复和验证

| 独立核查发现的问题 | 实际修复 |
|---|---|
| Windows 文本换行改变实际文件字节，使返回摘要与落盘摘要不一致 | 输入 JSON 和聚合文件写入统一 LF；回归直接比较真实 UTF-8 文件字节摘要 |
| 聚合程序接受重复任务，可能误报完整 | 队列与聚合共用 manifest 校验，拒绝重复线程、重复输入和扁平结果文件名冲突；全量 complete 时核对声明人口数 |
| 模型结果中的未知字段可能透传伪验收声明 | 结果及 issue 使用封闭字段集合，拒绝 `human_verified`、`tests_executed` 等额外字段；来源记录放在单独文件 |

`tests/test_annotation_assembly.py` 原有一个测试用重复任务承载另一个错误，修正该测试夹具使任务唯一，保留原本验证非法模型枚举的目的。新增 `tests/test_annotation_hardening.py` 8 项回归。

验证结果：

- Windows 新增回归：8 passed。
- WSL Ubuntu 的真实 Linux 全套测试：80 passed，没有跳过或猴子补丁。
- 试跑计分与日志识别规则：11 项通过，覆盖 LEFT/RIGHT、多行边界、null/非法行号、重复意见一对一、最大匹配、固定失败分母、工具调用识别及提示改变后拒绝复用旧输出。

证据：批次内 `windows_regressions.*`、`linux_full_suite.*`、`pilot_rule_tests.*`。本轮没有执行 EDA 项目的编译或硬件仿真。

检查全部 34,822 个历史结果的字段兼容性，发现仅 `7094.json` 带有额外 `input_file`。新副本把该字段移到 `legacy_schema_migration/mapping.json`，语义字段未改，并通过完整任务信息下的单条严格验证。原文件未改；本轮没有重新生成全量聚合数据。以后全量重建必须在新运行目录中采用该迁移映射，不能直接修改旧运行目录。

## 3. 标签修订

37 个抽查线程全部进入新修订层，其中 5 个线程发生变化：

| 线程 | 修订 | 依据和边界 |
|---|---|---|
| OpenTitan #9760:772593950 | `no_issue` → `candidate_issue` | 作者明确承认应清理不再需要的 num_ops；保留维护诉求，不推断随机化功能 bug，行号仍为 null |
| VUnit #595:351495250 | `needs_context` → `candidate_issue` | 邻线程已有 fixed_pkg 等替代接口示例；保留复用维护诉求，库和语言版本兼容性仍待专家确认，行号仍为 null |
| OpenTitan #8709:732083731 | performance → maintainability_readability | 收敛为拓扑简化诉求，没有性能测量或 CDC 故障证据 |
| ORFS #269:772607113 | `candidate_issue` → `needs_context` | 本轮保守暂缓：短问句 this 指代不唯一，不能仅由后续改动断言根评论指向哪个变量 |
| ORFS #269:772607900 | code_defect → maintainability_readability，改写 summary | 保留保存策略诉求；已有 run_all 路径会设置 save_checkpoint，避免“必然丢产物”的绝对化判断 |

前两项对应旧核查报告的两项明确 decision 修正建议；ORFS 的暂缓是本轮新增保守处理，不能混称为旧报告发现的第三项确定错误。

`changes.json` 保留旧值、新值、证据与摘要；`labels.json` 保留技术事实状态和专家问题。全部仍为提议标签。没有把“作者说 Updated/Done”直接当作技术验收证据。

## 4. 真实模型试跑

试跑前冻结 6 个 PR 和 8 个可定位参考问题，选择范围是旧抽查中的定向多样样本，不是代表总体的随机评测集。Rocket-chip 的两条 core/hart 命名意见合并为一个参考问题，并保留两个可选来源锚点；不会因跨线程重复而算两次。未定位及 needs_context 项保留在排除清单和人工表中，没有补造行号。

本轮使用 `gpt-6.1-sol`，reasoning effort 为 medium。6 次 reviewer 调用，1 次独立语义 judge 调用，均通过已登录的本机 Codex CLI 0.160.1 实际运行，无 Mock。reviewer 与 judge 使用相同型号，这是流程试跑，不能称为独立专家裁决。

reviewer 只接收白名单构造的 PR 标题、正文、语言和完整 B→R2 diff。未提供原始审查线程、标签、参考答案、最终修复或后续提交；每次是新的 ephemeral 会话，忽略用户配置，并禁用工具功能。7 次调用的事件日志均未观察到工具调用。CLI 因禁用 code mode host 发出提示，模型仍正常完成；该提示单独记为 warning。首例日志分类器曾将 warning 误记为工具调用，修正后保留原分类记录和原始事件，没有重跑或替换模型意见。

这轮模式为 **NoContext / diff-only**：没有仓库探索，没有恢复新的源码快照，也不能推断 FullContext 效果。CLI 的非交互方式见 [官方文档](https://learn.chatgpt.com/docs/non-interactive-mode)。

冻结计分规则：同文件、同 side、闭区间行号重叠（k=0），再要求语义描述同一问题；最大一对一匹配。LEFT 指 B 中被删除或修改的代码，RIGHT 指 R2；null 不参加行匹配。缺失/失败运行留在 6 PR 的分母里；judge 失败时指标应记为不可用，不伪造零分。

| PR | 模型意见 | 参考问题 | 严格匹配 |
|---|---:|---:|---:|
| Rocket-chip #2038 | 2 | 1 | 0 |
| Chisel #1374 | 1 | 1 | 0 |
| Ibex #363 | 0 | 1 | 0 |
| XiangShan #3104 | 1 | 2 | 1 |
| VTR #2568 | 1 | 1 | 1 |
| HDL #182 | 3 | 2 | 0 |
| 合计 | 8 | 8 | 2 |

完成率：6/6，100%。对暂定参考集的 micro Precision、Recall、F1 均为 25%；macro Precision 33.33%、Recall 25%、F1 27.78%。两项严格匹配分别是 XiangShan 的重复 fault 谓词和 VTR 的上传步骤缺少 always()。

**这些是与不完整暂定参考集的匹配指标，不能解释成模型缺陷准确率，也不能用于发表模型排名。** 参考集维护问题较多，模型输出主要是功能问题，任务政策需要下一轮明确。6 条未匹配意见不是自动判错：例如 Chisel 新意见涉及负向测试不保证抛出异常，需要另行核查；HDL 的 clamping 意见定位到新文件，而参考锚点在被删除的旧文件，当前严格文件/侧规则不会匹配。改变匹配规则必须开新实验，不能看过结果再改本轮分数。

原始意见见 `pilot/reviewer_outputs/*.json`；语义判断见 `pilot/judge_outputs/semantic_judge.json`；逐 PR 指标见 `pilot/metrics.json`；6 条待验证意见见 `pilot/unmatched_findings.json`。每次调用保存完整命令、提示摘要、事件与用量。CLI 报告的 7 次总 input+output token 数为 132,396，包含运行环境提示开销；没有据此估算货币费用。

## 5. 当前能交接什么，下一步需要谁做

本轮自动化执行已到可以等待下一轮科研要求的状态。最先需要的外部工作是让学长或具备对应 EDA 背景的专家确认人工复核表及新增意见，然后明确正式评测政策。详见 [下一轮交接](EDABench_科研继续交接.md)。

不要把本轮提议层直接并入全量 gold，不要用 15 PR 抽查或本轮 6 PR 匹配率估计全量标签准确率。现有包多数 PR 缺少 R2 快照的问题仍在；本轮 diff-only 没有修复整个语料池的源码覆盖。
