# EDABench 独立核查结论与下一步

日期：2026-10-06（Asia/Shanghai）。本报告完成交接阶段 E，综合 20261005_a 的 A/B/C 核查和 20261006_b 的 D 方法对照。全部独立阅读/判断由 LLM 执行，`human_verified=false`；没有真人专家验收。原始代码、采集数据、原标签和旧报告保持原样。

**这份初步项目值得保留，当前可信成果是原始审查语料、可追溯的版本/diff 关联和 LLM 候选整理。它还不能直接作为已经验收、能给 reviewer 排名的完整 EDABench 金标准。** 最影响可信度的工作，是建立独立金标准、补齐所需代码上下文、去重，并明确评测输入和计分边界。

## 已实际完成的核查与证据边界

| 核查层次 | 实际证据 | 能支持的结论 |
|---|---|---|
| 代码正确性 | 原套件在真实 Linux /tmp 环境 72 passed、0 failed；Windows 52 passed、20 failed，并作换行/权限诊断；三个隔离复现。见 [代码报告][code-report]。 | 支持已检查规则；发现 Windows 输入哈希问题、重复 manifest 假完整状态、额外字段伪验收透传。原数据中未观察到这三种触发造成的现存错误。 |
| 全量结构 | 34,822 个唯一输入/结果的哈希、PR/SHA、原评论、锚点和来源检查；10,727 个 PR 隔离重建，仅归一修复来源相对路径后语义一致。见 [结构检查][full-check]、[聚合比对][aggregate-check]。 | 结构一致性有全量证据；不证明全部理由、类别和缺陷技术事实正确。 |
| 15 PR 的材料 | 10 仓库、37 个完整选定版本线程、83 条导出评论；跨版本 141 条 inline 用于采集/版本核对。见 [15例报告][case-report]。 | 这批采集/回复、版本和 diff 一致；30 个可定位根和 7 个 null 根符合独立核对。没有发现需改采集/版本/位置的选例。 |
| 15 PR 的语义 | 先保存独立初判，再比原标签；2 条明确 decision 修正建议、1 条边界分歧，另有提炼和上下文问题。 | 只支持这 37 个线程的具体结论。8 随机 PR＋7 定向 PR 是混合设计，34/37 初判一致不能视作总体准确率。 |
| AACR 方法 | 阅读论文相关方法/提示、核对固定官方源码和实际数据；22 项对照。见 [方法报告][method-report]。 | 明确部分对应、自定义差异、未实现和证据不足；官方代码存在不能证明本项目已评测。 |
| 全量源码材料 | 对完整压缩包 inventory 与所有 10,727 PR 的 B/R2 路径作 join。见 [逐 PR 覆盖表][archive-coverage]。 | 808 PR 双快照、229 仅 B、176 仅 R2、9,514 均无。该统计是存在性，不能证明 808 全部树正确或依赖可运行。 |

本次 D/E 未重复运行已完成的原套件，也未重新采集、全量标注或编译/仿真。前批经过核对的 70,328 个提取成员摘要与来源一致；本批公开验证了参考 PDF/固定代码的字节身份。原采集 `complete=false` 仍成立，API 缓存也不代表截止时刻完整的事务历史。

## 哪些材料可以继续用

### 1. 保留为有来源的原始审查语料

总体 10,727 PR、34,822 线程、67,556 评论可以继续作为候选筛选和标注的来源池。保留原始正文、root/reply、B/R2、diff 摘要、锚点状态、采集失败和修复来源；不能因有 Done/感谢就删除原对话，也不能把原评论全部转换成 benchmark 参考答案。

本次 15 PR 的 83 条导出评论与保存 API 记录匹配，适合保留；这项材料结论不受两条 LLM decision 需修正影响。完整名单和逐线程证据见 [case_checks.csv][case-checks]、[15例报告][case-report]。没有核验后来编辑/删除的 GitHub 历史真值，也没有逐例实时重新抓取。

### 2. 采集、版本、位置需要修正的材料

15 例未发现需要改写采集正文、线程关系、R2 或锚点的错误。7 个 null 根是可靠性不足时的正确保留，应继续为 null；不能补造行号。历史修复留档中的 VUnit #595:351495429 仅重新绑定 input_sha256，XiangShan #3104:1653861340 将锚点终行 829→826；两者没有改变 decision/reason/summary。

全量有 2,015 条未定位候选 issue，应进入待补证据集合，不能混入行号匹配；这一数量不同于原始 6,617 条有 null 端点的评论。基线/历史无法恢复、构造失败的项目应按既有失败记录隔离，不能用当前 head 替换后声称恢复了 R2。对已导出的总体没有作全量独立语义/历史验收。

### 3. 可保留为候选、仍待真人专家确认的意见

