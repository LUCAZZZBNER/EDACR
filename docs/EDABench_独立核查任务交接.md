# EDABench 独立核查任务交接

交接日期：2026-10-05（Asia/Shanghai）。工作区：`D:/Projects/researches/EDACR`。本文供用户在新的独立对话中交给 LLM 接手，包含任务、上下文、已完成工作、文件位置、证据边界和交付要求。

## 1. 接手后需要完成什么

用户希望核查学长提供的初步 EDABench 项目，判断数据采集、版本对齐、LLM 候选判断是否可靠，并核对与 AACR-Bench 的对应关系。接手后请实际开展核查并产出报告，不要只解释概念或再次提供计划。

学长原话：

> 这是我之前初步跑的一个EDAbench的结果，你可以看看，检查哪些有效。主要内容是按照我们上次提到的AACR-Bench那篇工作进行了复现，复现的EDA仓库在docs下的excel中，来自于大创同学初步收集选择的仓库。然后我有一个GitHub的API爬取。接着是用llm做了一个初步的判断，得到了基本的数据集。目前它的内容是GPT-6写的，我没来得及校验，你检查检查代码的正确性，挑十几个case人工看看是否正确收集，然后看看LLM的初步判断是否正确，是否对得上AACR-Bench论文中的实现吧。

具体目标：

1. 审查采集、材料构造、版本选择、评论定位、LLM 输入/输出校验和 PR 聚合代码，验证关键规则及测试，记录可复现的问题。
2. 独立挑选约 15 个 PR case，检查原始收集、版本与 diff、评论定位及 LLM 判断。至少覆盖不同仓库、文件类型、decision 和复杂讨论，明确每个 PR 实际检查的线程范围。
3. 对照 AACR-Bench 论文及固定版本参考代码，说明哪些阶段得到复现、哪些是项目自定义口径、哪些尚未实现或没有验收证据。
4. 给出哪些样本/线程可以作为候选继续使用，哪些需要修正、补充上下文或专家确认。不要把有限抽查结果外推为整个数据集的真实正确率。

“人工看看”是学长的原始要求。LLM 接手可以逐例独立阅读和核对，但不能把自己的审阅写成真人专家验收。请将此部分标为“LLM 独立审阅”，保留待真人确认事项和证据。

## 2. 当前对话完成了什么，未完成什么

### 已完成

- 原研究方向 PPT 已移入本工作区的 docs，并生成研究方向与创新点大纲。
- 学长提供的 Google Drive 项目包已经完整下载，无需再次下载。
- 扫描了整个压缩包目录，生成完整路径/大小清单和逐文件用途 CSV。
- 选择性解出了主要 Python 源码、测试、项目文档、原始导出数据、PR 候选汇总、关联 diff 和部分标注运行说明。
- 阅读过部分采集/构造/标注管理代码、项目说明和已有十例抽查记录，解释了各目录职责与数据流。
- 曾对已导出样本引用的 10,724 个唯一 diff 路径进行摘要核对，记录中未发现不匹配；样本数为 10,727，不能把唯一 diff 数量当成 PR 数量。
- 曾重新计算原始 samples.json 摘要，与 manifest 一致。
- 查询过 AACR 官方 README、论文摘要和 GitHub API 官方文档；尚未逐页审读论文、逐模块验证全部实现。
- 用一个真实样本核对了源码关联方式：samples 不含直接的 archive_path，只记录 repository、source/target SHA 和 diff_path。

### 尚未完成

- 没有完成系统性代码审计，也没有在当前工作区运行原项目测试套件。
- 没有新增 15 个 case 的独立核查或真实专家验收。
- 没有完成全量 LLM 标签正确性检查。
- 没有逐项完成 AACR 论文方法对照。
- 没有在 EDA 样本上运行被测代码审查模型并输出 benchmark 得分。
- 尚未完整解出原始采集数据库、全部逐线程输入/输出和全部源码归档。

前期用户曾要求“下载完先别分析”，当时已停止审计，仅继续下载；之后授权了目录梳理和本交接文档。当前交接的目的，是在新的独立对话中启动上述核查任务。不要把此前的材料阅读当成已经完成该任务。

