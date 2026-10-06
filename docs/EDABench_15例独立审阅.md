# EDABench 15 例独立审阅

日期：2026-10-05；批次：20261005_a。**LLM 独立审阅，human_verified=false**。本报告不称作真人专家验收，不给总体正确率，不开展 AACR 方法对照。

实际审阅 15 个 PR、10 个仓库、37 个完整当前线程、83 条导出评论，原始 inline 跨版本材料共 141 条用于核对与版本投票。15 例的采集字段/回复关系、独立 revision 投票、构造 SHA、缓存 baseline、diff 摘要和独立定位均一致。语义对照发现 **2 条应修正的 decision、1 条 no_issue/needs_context 边界分歧**，另有类别依据偏弱、短指代过度具体、条件后果需收敛等问题。

## 抽样与审阅范围

总体是最终 pr_summary.csv 的 10,727 个 PR。固定该文件行序，用 Python random.Random(20261005).sample(rows, 8) 无放回抽取 8 个 PR；再依据结构元数据选 7 个边界 PR，覆盖未定位、多轮/争议、跨线程指代、多行、重命名和两条修复留档。定向组用于找边界，不作总体比例估计。本次和旧 random-10 的 PR 无重叠，且旧 audit 单位是评论，本次单位是 PR。

随机组：8 PR、22 线程、46 评论；定向组：7 PR、15 线程、37 评论。每例读选定 R2 版本的全部导出线程，包括无候选线程；没有只挑 candidate_issue。未审阅所有其他版本的语义，也不把 83 条导出评论称为该 PR 全部历史讨论。范围和抽样冻结见 [sampling_manifest.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/sampling_manifest.json>)、[random_pr_selection.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/random_pr_selection.json>)。

先阅读当前线程、代码、必要邻居形成初判并保存 [independent_judgments.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/independent_judgments.json>)，之后读取原 result/修复留档做比较，见 [review_comparisons.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/review_comparisons.json>)。初判不因后续证据覆盖，对照后的修正独立保存于 [adjudications.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/adjudications.json>)。本次审阅使用同样的文档口径，但执行/判断与原采集、首轮标注独立；这不是独立真人双盲实验。

## 材料、语义和技术事实分开看

| 层次 | 本次证据 | 实际结论 |
|---|---|---|
| 采集/关联 | API 缓存页→raw inline→exported note/author/ID/reply/commit/hunk | 83 条导出评论均匹配；缓存已过滤 cutoff，不能验证后来删除/编辑的历史真值。 |
| 版本/材料 | 原始根线程独立投票，缓存 construction/compare，diff 字节和独立解析 | 15 PR 一致；14 个 R2 不等于最终 head，case-12 恰好相等；未独立恢复全部 Git 历史。 |
| 位置 | 自写 LF unified-diff 解析器，原 hunk 双侧对照 | 30 个 verified、7 个 null 均符合独立验证；null 不代表丢掉候选。 |
| 模型语义 | 完整线程阅读、先行初判、原 summary/reason/证据 ID 比较 | 34/37 初判 decision 相同，3 条不同；2 条建议改 decision，1 条属于边界。相同率不是准确率。 |
| 技术事实 | 静态补丁/完整可用快照/对话确认，分别记录条件 | 命名、重复谓词、clamping 等有静态支持；规范、库兼容、CI/仿真后果部分仍 unknown。 |
| 完整仓库上下文 | 包 inventory 和独立 Git tree 重算 | 仅 case-05/06 的 B/R2 快照存在并验证；13 例不能宣称完成完整源码上下文核验。 |

数据库只读参数、API fetched_at、选例原始实体、完整 diff、定位行文本和原结果摘要均已留存。来源索引：[case_checks.csv（每线程一行）](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/case_checks.csv>)、[material_checks.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/material_checks.json>)、[archive_tree_checks.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/archive_tree_checks.json>)。源码树哈希使用 tar 字节/POSIX 模式和缓存 gitlinks；不展开/运行仓库脚本。

## 15 个 PR 的结果