当前 26,512 个候选 issue 中，24,497 可定位、2,015 未定位；类别为维护/可读性 20,415、code defect 5,319、performance 493、security 285。数量是模型候选规模，不能表述为 26,512 个已确认缺陷。维护/可读性约占 77.00%，应与功能、性能、安全结论分别汇报。

15 例中有依据的候选包括 OpenTitan #16168 的构建规则维护、Chisel #1374 的文档/接口建议、XiangShan #3104 的重复谓词和位宽建议、VTR #2568 的 CI 条件、HDL #182 的 clamping 静态差异、NVC #602 的重复调用整理。它们适合进入专家标注池；具体仿真触发、规范约束和项目依赖有些仍 unknown。逐例适用范围见 [15例报告][case-report]，不能将整 PR 标为技术验收通过。

### 4. 应修正或补背景的 LLM 意见

以下都为 LLM 独立审阅建议，未覆盖原标签，待真人确认。每项证据可从 [原逐例报告][case-report] 和对应 case 文件追溯。

| 线程 / case | 建议处理 | 保留的技术边界 |
|---|---|---|
| OpenTitan #9760:772593950 / [case-03][C03] | 原 no_issue→candidate_issue / maintainability_readability；作者明确表示 num_ops 旧代码应清理并已 Updated。 | 不补写随机化功能 bug；未证明所有继承调用都无用途。 |
| VUnit #595:351495250 / [case-10][C10] | 原 needs_context→保留“复用已有转换接口”的维护候选；不能再声称替代实现没提供。邻线程 351925777 已有 ieee.fixed_pkg/from_hex_string/to_integer 示例。 | VHDL 版本/库兼容性仍待确认，不能宣称可直接编译替换。 |
| Rocket-chip #2038:305632102 / [case-05][C05] | 初判 no_issue 与原 needs_context 有边界分歧；对照后维持保守 needs_context，不计确定错误。 | 复位/规范和接线未澄清；另一个复位问题也需上下文。 |
| OpenTitan #8709:732083731 / [case-01][C01] | 拓扑简化候选保留；performance 类别需改为维护，或补具体性能证据。 | 未测性能，不推导 CDC 等新故障。 |
| ORFS #269:772607113 / [case-13][C13] | 短问句 this 指代待澄清，收敛过度具体 summary。 | 原 hunk 指 standalone，后续删除 save_checkpoint 只能作线索，不能断言错变量。 |
| ORFS #269:772607900 / [case-13][C13] | 产物保存条件诉求可保留，改写绝对化后果。 | run_all 在 final_report 前会设置 save_checkpoint，不能称该入口必然丢产物。 |
| Rocket-chip #2038:305632253/305632267 / [case-05][C05] | 合并为一个 core/hart 命名问题，保留两个来源线程。 | 这是评测前语义去重，不删原始讨论。 |
| OpenTitan #28260:3207246034 / [case-07][C07] | 补入明确指向另一文件的 3207631186，再重新判断上下文充分性。 | 最近四同文件邻居遗漏是输入覆盖风险；完整 PR 本次读到了，不证明首轮 worker 也看到了。 |

另有 OpenTitan #25979 的条件性目录读取后果与英文输出风格，HDL #182 的 signed/input range 等 unknown，应按原逐例记录处理。纯风格问题与功能事实问题不能统一计入一个“错误率”。

### 5. 暂不能宣称完成完整仓库上下文评测的案例

本次查的是完整包内全部归档记录，覆盖结果为：

| 包内 B/R2 快照 | PR 数 | 当前用途与缺口 |
|---|---:|---|
| 两者都有 | 808 | 可优先作为恢复/验证池；本次仅前批 case-05/06 的四棵树得到独立哈希验证，未全量验树/依赖。 |
| 只有 B | 229 | 缺审查目标源码，需要恢复 R2。 |
| 只有 R2 | 176 | 可检查部分目标上下文；若需重建/核验 B→R2 diff 或旧侧上下文，还需 B。 |
| 两者都无 | 9,514 | 当前包提供 diff/评论/版本记录；整仓评测先恢复固定 SHA 文件树。 |

合计 9,919 PR 未同时保存两份快照，9,743 PR 未保存 R2 快照。**缺包内归档不等于 SHA 永久不可恢复**，也不说明原 diff 必然错误；项目本来会在构造后释放部分临时源码。需要逐评测 PR 检查 GitHub 历史可取性、完整树、子模块/依赖和环境。

15 例中仅 case-05/06 有 B/R2 快照且已独立核树，其余 13 例只能声称完成本次 diff/讨论范围的核查。完整 PR 列表及 SHA 见 [逐 PR 覆盖表][archive-coverage]；不能把13/15比例外推，本文总体数量来自全量 inventory join。

## 最影响可信度的处理优先级

P0 指最终 benchmark 可信度的前置条件，P1 指下一轮标注/接入前应修的实现问题，P2 指扩大规模与完整论文对照。下面是可检查的工作项，本次没有替用户执行真人标注、标签覆盖或模型评测。