## 3. 路径与下载完整性

| 名称 | 绝对位置 |
|---|---|
| 工作区 | `D:/Projects/researches/EDACR` |
| 下载存放目录 | `D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05` |
| 原始项目压缩包 | `D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/edabench.tar.gz` |
| 当前选择性解出的项目副本 | `D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench` |
| 下载期间的早期预览副本 | `D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/preview/EDABench` |
| 完整压缩包目录清单 | `D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/archive_inventory.json` |
| 逐文件用途清单 | `D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/project_file_catalog.csv` |
| 下载状态 | `D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/download_status.json` |
| 本交接文档 | `D:/Projects/researches/EDACR/docs/EDABench_独立核查任务交接.md` |

压缩包来源：学长提供的 Google Drive 原始备份（含凭证，公开文档省略原始下载链接；共享数据使用仓库 README 中的脱敏数据链接）。文件名 edabench.tar.gz，大小 **16,572,762,941 字节**，本地下载后计算的 SHA-256：

```text
9a94bb0c99e829b1c9a5f23295765d0a36156d3e3e400aae4fe5ecd0628547c5
```

这是本地完整性记录，不是独立提供方签名。download_status.json 已为 complete，后台下载工作已经结束，不要按旧 PID 恢复下载。

压缩包内根目录为 `EDABench/`。完整目录包含 88,767 个普通文件和 263 个目录，文件内容合计 54,825,872,469 字节。目录清单已读完整 tar 流；不是早期前缀扫描结果。嵌套源码归档展开后体积还会增加。创建交接时 D 盘剩余约 350.03 GiB；正式解压前应重新检查。

注意两个 data：外层 EDACR/data 是本次下载的存放目录；压缩包内 EDABench/data 才是学长项目的生成数据目录。

## 4. 已有说明文档

优先阅读以下真实本地文件；用户可能在 IDE 中编辑过，保留现有内容，不要覆盖：

- [目录与文件说明](D:/Projects/researches/EDACR/docs/EDABench_目录与文件说明.md)
- [研究方向与创新点大纲](D:/Projects/researches/EDACR/docs/EDACR_研究方向与创新点大纲.md)
- [研究方向 PPT](D:/Projects/researches/EDACR/docs/EDACR.pptx)

原 PPT 的思路：PR 级 EDA code review benchmark；收集 PR、提交、文件、审查线程；按目标审查版本组织评论；选择一个审查版本；将基线到该版本的完整 diff 作为代码改动材料，将对应实质审查意见作为参考。

PPT 表述与项目实际口径可能有差异，例如项目按独立根线程计票而非简单评论条数，原始导出先保留未做语义筛选的评论。核查时记录差异和依据，不要自动认定它们完全一致。

## 5. 项目结构和数据流

以下是压缩包内部路径，不表示都已经解出到磁盘：

```text
EDABench/
├── docs/                 PPT、仓库名单及方法/标注/运行说明
├── edabench/             GitHub 采集、版本/评论对齐、完整 diff 和原始导出
├── scripts/              LLM 输入准备、队列、结果校验、PR 候选聚合
├── tests/                自动化测试
├── reference/            AACR 论文、固定版本官方代码、来源记录
├── config/github.yaml    原始 GitHub 凭据配置
├── data/
│   ├── state.sqlite3     原始 API 记录和采集状态
│   ├── diffs/            固定 source→target 的完整 diff
│   ├── archives/         部分固定提交的完整源码快照
│   ├── dataset/          原始 PR/评论导出及来源、失败记录
│   ├── annotation/       LLM 逐线程输入/输出及汇总、修复记录
│   ├── pr-candidates/    按 PR 汇总原始样本与线程标注
│   └── audit/            包内已有抽查材料
├── results/              本包为空
└── .git/、运行缓存
```

数据流：Excel 仓库名单 → GitHub API 原始缓存 → 选择审查 revision/基线并构造 diff → dataset 原始样本 → annotation 对已有讨论做 LLM 判断 → pr-candidates 按 PR 聚合。

### 5.1 概念与版本关联