| Case | PR | 组 | 线程 | 评论 | 变更 LOC | 结论与限制 |
|---|---|---|---:|---:|---:|---|
| [case-01](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-01.md>) | lowRISC/opentitan #8709 | random | 1 | 3 | 1172 | 互连拓扑简化诉求可保留；性能类别缺少直接支持。 |
| [case-02](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-02.md>) | lowRISC/opentitan #27663 | random | 1 | 3 | 155 | 未来 splicing 资源建议已由当前 devbundle 范围解释，no_issue 合理。 |
| [case-03](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-03.md>) | lowRISC/opentitan #9760 | random | 2 | 5 | 138 | 一条 num_ops 清理诉求被错误消解；另一条交易/复位问答的 no_issue 合理。 |
| [case-04](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-04.md>) | lowRISC/opentitan #16168 | random | 2 | 4 | 57 | manual 与 maybe_skip_in_ci 两条构建维护建议可保留；后者无可验证行号。 |
| [case-05](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-05.md>) | chipsalliance/rocket-chip #2038 | random | 4 | 4 | 106 | 两条复位/规范问题维持 needs_context；两条同义 hart/core 命名建议需评测前去重。 |
| [case-06](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-06.md>) | chipsalliance/chisel #1374 | random | 2 | 4 | 87 | 文档迁移与 getOrElse 两条维护诉求均可保留；一条保持 null 行号。 |
| [case-07](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-07.md>) | lowRISC/opentitan #28260 | random | 7 | 17 | 1283 | 7 条完整线程涵盖 task/function 解释、排版和任务拆分；跨文件指代暴露输入上下文遗漏。 |
| [case-08](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-08.md>) | lowRISC/opentitan #25979 | random | 3 | 6 | 55 | 注释、basename 与递归复制三条诉求有对话依据；目录触发的读取失败属于条件性推断，未执行。 |
| [case-09](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-09.md>) | lowRISC/ibex #363 | targeted | 2 | 2 | 107 | 规范引用注释和对齐排版可保留；无功能缺陷外推。 |
| [case-10](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-10.md>) | VUnit/vunit #595 | targeted | 3 | 9 | 212 | 替代转换示例已在邻线程输入内，不能声称缺材料；一条现有候选曾修复输入摘要绑定。 |
| [case-11](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-11.md>) | OpenXiangShan/XiangShan #3104 | targeted | 2 | 11 | 40 | 异常位宽维护建议和重复谓词逻辑问题可保留；后者曾规范化锚点，未改变语义。 |
| [case-12](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-12.md>) | verilog-to-routing/vtr-verilog-to-routing #2568 | targeted | 1 | 3 | 61 | CI 工件条件诉求及作者承认有依据；选定 R2 恰好等于最终 head，系规则结果。 |
| [case-13](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-13.md>) | The-OpenROAD-Project/OpenROAD-flow-scripts #269 | targeted | 3 | 6 | 125 | 最终产物条件保存有明确讨论；一条短问句指代不清，后续修改只能作为补充线索。 |
| [case-14](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-14.md>) | analogdevicesinc/hdl #182 | targeted | 3 | 5 | 433 | 包含重命名和 LEFT 锚点；signed 问题保留 unknown，clamping 丢失有静态支持。 |
| [case-15](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-15.md>) | nickg/nvc #602 | targeted | 1 | 1 | 56 | 缓存 tree_kind 调用的维护建议可保留；没有实测性能结论。 |

上表每个 case 链接均包含 B/R2/最终 head、全体线程/评论 IDs、输入/结果路径和摘要、原理由/候选、先行独立判断、对照后结论、完整当前评论、hunk/代码证据、修复历史和需专家确认项。LOC 为新增+删除行数，不代表最终文件大小。

## 需要修改的两个 decision

### 1. OpenTitan #9760：清理诉求不应因 Updated 被抹掉

根 772593950，原 decision=no_issue。随机化是否失效的疑问得到解释，但作者 772619047 明确表示 num_ops 相关代码不再需要、应移除并已更新。按项目口径，维护/可读性诉求属于 candidate_issue，Done/Updated 不使原有效诉求消失。

建议改为 candidate_issue / maintainability_readability，提炼清理 num_ops 相关旧代码。现有选定补丁不能证明完整继承链没有用途，因此不补写“随机化功能 bug”。完整依据：[case-03](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-03.md>)。

### 2. VUnit #595：输入中实际提供了替代转换实现

根 351495250，原 decision=needs_context；理由声称未提供指向的替代实现/依赖结论。其 input.neighbor_threads 实际含评论 351925777，导入 ieee.fixed_pkg.all，并示例用 from_hex_string/to_integer 实现 base16_decode。该证据原本就在输入中。

