# EDABench 代码核查报告

日期：2026-10-05；批次：20261005_a。按用户授权完成交接阶段 A/B/C，AACR 方法对照暂不开展。审阅执行者为 LLM，human_verified=false。

本次离线核查支持现有数据链路的结构一致性：34,822 个输入/结果均通过现有结构规则和新增的 dataset→input 对应检查，隔离重建的 10,727 个 PR 聚合记录在消除修复记录相对路径变化后语义一致。发现 1 个 Windows 输入哈希缺陷、2 个验证防线缺口；没有在原全量产物中观察到这三种触发造成的现存数据错误。代码核查不能证明全部候选意见技术上成立。

## 范围、材料与保护

阅读项目 AGENTS、README、method、thread-annotation、thread-full-run、pr-candidates 文档，以及 inputs/storage/github/collect/revisions/material/build/CLI、prepare/assemble/queue/PR 聚合与对应测试。未修改这些来源代码、原始 samples、原标注、原 PR 汇总、旧 audit 或既有用户文档。

完整 inventory 驱动一次安全顺序解包，新增材料目录 [audit_material_20261005](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/audit_material_20261005/EDABench/data>)；取出 70,329 个所需文件约 38.35 GiB，含 40,102,420,480 字节数据库、零字节 WAL、32,768 字节 SHM、全量输入/结果、修复留档及选例 diff/快照。逐成员字节摘要、空间检查、缺失项和过程见 [extraction_evidence.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/extraction_evidence.json>)；missing=[]。因 Windows 长路径限制使用较短独立目录。跳过凭据配置、归档脚本和不安全成员，不执行源码归档内容。

核查结束后重新计算 70,328 个提取成员的 SHA-256，合计 41,177,797,895 字节（含数据库主文件），全部与提取时摘要一致；仅排除 SQLite SHM 运行辅助结构。原 samples/pr_summary 也与本批开始时摘要一致，见 [integrity_checks.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/integrity_checks.json>)。

SQLite 用 mode=ro、PRAGMA query_only=ON，未用 immutable 绕过日志，未运行原 Store 初始化器。缓存响应 270,015 条；tasks 中 complete=28,702、failed=2,939。采集截止 2026-09-21T15:21:52.199716Z；响应 fetched_at 范围 2026-09-21 至 09-24；现有 dataset complete=false。这是已保存采集状态，不表示全量采集已完成或实时 GitHub 状态。依据：[database_readonly_checks.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/database_readonly_checks.json>)。

## 关键规则实际审查

| 环节 | 实现位置 | 检查结果与边界 |
|---|---|---|
| 仓库输入与去重 | [edabench/inputs.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/inputs.py:8>)、[edabench/collect.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/collect.py:32>) | 按 full_name 列读取所有 sheet，大小写无关去重，保存原表摘要；空表/非法仓库名拒绝。原测试覆盖输入读取。未新增 star/语言筛选。 |
| closed PR/截止 | [edabench/collect.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/collect.py:87>) | created/closed_at 均不晚于 cutoff，包含未合并 closed PR；评论 created_at 截止。过滤不能恢复截止时刻的被编辑/删除内容。 |
| REST/GraphQL 分页与失败 | [edabench/github.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/github.py:63>)、[edabench/github.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/github.py:152>)、[edabench/collect.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/collect.py:109>) | REST 跟随 next；GraphQL 分别翻 reviewThreads 和每线程 comments；认证、限流、错误及 guarded 状态有处理。原套件含模拟分页/限流测试；15 例 raw inline 与逐页缓存完整对照。 |
| 数量上限 | [edabench/collect.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/collect.py:154>)、[edabench/material.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/material.py:33>) | commits ≥250 或数量不等触发历史恢复；PR files <3000 才标完整；compare ≥300 文件拒绝直接当完整 diff，转已验证归档。上限是实现保守规则，本轮未联网重新测 API。 |
| 根线程、循环与 bot | [edabench/revisions.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/revisions.py:25>)、[edabench/revisions.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/revisions.py:30>) | 回复追根、缺根/循环留失败，按 root.original_commit_id 归版本；仅 type=Bot/login 后缀 [bot] 排除。未知身份保留，不能断言 GitHub 评论没有 AI 辅助。 |
| R2 投票 | [edabench/revisions.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/revisions.py:30>) | 每个含非明确机器人的独立根线程一票，最多票→最早根时间→SHA；不是回复数投票。独立重算所选 15 PR 全部匹配，14 例 R2 与最终 head 不同，1 例恰好相同。 |
| 基线/force-push | [edabench/collect.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/collect.py:109>)、[edabench/material.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/material.py:259>) | 保存 ref 事件、候选 base、merge-base 与原始 hunk 一致性；15 例 source 都与缓存 compare.merge_base 一致。没有完整 Git 历史去独立重算全部 merge-base；不能证明未公开/已删除历史。 |
| 完整 patch/rename/binary/树 | [edabench/material.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/material.py:33>)、[edabench/material.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/material.py:99>)、[edabench/material.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/material.py:117>)、[edabench/material.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/material.py:145>) | 验 hunk 计数/缺 patch、递归树 truncated 时逐树遍历、按文件字节/模式/链接重建 Git tree 后才本地 diff。实际 15 diff 摘要和独立统计一致，case-14 含 rename；case-05/06 的 4 个快照 tree 独立重算匹配。实际样本不覆盖所有 binary/符号链接分支。 |
| LEFT/RIGHT、多行、旧位置 | [edabench/revisions.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/revisions.py:63>)、[edabench/revisions.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/revisions.py:103>) | 原行号优先、旧 original_position 回退、双侧原始 hunk 一致性；跨侧范围/缺上下文保留 null。独立解析结果为 30 verified、7 正确保留 null，未发现这 37 个根的定位错误。 |
| 构造/导出完整性 | [edabench/build.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/build.py:18>)、[edabench/build.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/build.py:138>) | 仅 complete 原采集、ready 构造、摘要正确且含代码变更的 diff 可导出；无可定位非 bot 评论 PR 被排除，仍保留通过 PR 内未定位评论。失败、不完整和排除原因有留档。 |
| LLM 输入与上下文 | [scripts/prepare_thread_pilot.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/prepare_thread_pilot.py:68>) | 同版本完整线程、原 hunk、所选文件 patch、左右窗口、最近四同文件邻居；当前线程不截断。跨文件显式指代可能遗漏，绝对 full_diff_path 不便搬迁，见 CTX-01。 |
| 输出 schema/来源 | [scripts/assemble_thread_annotations.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/assemble_thread_annotations.py:156>)、[scripts/annotation_queue.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/annotation_queue.py:123>) | 校验 key/hash、decision/category、非空理由/summary、当前线程至少一个证据 ID、精确锚点/null；不能判定理由真假、类别是否技术合理、是否测试过。CODE-02/03 是具体缺口。 |
| PR join/统计与修复 | [scripts/build_pr_candidates.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/build_pr_candidates.py:29>)、[scripts/build_pr_candidates.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/build_pr_candidates.py:186>) | 对 PR/revision/assessment 唯一性、缺失/多余、来源指纹、可定位候选多重集合交叉检查；保留零候选 PR、未定位意见及修复来源。原设计未做跨线程语义去重；case-05 提醒评测前需处理同义参考。 |