- B/source_commit：基线版本；R2/target_commit：选中的审查版本；R3 可表示后续修复版本。示例编号只是讲解用符号，实际使用 commit SHA。
- revision：在这里指具体 commit 对应的代码版本，不是 PR 编号。
- 线程：根评论及回复。项目按根评论 original_commit_id 归组；后续回复不单独增加版本票数，也不改变根线程归属。
- 版本选择在材料构造阶段已经发生，不是到 dataset 才选择。dataset 记录最终 PR、版本、评论和 diff 的关联。
- diff 命名：`EDABench/data/diffs/<owner>/<repo>/<sourceSHA>..<targetSHA>.diff`。
- 源码快照命名：`EDABench/data/archives/<owner>/<repo>/<SHA>.tar.gz`。
- archives 是共享材料缓存，不保证覆盖所有导出 PR 的 B/R2；也可能含未成功导出的 PR 或其他用途产生的材料。单个 SHA 包是完整文件树快照，不是仓库全部 Git 历史。
- 未来完整仓库上下文评测须准备与审查 target SHA 对齐的源码目录；原始评论和后续修复不能泄漏给被测审查模型。此项目目前没有完成该评测环境。

### 5.2 dataset

已解出到：`D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/data/dataset`。

六个文件：samples.json、manifest.json、report.json、decisions.json、alignment_failures.json、unavailable_history.json。

samples.json 为 JSON 数组，353,229,255 字节。此前重新计算摘要与 manifest 一致：

```text
02643c183771086b6f2cc1474dd08dc773864d34c2edfa45bb9550fbc388de28
```

核心字段：githubPrUrl、source_commit、target_commit、project_main_language、change_line_count、comments、metadata。评论正文在 `comments[].note`；位置为 path/side/from_line/to_line；comment metadata 含作者、评论 ID、原始 commit/行号、线程关系、原始 hunk、定位状态与后续改动证据。

样本 metadata 含 repository、number、title、body、diff_path、diff_sha256、raw_database、raw_pr_entity、历史/事件关联、版本投票和统计。diff_path 相对项目 data 根目录。category/context/source_model 在原始导出中留空，原始 GitHub 评论 is_ai_comment=false 不代表确定作者没有使用 AI。

decisions.json 是 PR 构造/导出决定，不是 LLM decision。原始导出保留相关非机器人评论，包含说明、感谢、Done 等，不能直接全部当作缺陷参考答案。

### 5.3 原始数据库与代码材料

state.sqlite3 大小 **40,102,420,480 字节**，尚未解出。配套 state.sqlite3-wal 本包为 0 字节，state.sqlite3-shm 为 32,768 字节。

storage.py 定义：meta（元信息）、responses（按页 API JSON/文本及部分响应头/时间）、entities（按 kind/repo/id 索引的 JSON）、tasks（任务状态）。collect.py 可见 repository、pr_index、comment_index、pr、commits、files、reviews、inline、discussion、threads、events、revision、history 等实体；材料构造还有 selection、construction、diff 等。请以实际数据库和源码为准查询，不假设每种实体都按单个评论分行存储。

完整包中有 15,297 个 diff，内容约 3.75 GB；2,353 个源码归档，合计约 9.41 GB。缓存数不等于导出样本数。

### 5.4 annotation

主要批次：pilot-200-20260926（150 随机＋50 定向复杂线程）与 full-20260926（全部 34,822 个导出线程）。全量目录有同数 inputs 和 results。

模型任务是阅读完整线程、相应代码与必要的相邻线程，对已有讨论进行判断和提炼，不独立增加当前线程从未提出的问题：

- candidate_issue：有支持材料的具体技术诉求，包括维护性、可读性、格式/注释建议；不保证是功能 bug。
- no_issue：无可保留诉求或质疑已被解释清楚；不代表整个 PR 没缺陷。
- needs_context：上下文不足或有未解决争议。
- 四类候选 category：code_defect、security、performance、maintainability_readability。

主文件：manifest.json、execution.json、thread_assessments.jsonl、candidate_issues.jsonl、needs_review.jsonl、report.json。candidate_issues 汇总只导出可定位候选；未定位候选仍可在 assessments/needs_review 和 PR 聚合中保留。