建议按“复用已有转换接口，避免维护重复实现”的具体维护诉求保留 candidate_issue。不能声称缺实现；项目 VHDL 版本与库兼容性仍应单列 unknown，不能直接宣称能编译替换。完整依据：[case-10](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/cases/case-10.md>)。

两条均为本次 LLM 基于可追溯文本作出的修正建议，未改写原标签，仍待真人确认。

## 分歧与提炼质量

- **边界：**Rocket-chip #2038 根 305632102 初判 no_issue，原 needs_context。规范记忆不确定、问题尚未澄清，对照后接受保守 needs_context；不计确定错误。完整快照能区分 hrmask 配置与 hrDebugInt 状态，仍缺规范/集成接线。
- **类别依据：**OpenTitan #8709 拓扑简化建议可保留，原 performance 缺明确性能论证；建议归维护/可读性，或补性能证据。不能补写 CDC 故障或性能实测结论。
- **短指代：**ORFS #269 根 772607113 的 this 未指明变量，原 hunk 指到 standalone 0，后续 diff 删 save_checkpoint 但保留 standalone。原 summary 与本次初判均有过度具体风险。建议明确指代待澄清，不能把 Fixed 当技术事实验证，也不能据锚点就断言模型选错变量。
- **条件性后果：**ORFS #269 当前 run_all 在 final_report 前开 save_checkpoint，不能称这个入口必然丢最终产物；OpenTitan #25979 的 readdir/read 子目录问题有明确条件；HDL #182 的 clamping 丢失有静态对比，输入范围/仿真后果未测。
- **同义参考：**Rocket-chip #2038 根 305632253/305632267 都要求 core/hart 命名统一；原线程模型允许分别保留，但评测匹配/分母不能默认是两个独立缺陷。
- **上下文遗漏：**OpenTitan #28260 根 3207246034 指向另一文件的 3207631186。全 PR 阅读可解读，原最近四同文件邻居策略未提供该回复，存在可复现的输入覆盖风险。
- **风格偏离：**OpenTitan #25979 根 2137882113 的 reason/summary 为英文，与批次中文要求不同；这是格式风格问题，技术诉求仍有依据。

这些条目与两条 decision 修正分开计数，互不视作“错误数”的统一分母。

## 修复留档核对

所选 37 个线程中 2 个经过 2026-09-29 修复，均比较当前结果与 original_results：

| 线程 | 修复类型 | 实际变化 | 语义变化 |
|---|---|---|---|
| VUnit #595:351495429 | reviewed_input_rebinding | 只改变 input_sha256，重新绑定当前输入 | decision/reason/summary 均未变 |
| XiangShan #3104:1653861340 | deterministic_anchor_normalization | to_line 829→826，匹配根线程锚点 | decision/reason/summary 均未变；静态论证依然要看 826–829 |

修复 before/after 摘要、timestamp、字段 diff 和旧结果文件均在 case-10/11 中。它们与首轮输出有来源差别，但不构成额外真人验收。本次不重跑历史修复执行脚本。

## 统计口径和有效性

原 37 个线程 decision 为 candidate=26、no_issue=7、needs_context=4；候选意见共 26 条，其中 21 可定位、5 未定位。随机组为 14/6/2（22 线程），定向组为 12/1/2（15 线程）。先行判断有 3 个 decision 差异；对照后的建议为 28 candidate、6 no_issue、3 needs_context，含 2 个修改及 1 个接受原保守判断。数量仅用于描述本批，不推导总体误标率或模型准确率。

83 条原始评论适合保留为有来源的审阅语料；本次没有发现应改采集/版本/行号的选例。模型候选大多符合“整理已有具体诉求”的政策，但多数是维护、排版、文档建议，不能全部称作真实功能缺陷。两条 decision 建议修正、歧义/类别/条件项应补注；needs_context 应继续保留未知。缺源码的 13 例只支持本轮 patch 级核验，不满足完整仓库上下文核验。

尚未开展全量语义复核、真人专家验收、EDA 编译/仿真、被测 reviewer/judge 评测和 AACR 对照。当前成果是独立核查证据及修改建议，原结果保持原样。下一步优先处理代码报告中的来源/摘要防线和本报告的明确修正，然后准备专家核验/上下文补齐。