| 优先级 | 工作 | 完成时应拿到的证据 |
|---|---|---|
| P0 | 建立专家确认的独立 gold 层。先用这 15 PR/37 线程作校准，处理两条 decision、歧义和技术 unknown；明确维护/纯风格政策，随后对最终评测候选作独立双标和争议裁决。 | 每 issue 的来源、专家资格/标注记录、独立判断、采纳/排除原因、冲突裁决与上下文证据；所有 unresolved 保持待定。 |
| P0 | 在 PR 级去重、补跨文件引用、标注 Diff/File/Repo 需求；冻结参考集并保留候选与 gold 的独立版本。 | 去重 issue_id→全部来源线程映射、上下文需求与理由、gold manifest/hash；不能拿分类完成状态代替。 |
| P0 | 给拟评测 PR 恢复 B/R2 并隔离 reviewer 视野：只提供允许代码与 PR 元数据，原讨论/gold/最终修复不在模型可访问路径。 | 文件树/版本摘要、依赖与失败清单、实际访问日志；不能以 checkout R2 证明 future refs 不可读。 |
| P1 | 修 CODE-01 Windows 字节摘要，CODE-02 assemble 重复任务完整性，CODE-03 未知字段/伪验收透传。 | 三个原隔离复现不再触发；适用平台原套件通过；不覆盖旧运行来源。最小建议及复现见 [代码报告][code-report]。 |
| P1 | 为 EDA 写 gold 接入适配：PR 编号＋完整 SHA 的唯一 ID、LEFT/multi-line/null 政策、保留 title/body/category/context/provenance。 | 三组 ID 冲突不再产生重复；真实 LEFT/null/多行测试匹配符合冻结规则；未定位不记行准确率。见 [方法 D16–20][method-report]。 |
| P1 | 冻结 reviewer/judge 与指标政策。禁止真实评测静默 Mock；明确行重叠 k=0/容差模式，补 hunk 语义判断；规定失败/超时、重复匹配、未匹配新真问题处理。 | 精确模型/提示/参数/工具版本；固定 PR 分母、完成率、micro/macro Precision/Recall/F1、raw findings/judge 判定。当前包未有这些分数。 |
| P2 | 扩大 EDA 分层集，降低单仓库 57.36% 权重；按 RTL/工具/验证、尺寸、仓库和时间报告覆盖。若目标是完整 AACR 流程，再补独立多模型新问题生成和验证。 | 冻结抽样规则、PR 与 issue 数量、来源模型/框架、去重和专家确认记录；新增模型意见与原线程整理分开。 |

具体的官方移植风险还包括：converter 将非空原评论全当参考；三个生成适配器 side 固定为 right；null 可能跳过行约束记匹配；缺 reviewer 结果不进入指标分母；固定 schema 丢 PR title/body 等字段。静态推演及真实冲突证据见 [方法报告][method-report]、[八项静态核对][static-traces]，不是已发生的 EDA 得分异常。

## 当前能够给出的结论

结构完整、语义合理、专家确认、可评测应分别记录。现在全量结构有证据，有限样本的语义有独立 LLM 审阅，专家确认未完成，完整仓库评测未执行。AACR 对照已完成，结果支持“部分环节对应＋明确自定义规则＋后续核心阶段缺失”的表述。

本轮交接 A–E 核查和报告已完成。尚未完成的是项目下一阶段本身：全量语义复核、真人专家标注、EDA 编译/仿真、独立新问题生成、代码/标签修正和 reviewer benchmark 运行。当前建议先形成可验证的少量 gold 与评测闭环，再扩大量；不应直接以大规模候选数量作为论文中的真实缺陷数或评测成绩。

证据分别保存在 [A/B/C 批次][prior-root]、[D/E 批次 README][current-readme]。四份报告共同覆盖此次任务；前两份日期和“当时未开展 AACR”的范围说明作为历史记录保留，本报告补齐后续范围。

[code-report]: <D:/Projects/researches/EDACR/docs/EDABench_代码核查报告.md>
[case-report]: <D:/Projects/researches/EDACR/docs/EDABench_15例独立审阅.md>
[method-report]: <D:/Projects/researches/EDACR/docs/EDABench_AACR方法对照.md>
[full-check]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/full_annotation_checks.json>
[aggregate-check]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/aggregation_semantic_comparison.json>
[case-checks]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/case_checks.csv>
[archive-coverage]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/evidence/package_archive_coverage.json>
[static-traces]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference_adapter_static_traces.json>
[prior-root]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/README.md>
[current-readme]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/README.md>
[C01]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-01.md>
[C03]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-03.md>
[C05]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-05.md>
[C07]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-07.md>
[C10]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-10.md>
[C13]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-13.md>