全量目录另有 queue.sqlite3、WORKER.md、feed_queue.py、watch_run.py、日志和历史状态；queue.db 和 queue.sqlite 本包是 0 字节。classification_complete=true 指当前结构规则通过，不是所有语义判断正确。location_status=verified 指位置验证，不是专家确认。

项目文档 `docs/thread-full-run.md` 明确写明：“全量分类不增加LLM发现新问题的阶段，也不生成已确认缺陷或人工金标准。”这一点已确认。

运行记录标注首轮模型是 **gpt-5.6-luna / max**，通过 Codex worker 执行；学长说 GPT-6 写实现，可能指编程过程，两者不是同一概念。不要直接判定学长描述错误。修复记录注明后续 Codex 定向复核，与首轮生成配置不同。

### 5.5 修复留档

full-20260926/repair-20260929 中保留 633 份无效输出修复材料：repairs.jsonl、initial_invalid.json、review_packets.json、summary.json、scope.json、repair_groups.json、original_results、original_aggregates、队列备份及 execution_scripts。

包内 README 记录 489 份主要为确定性锚点规范化，144 份为 Codex 定向复核，11 个 decision 改变。修复记录不是新增真人验收。旧 supervisor/status 或原汇总可能早于最终修复，不应混读或当作最终产物。

### 5.6 pr-candidates

已解出到：`D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/data/pr-candidates/full-20260926`。

五个文件：pr_candidates.jsonl、pr_summary.csv、statistics.json、report.md、manifest.json。

它把 dataset 的 PR/revision/原始评论关联，与 annotation 的线程判断、理由、候选意见和来源相结合；不重新调用 LLM，保留零候选 PR。PR 聚合不完整复制全部评论全文，使用 IDs 和 provenance 追溯。

### 5.7 audit 的真实边界

已解出到：`D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/data/audit/random-10-20260926`。

抽样单位是 **10 条导出评论**，seed=20260926；恰好涉及 10 个 PR 和 7 个仓库。不是随机抽 10 个 PR 的设计。

包内 checks.json 记录程序核对：原文、非明确机器人、版本选择重现、根版本、构造 SHA、diff 摘要、定位结果等。README 与 review-01-05/review-06-10 记录缓存和代码阅读。文档有“主代理”等措辞，不能据“人工阅读”字样认定由真人专家验收。

报告记录十条原文/关联一致、八条定位验证、两条正确保留未定位。不联网、不验证缺陷实际存在、不把 resolved/Done 当采纳证明；不是完整 LLM 标注验收。`location_result_matches=true` 也可能表示正确重现一个定位失败，而非定位成功。

接手者可借鉴方法，但必须新增独立样本和判断，不把旧报告复制成自己的核验结果。

## 6. 已知规模和方法边界

以下为包内产物及已读 manifest 的记录，后续报告要核对来源，而不是默认全部属实：

| 指标 | 当前记录 |
|---|---|
| Excel 仓库输入行 | 44 |
| 贡献导出 PR 的仓库 | 34 |
| 导出 PR | 10,727 |
| 导出线程 | 34,822 |
| 原始导出评论 | 67,556 |
| 有候选意见的 PR | 8,680 |
| 有可定位候选意见的 PR | 8,594 |
| 候选意见 | 26,512 |
| 可定位候选意见 | 24,497 |
| 未定位候选意见 | 2,015 |
| 原始采集完成状态 | complete=false |
| 人工验收 | human_verified=false |

采集截止时间为 2026-09-21T15:21:52.199716Z，API 观测范围约为 2026-09-21 至 09-24。API 缓存不是截止时刻的事务性历史快照；编辑、删除、resolved/outdated 等存在观测时刻边界。

项目保留 closed PR，包括未合并；未按 stars、主语言、自然语言、LOC、文件数和采纳情况限制；源码/测试/构建/约束文件计作代码，纯文档 PR 排除，混合代码文档 PR 保留。这些是项目规则，不代表与论文全部相同。

每 PR 一个 revision，每个含非明确机器人的独立根线程一票；并列按最早根审查时间，再 SHA。只凭 GitHub Bot 类型或 [bot] 后缀排除，未知身份保留。