## 测试结果及解释

**最终完整原套件在真实 Linux 环境运行：72 passed，0 failed，4.20s。** Ubuntu 24.04 / WSL2，Python 3.12.3，Git /usr/bin/git；fixture 使用 Linux /tmp 专属临时目录，没有修改原代码/测试、没有换行 monkeypatch、没有排除测试。日志 [pytest_linux_posix.log](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/logs/pytest_linux_posix.log>)，环境 [linux_test_environment.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/linux_test_environment.json>)，运行器 [run_linux_tests.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/run_linux_tests.py>)。此结果补齐了此前 4 个符号链接/归档回退测试，但不消除 Windows 的可移植性缺陷。

运行原项目全部 72 个测试案例，日志 [pytest_original.log](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/logs/pytest_original.log>)：**52 passed，20 failed，3.76s**。失败分为 14 个 fixture 使用 LF 摘要而落盘为 CRLF 的连锁断言、2 个 prepare 的实际跨平台摘要缺陷、4 个符号链接 fixture 创建失败（WinError 1314）。全部失败名称和堆栈已保存，未删改原测试。

为了区分字节换行与其他逻辑问题，在独立诊断运行中将 Path.open 文本写入和 NamedTemporaryFile 文本写入设为 LF，并排除上述 4 个符号链接 fixture：**68 passed，4 deselected，2.36s**。脚本 [run_tests_lf_diagnostic.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/run_tests_lf_diagnostic.py>)，日志 [pytest_lf_diagnostic_final.log](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/logs/pytest_lf_diagnostic_final.log>)。这是 Windows 的 LF 模拟诊断，与上述真实 Linux 完整运行分别留档。

首次 WSL 运行将 fixture 放在 /mnt/d 的 Windows 挂载盘，得到 71 passed、1 failed（12.22s）；Git 初始化为 core.filemode=false，run.sh 可执行模式未进入 fixture 提交，导致期待 100755 的断言失败。随后使用 Linux /tmp 重跑完整套件，72 全通过。保留 [pytest_linux_mntd.log](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/logs/pytest_linux_mntd.log>)、[挂载盘 fixture Git 配置](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/evidence/linux_mntd_fixture_git_config.txt>)，不把文件系统差异归成算法缺陷。

Windows CLI 导入因 fcntl 不可用失败，见 [windows_cli_import.log](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/logs/windows_cli_import.log>)。最初沙箱内 WSL 查询受限；自动审核允许只读查询后找到 Ubuntu 24.04，实际完成上述运行。依赖安装/纯 Python 包复制仅在本批 env 内，未安装系统软件、未使用归档凭据。Linux runner 关闭额外 pytest 插件自动加载，套件不依赖外部插件；临时目录为专属测试夹具。

## 可重现问题与最小修复

### CODE-01：输入摘要绑定错误（Windows 工作流 P1）