OpenTitan 贡献 PR 约占总体 57%，大 PR 与维护性候选占比偏高；这是此前统计观察，后续应重读 statistics/report 定位具体口径。没有按全文读取/逐条复核整个总体。

## 7. 已核对过的具体样本事实

原始 samples.json 第一条对应 [analogdevicesinc/hdl PR #26](https://github.com/analogdevicesinc/hdl/pull/26)。

```text
repository: analogdevicesinc/hdl
source_commit: e77428c50e4ac7e6ec3887788f09eb0c9dabba5a
target_commit: c6eb1c6c8b16991480b9b764fd39459b10631a82
diff_path: diffs/analogdevicesinc/hdl/e77428c50e4ac7e6ec3887788f09eb0c9dabba5a..c6eb1c6c8b16991480b9b764fd39459b10631a82.diff
first_comment_path: projects/fmcomms5/zcu102/system_bd.tcl
```

实际检查了完整目录：该 B 与 R2 的 archive 包均未保存；对应 diff 已解出。这个事实说明 samples 可正常关联版本和 diff，却不保证有完整源码快照。不要推广成所有 PR 都缺源码。

## 8. 核查步骤和证据要求

### 阶段 A：建立可用材料和基准

1. 阅读本交接、目录说明、项目 AGENTS/README、docs/method.md、thread-annotation.md、thread-full-run.md、pr-candidates.md。
2. 读完整 inventory 判断哪些文件已解出；选择性补齐数据库及所选 case 的输入/输出、修复记录和参考材料。
3. 尽量一次顺序扫描 tar 取出所需文件。大 gzip 不支持廉价随机访问，避免为每个 case 单独重新扫描 16.57 GB 包。
4. 解压前检查空间，校验成员路径，拒绝越界路径/不安全链接；不要执行仓库或解包脚本。
5. 保留原始包、已有导出、旧 audit。为新核查建立独立批次目录。

补齐材料至少包括：原始 state.sqlite3 及配套文件；选中 threads 对应 inputs/results；需要的 annotation 汇总/完整 manifest；必要修复前输出；reference 论文和官方实现。不要假设 4 位编号能直接由 comment ID 推导，按 manifest/provenance 找文件。

### 阶段 B：代码与测试

按实际行为和风险审查，重点：

- 输入仓库读取和去重、PR 范围和截止时间、REST/GraphQL 分页、接口数量上限与失败状态。
- 嵌套线程分页、回复继承、缺根/循环、机器人与作者身份。
- revision 选择是否符合既定口径，是否误用最终 head。
- base/ref/force-push 恢复、merge base 与 hunk 证据是否足够，未公开历史的边界是否说明。
- patch 截断、binary、rename、模式变更、完整 diff 和归档树验证。
- LEFT/RIGHT、多行、旧 original_position、原始/当前行号混用，未定位是否保持 null。
- 构造和导出规则、摘要关联、失败与 incomplete 状态、可重复生成。
- LLM 输入是否串线程/串版本、是否错误截断讨论、是否提供会改变任务含义的后续材料。
- 结果校验是否只确保格式，语义方面有哪些不能由程序证明的地方。
- 候选聚合的重复/缺失/多余 join、零候选、未定位、修复来源和统计分母。

运行原有测试；新增测试仅针对具体风险或已发现问题，不写镜像实现的无意义断言。每个确认缺陷提供可重现证据、代码位置、影响和最小修复建议；不确定之处明确标为风险或需要进一步证据。

不要一开始重跑 GitHub 全量采集或全量标注。离线核查已有产物即可获得大量证据。不要直接对原始数据运行会写入的 collect/run/build 或队列修复；需要实验时使用独立输出和隔离的验证数据。

### 阶段 C：约 15 个 PR case 的独立核查

样本选择建议：保留一部分固定种子随机 PR，再补充边界 PR；随机组与定向组分开报告，定向样本不用于估计总体错误率。不要仅挑有候选/容易验证的样本。

覆盖不同仓库、RTL 与 EDA 软件/构建/测试文件、小/大改动；不同 decision；多轮争议、短回复、跨线程指代、未定位、多行、重命名、后续修复等。从 pr_summary.csv 起步，记录抽样规则、seed、总体和实际覆盖。

对每个 PR：

1. 固定 repository、PR 编号、source/target SHA、选定的线程列表。
2. 原始样本 note 与 API body 对照；核对作者、comment ID、回复/根关系。
3. 用原始线程按规则独立重算版本选择，不只相信现有 selection；对照根 original_commit_id。
4. 核对 baseline/construction/diff 的版本和来源，检查是否使用了最终版本。
5. 独立解析 unified diff，核对评论 path/side/range 与原始 hunk 内容。避免仅再次调用同一定位函数作为独立证据。
6. 查 inputs 和 results，阅读完整当前线程及必要相邻证据和代码；先形成自己的判断，再比较原标签，减少被模型输出引导。
7. 检查 decision、类别、候选 summary、位置、证据 ID 和多问题拆分；特别注意 Done、作者说明、争议已否定、邻线程污染和无依据后果。
8. 如果结果被修复过，对照 repairs/original_results，标明当前与首轮模型的差异。
9. 分别记录“采集/对齐正确”“候选意见符合口径”“技术事实是否成立”；后者无法确认时保留 unknown，不通过拍脑袋补齐背景。

约 15 个 PR 不意味着只读 15 条评论。对每个 PR 明确检查哪些完整线程、多少条评论/意见。对于过大的 PR，先声明审阅范围和选择规则，不能只读一个线程却声称全 PR 已验收。

建议每线程的检查字段：case_id、repository、PR URL、B/R2、thread_key、comment IDs、输入/结果路径及摘要、原标签/类别、独立判断/类别、采集状态、版本/定位状态、语义状态、证据、修正建议、需专家确认事项。

### 阶段 D：AACR-Bench 对照

优先读本地论文和固定 commit 官方参考代码，必要时查原始官方来源。不能只凭论文摘要或当前 GitHub README 宣称方法完全一致。

逐项比较：仓库/PR 来源与筛选；版本选择与基线；完整 diff/仓库上下文；评论定位；已有意见整理与 AI 新问题补充；专家核验及一致性；分类体系；正负样本与拆分；被测 reviewer、评测 judge 和指标；未来版本/人工参考泄漏控制。

对照表字段：论文/参考实现依据（页码/节/文件行）、本项目实现位置、实际产物证据、差异、影响、建议。标为“已对应”“自定义差异”“未实现”“证据不足”，不要用笼统“复现成功/失败”掩盖阶段差异。

### 阶段 E：总结有效性与优先级

给出分层结论：

- 适合保留为原始审查语料的样本/线程。
- 采集、版本或位置需要修正的样本/线程。
- LLM 判断合理但还未经专家确认的候选意见。
- LLM 错判、错误提炼或需额外上下文的意见。
- 暂时不能用于完整仓库上下文评测的缺源码/缺历史案例。

列出最影响 benchmark 可信度的修复优先级，并把“结构完整”“语义正确”“专家确认”“可评测”分开说明。

## 9. AACR 参考来源

- [论文 AACR-Bench: Evaluating Automatic Code Review with Holistic Repository-Level Context](https://arxiv.org/abs/2601.19494)
- [论文 v3](https://arxiv.org/abs/2601.19494v3)
- [官方代码](https://github.com/alibaba/aacr-bench)
- 固定参考 commit：`68a569759289a83654a59d06db2a72910edf0a4a`，来源在项目 reference/aacr-source.json。
- 论文 PDF 压缩包内路径：`EDABench/reference/2601.19494v3.pdf`。
- 官方参考源码压缩包内路径：`EDABench/reference/aacr-bench/`，包括 dataset、evaluation、reviewers、converters、judge、schema 等。
- [GitHub PR review comments 官方文档](https://docs.github.com/en/rest/pulls/comments)。

官方参考评测代码存在，不等于本项目已经执行该评测。当前项目根 results 为空。不要把官方 positive/negative_samples 当成 EDA 新数据。

## 10. 环境、凭据和执行限制

- 主机为 Windows / PowerShell；中文文件用 UTF-8 读取，Python 输出建议使用 `python.exe -X utf8`。以前默认编码导致终端中文乱码，但文件本身可正常 UTF-8 读取。
- 原项目使用 fcntl 文件锁，watch_space.py 使用 Linux /proc；不能假设 Windows 下所有运行入口都可直接执行。先确认可用运行环境；不要为了跑测试未经证据大改采集语义。环境导致无法运行的项目，与程序缺陷分开记录。
- 当前工具默认 sandbox 曾出现启动问题，获自动审核的 require_escalated 调用可正常读写工作区；遇到限制按当前会话权限处理，不需要重复下载或篡改权限配置。
- 当前工作区写权限以新对话实际设置为准；不要修改受保护的 .git、.agents、.codex、.aws 等目录。
- 压缩包 config/github.yaml 含明文 GitHub PAT。早期预览读取曾暴露过一次，已告知用户并将 preview 配置脱敏。不要再次输出、使用或复制密钥到报告；原始包未改动。解出阅读材料时跳过凭据配置。不要自动使用这个 token 开始联网采集。
- 不要执行归档内仓库脚本或临时修复执行脚本；后者是历史留档，不是常规入口。
- 原始数据库应只读核查；读 SQLite 时处理好 WAL/SHM，保留原件。除非确认快照无未合并 WAL，否则不要随意用 immutable 参数绕过日志。不要用 Store 初始化器/构建入口代替只读检查。
- 可以在独立核查目录保存派生索引、测试日志、抽样包和报告。原始 samples、annotation、pr-candidates、旧 audit 与现有用户文档保持可追溯。
- 旧 download_status 的 complete 只表示下载完成，annotation 的 complete 只表示该批输出/结构完成，dataset 的 complete=false 表示原始采集仍不完整。
- 用户希望自主推进，不要在每个可逆步骤重复询问。只有真实缺失信息或权限会阻止动作时才询问，并继续可独立完成的部分。
- 不要自行创建新聊天、自动化或对外发消息。用户自己会开启独立对话。是否使用子代理遵循新对话的明确授权和工具规则，本交接不要求多代理执行。

## 11. 建议交付位置与格式

新核查的派生数据可放：

```text
D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/<新批次>/
  sampling_manifest.json
  case_checks.csv
  cases/<case编号>.md
  code_findings.json
  logs/
```

最终报告建议新建，以下文件当前尚未创建：

1. `D:/Projects/researches/EDACR/docs/EDABench_代码核查报告.md`
2. `D:/Projects/researches/EDACR/docs/EDABench_15例独立审阅.md`
3. `D:/Projects/researches/EDACR/docs/EDABench_AACR方法对照.md`
4. `D:/Projects/researches/EDACR/docs/EDABench_核查结论与下一步.md`

可按实际情况调整文件拆分，但必须包含：执行范围与限制、证据出处、测试结果、每例材料/语义判断、明确问题及优先级、论文对照和未决事项。代码建议可形成最小补丁文件；未经用户要求不要直接改写原始标签或重新生成整套数据覆盖来源。

验收标准：

- 关键代码规则得到实际检查，问题有定位与可重现证据；测试运行或无法运行的真实原因有记录。
- 独立抽查约 15 个 PR，样本规则和每 PR 审阅范围透明，评论/版本/位置和模型判断分开评估。
- 所有“正确/错误/不足”结论有对应材料，不用模型置信度代替证据，不冒称真人专家。
- AACR 对照引用实际论文/固定实现，不只重复项目自述。
- 输出当前哪些材料可继续用、哪些需要处理，并列出最先应修的事项。
- 报告明确尚未进行的全量审阅、专家验收及被测模型评测，避免把抽查结果包装成最终 benchmark。

## 12. 沟通与启动方式

用户是该方向初学者，已理解仓库、PR、SHA、revision、线程、RTL/EDA 工具代码以及主要目录的含义。解释结论时用中文、具体例子和清楚的证据；少重复基础定义，重点说发现、影响和下一步。

接手后的首条进展可以概括已接受三项核查任务，然后先读项目规则、确认材料、建立独立抽样。不要再次把完整目录讲解一遍，也不要从零下载项目。

本文中的规模、已读行为和旧审计结论都是接手线索，不能代替你的独立验证。请把新增结论与这些历史记录分开，直到有实际证据支持为止。