[scripts/prepare_thread_pilot.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/prepare_thread_pilot.py:25>) 文本临时文件默认 newline=None，在 Windows 将 LF 转 CRLF；[scripts/prepare_thread_pilot.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/prepare_thread_pilot.py:35>) 却对转写前 text.encode() 求哈希。合成复现 reported=6a161db74b5017aebb5423cd4c406e29466ef14de03a3165d80721f9a2cbfe2e，actual=2b7c02b09d64a4648be9d18d44513606c9744e8e730ce20ebdb1df4fcc8cb1fc。结果是自身生成输入无法通过队列/汇总的摘要规则，复用与恢复也可能失败。

最小修复是固定 newline='\n'，或写 UTF-8 二进制并对相同字节求摘要。现有 34,822 个归档输入全部匹配，因此本项不说明原 Linux 批次已经损坏。

### CODE-02：重复 manifest 可产生假完整状态（P2）

[scripts/assemble_thread_annotations.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/assemble_thread_annotations.py:269>) 不先验证 manifest 唯一性，循环按任务累加；[scripts/assemble_thread_annotations.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/assemble_thread_annotations.py:411>) 仅以有效输出计数比较 population_threads。两个重复 full 任务、一个唯一线程的隔离样本得到 valid_output_count=2、classification_complete=true。

queue._validate_manifest 已拒绝重复，后续 PR 聚合也拒绝重复 assessment，故不是全路径可逃逸；实际 manifest 无重复。最小修复：assemble 入口复用唯一性/字段校验，以唯一集合核对人口规模后再统计。

### CODE-03：伪验收声明可透传（P2）

[scripts/assemble_thread_annotations.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/assemble_thread_annotations.py:156>) 没有允许字段集合；[scripts/assemble_thread_annotations.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/assemble_thread_annotations.py:385>) 将 dict(result) 原样扩入 assessment。合成合法结果添加 human_verified=true、tests_executed=true 后，validate_result 返回 []。总报告 human_verified=false 未同步禁止单项伪声明。

最小修复：闭合输出字段，禁止 worker 自行提供验收、执行、provenance 标志；仅按可信运行记录生成它们。本次全量结果仅 1 个额外 input_file（firesim/firesim#1497:1186576028），没有观察到伪 human_verified/tests_executed；这是防线缺口，不是已证造假。

三项合成复现使用原函数、独立夹具/输出目录；详见 [risk_reproductions.py](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/risk_reproductions.py>) 和 [risk_reproductions.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/risk_reproductions.json>)。源码未应用修复。

### 上下文与移植风险

case-07 的跨文件回复不在当前 thread packet 内，说明只选最近四同文件邻居不能完整覆盖显式引用；应额外解析同 PR/选定版本的评论链接，同时保留 missing context 提示。已有 full_diff_path 为原机绝对路径，搬迁后应通过 relative path+hash 解析，不能默认其可访问。完整 PR 本次读到了额外回复，不证明首轮 worker 也读到了。

## 全量结构验证与隔离重建

[full_annotation_checks.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/full_annotation_checks.json>)：34,822 个任务、同数唯一线程/输入文件，覆盖 dataset；每个实际输入哈希、结果 schema、PR/SHA、anchor、导出评论正文、diff 摘要关联一致；error_count=0。这里使用原 validate_result 校验格式，并自行做源集合/关联检查；不是独立评判所有模型语义。

全量 decision：candidate_issue=26,027，no_issue=7,045，needs_context=1,750。候选 issue 共 26,512，类别为维护/可读性 20,415、code_defect 5,319、performance 493、security 285。类别计数单位为 issue，不能与线程数混用。

隔离输出 [aggregate_rebuild](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/aggregate_rebuild>) 得到：10,727 PR、34,822 线程、67,556 评论；8,680 PR 有候选，8,594 PR 有可定位候选；24,497 可定位意见、2,015 未定位意见。原/重建 CSV、statistics、报告内容仅换行不同；PR JSONL 另有 556 个 PR 的 repair.record_file 相对路径因输出位置变化而不同。仅将这个来源路径归一后 10,727 条记录无语义差异，未归一 label、reason、summary 或其他字段。摘要与比较分别见 [aggregation_rebuild_checks.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/aggregation_rebuild_checks.json>)、[aggregation_semantic_comparison.json](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/aggregation_semantic_comparison.json>)。

## 结论与优先级

现有原始审阅语料和关联可以保留；结构完成不代表语义正确、真人确认或可直接作金标准。先修输入摘要与完整性/来源校验防线，再复核两条明确需要修改的 LLM decision 及含糊 summary，详见 [15例独立审阅](<D:/Projects/researches/EDACR/docs/EDABench_15例独立审阅.md>)。在完整仓库评测前补齐缺源码案例，并处理同义参考、上下文缺失和后续材料的使用边界。

未进行全量语义审阅、真人专家验收、EDA 编译/仿真、被测 reviewer 评测、GitHub 实时重新采集或 AACR 方法对照。复现命令和证据索引见 [本批 README](<D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/README.md>)。
