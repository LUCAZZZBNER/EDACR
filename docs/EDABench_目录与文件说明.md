# 下载项目 EDABench：目录与文件说明

> 2026-10-07 目录迁移说明：本文保留当时阶段的记录，当前项目根目录为 `D:/Projects/researches/EDACR/`；原始压缩包已按要求删除，原始数据从学长云盘恢复。当前目录与历史路径对照见 [项目目录与迁移说明](project-layout.md)，本轮结果在 `data/audit/20261006_c/`。

依据：2026-10-05 对完整 `edabench.tar.gz` 的目录扫描，以及包内 Python 源码、说明文档和运行记录。本文解释文件职责，不代表已经完成代码正确性检查或逐条语义验收。

## 1. 先分清两个 data

本地下载目录是 `D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/`，里面有原始压缩包和下载辅助文件。

压缩包内部的项目根目录是 `EDABench/`。项目自己的 `EDABench/data/` 才是学长采集的科研数据、缓存与 LLM 标注。

当前 `extracted/EDABench/` 是选择性解出的阅读材料，**不是完整解压的可运行项目**。已经解出主要代码、项目文档、原始导出数据、PR 候选汇总和部分其他材料；没有完整解出约 40.10 GB 的原始数据库和全部逐线程文件。`preview/` 则是下载期间更早形成的少量预览副本。

原压缩包已下载完成：16,572,762,941 字节，约 16.57 GB。完整目录扫描得到 88,767 个普通文件、263 个目录，文件内容合计约 54.83 GB；嵌套仓库归档如果进一步解压，体积还会增加。

## 2. 这个项目整体在做什么

它是一套用 Python 写的 **EDA 仓库 PR 审查数据采集与候选意见整理程序**。`edabench/*.py` 是构建数据集的程序；被采集仓库中的 C++、Python、Verilog 等代码是审查对象，两者需要区分。

数据流如下：

```text
docs/final_repository.xlsx：要采集的仓库名单
        ↓
edabench/：通过 GitHub API 采集 PR、评论、提交与历史信息
        ↓
data/state.sqlite3：原始 API 材料与执行状态
data/diffs/：指定 source → target 的代码改动
data/archives/：部分固定版本的仓库源码归档
        ↓
data/dataset/samples.json：版本对齐的原始 PR＋评论数据集
        ↓
scripts/prepare_thread_pilot.py：准备逐线程 LLM 输入
        ↓
data/annotation/.../inputs/ → LLM → results/
        ↓
scripts/assemble_thread_annotations.py：结构校验与线程级汇总
        ↓
scripts/build_pr_candidates.py：按 PR 汇总
        ↓
data/pr-candidates/full-20260926/：候选意见和统计
```

`docs/thread-full-run.md` 明确写明“全量分类不增加LLM发现新问题的阶段”。因此这里完成的是 **基于已有评论的 LLM 整理和分类**，没有在这个阶段独立补充人工漏掉的问题。

## 3. 项目总目录

下图是压缩包内的完整项目结构概览，而不是当前已解出副本的全部文件。

```text
EDABench/
├── README.md                       项目总体说明
├── AGENTS.md                       给 AI 编程助手的工作规则
├── pyproject.toml                  Python 项目与依赖配置
├── .gitignore                      Git 忽略规则
├── config/
│   └── github.yaml                 GitHub API 凭据配置
├── docs/                           输入材料与方法、运行说明
├── edabench/                       原始采集和数据集构造代码
├── scripts/                        LLM 输入、队列、汇总和候选聚合脚本
├── tests/                          程序自动化测试
├── reference/                      AACR 论文、官方参考代码与来源记录
├── data/
│   ├── state.sqlite3               原始材料和采集状态数据库
│   ├── state.sqlite3-wal / -shm     数据库配套文件
│   ├── diffs/                      完整代码改动，15,297 个文件
│   ├── archives/                   固定版本仓库归档，2,353 个文件
│   ├── dataset/                    原始导出数据，6 个文件
│   ├── annotation/                 LLM 线程标注及过程记录，70,811 个文件
│   ├── pr-candidates/              PR 级候选汇总，5 个文件
│   ├── audit/                      包内已有的 10 个样本检查记录，16 个文件
│   └── 运行脚本、日志、状态记录
├── results/                        本包中为空
├── .git/                           项目自身的 Git 历史
└── .pytest_cache/、__pycache__/      测试和 Python 运行缓存
```

文件最多不等于最重要：70,811 个标注文件大多是逐线程输入和输出。最大单个文件是 `state.sqlite3`，40,102,420,480 字节，约 40.10 GB。

## 4. 根目录与 config：入口和设置

| 文件                   | 用途                                                                  | 阅读时要注意                           |
| ---------------------- | --------------------------------------------------------------------- | -------------------------------------- |
| `README.md`          | 总体说明、采集口径、运行入口，以及与候选标注阶段的关系                | 先读它建立全局认识                     |
| `AGENTS.md`          | 约束 AI 编程助手如何修改代码                                          | 不属于数据集或实验结果                 |
| `pyproject.toml`     | 项目名、Python 版本、依赖和测试配置；依赖包括 httpx、openpyxl、PyYAML | 说明这是 Python 数据处理项目           |
| `.gitignore`         | 指定数据、凭据、缓存等哪些内容不提交到 Git                            | 不会影响这些文件实际存在于压缩包中     |
| `config/github.yaml` | 保存采集 GitHub API 时用的 token                                      | 原包含凭据，本文不展示；预览副本已脱敏 |

## 5. docs：输入材料和使用说明，每个文件的职责

| 文件                           | 用途                                                                                               |
| ------------------------------ | -------------------------------------------------------------------------------------------------- |
| `EDACR.pptx`                 | 原始研究方向 PPT，提出 PR 级、按审查版本对齐的 EDA code review benchmark                           |
| `final_repository.xlsx`      | 要采集的 GitHub 仓库名单；程序读取工作表中的`full_name` 列。采集 manifest 记录了 44 条输入仓库行 |
| `method.md`                  | 最核心的方法说明：采集范围、线程与版本选择、base/target、完整 diff、评论定位、导出字段与完整性边界 |
| `running.md`                 | 安装、采集、离线导出、查看状态、限流、中断恢复等操作说明                                           |
| `validation.md`              | 原始采集和构造过程的验证记录；记录本身不替代重新核验                                               |
| `archive-recovery.md`        | 某些仓库归档异常的处理、缓存清理和续跑历史                                                         |
| `speedup-validation.md`      | 采集和材料构造流水线提速后的验证记录                                                               |
| `thread-annotation.md`       | LLM 的标注任务与判定规则：哪些线程是候选问题、无问题或上下文不足；类别和输出格式                   |
| `thread-pilot-validation.md` | 200 个线程试运行的抽样、输入、输出、复核和限制                                                     |
| `thread-full-run.md`         | 扩展到全部已导出线程时的队列、并发、恢复和最终校验流程                                             |
| `pr-candidates.md`           | 如何将线程结果汇总为 PR 候选集，解释五个输出文件及统计口径                                         |

推荐首先读 `method.md`、`thread-annotation.md` 和 `pr-candidates.md`，它们分别回答“怎么收集”“LLM 怎么判断”“最终候选集怎么形成”。

## 6. edabench：学长让你检查的核心采集代码

| 文件             | 具体做什么                                                                                            | 对应需要检查的问题                          |
| ---------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| `__init__.py`  | 声明 Python 包，简述原始版本对齐语料的定位                                                            | 没有主要采集逻辑                            |
| `__main__.py`  | 命令入口；提供 run、collect、build、status，连接配置、数据库和流程，限制同一数据目录的写进程          | 运行参数和各阶段连接是否正确                |
| `inputs.py`    | 读取 Excel 仓库名单、校验 owner/repo 格式并标记重复行；读取 GitHub token                              | Excel 有没有漏读、重复仓库怎么处理          |
| `github.py`    | GitHub REST/GraphQL 请求、分页、缓存、重试、限流、认证异常等                                          | 原始 PR 和评论有没有因分页或失败而漏掉      |
| `storage.py`   | 管理 SQLite：保存元信息、API 响应、实体、任务和摘要                                                   | 断点恢复及数据关联是否一致                  |
| `collect.py`   | 扫描仓库和 PR，获取 PR 详情、提交、文件、reviews、评论、线程及历史事件；协调采集任务                  | 收集对象、历史信息和原始评论是否正确        |
| `revisions.py` | 判断代码文件和机器人；将评论归成根线程，选择目标 revision；解析 diff 并校验评论位置；记录后续改动证据 | 目标 SHA 是否选对，线程归组和行号是否对齐   |
| `material.py`  | 获取固定版本材料，验证完整 diff；API 材料不足时用仓库归档和本地 Git 重建，并验证源码树                | diff 是否完整、是否确实属于这两个 SHA       |
| `build.py`     | 从缓存离线构造和导出 PR 样本，记录纳入/排除原因、失败、统计与 manifest                                | samples.json 是否忠实反映原始采集与构造规则 |

这层主要负责 **正确收集和对齐材料**。LLM 判断一条评论是否有技术价值，主要发生在下一层。

## 7. scripts：LLM 标注流程的管理代码

| 文件                               | 用途                                                                                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `prepare_thread_pilot.py`        | 从原始数据和缓存准备单线程输入，含 PR、source/target、当前线程及回复、代码和相邻线程。虽叫 pilot，也支持`--all` 全量准备，并可复用输入摘要一致的试运行结果 |
| `annotation_queue.py`            | 用独立 SQLite 队列管理领取、提交、租约、失败重试和恢复，避免多名 worker 重复处理一个线程                                                                     |
| `assemble_thread_annotations.py` | 读取逐线程模型输出，验证输入摘要、线程标识、类别、证据评论 ID 与位置，生成线程判断、可定位候选、待核查项和统计                                               |
| `build_pr_candidates.py`         | 将原始 PR 与线程标注关联，形成每个 PR 的候选意见集合，并输出 CSV、统计、报告和来源 manifest                                                                  |

这些脚本不直接替代模型推理。包内文档记录模型由 Codex worker 执行，Python 脚本负责准备和管理材料。**格式、ID、位置校验通过，只表示结构一致，不能证明意见在技术上成立。**

## 8. data/state.sqlite3：原始材料的大仓库

| 文件                  | 用途                                                              |
| --------------------- | ----------------------------------------------------------------- |
| `state.sqlite3`     | SQLite 主数据库；源码定义 meta、responses、entities、tasks 四类表 |
| `state.sqlite3-wal` | WAL 事务日志，存放尚未合并回主库的事务内容；本包中大小为 0        |
| `state.sqlite3-shm` | WAL 模式的共享协调文件                                            |
| `.writer.lock`      | 防止多个采集/构造进程同时写入同一数据目录的锁文件                 |

四类表分别保存：

- `meta`：仓库输入、截止时间、配置和运行元信息。
- `responses`：按页缓存的 API 响应、部分响应头和抓取时间。
- `entities`：按类型、仓库和 ID 保存的 PR、评论、提交、构造材料等 JSON。
- `tasks`：每个采集或构造任务的完成、失败、待恢复状态。

当你发现 `samples.json` 中一条记录可疑时，原始数据库是追溯来源的重要材料。数据库用途由源码和文档确认；本次没有解出并逐表审计这个大文件。

## 9. data/diffs 与 archives：实际代码材料

| 路径模式                                               | 用途                                                                                                     |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `diffs/<owner>/<repo>/<sourceSHA>..<targetSHA>.diff` | 保存这两个固定版本之间的代码改动；包含文件路径、hunk、增删行等，用来核对 B→R 的内容和评论位置           |
| `archives/<owner>/<repo>/<SHA>.tar.gz`               | 一个仓库在一个固定提交版本的源码快照，用于 API diff 不完整时重建材料；同样是压缩包，不是已经展开的源码树 |

完整包中有 15,297 个 diff 和 2,353 个仓库归档。缓存文件数量不等于导出样本数量：是否进入最终 samples 由构造和导出阶段决定。

## 10. data/dataset：原始导出数据的六个文件

| 文件                         | 用途                                                                                                            |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `samples.json`             | 最核心的原始 PR 数据集：10,727 个 PR，含仓库、PR、source/target SHA、原始审查评论与位置、线程和 diff 等关联信息 |
| `manifest.json`            | 数据来源、输入摘要、参考版本、截止时间、采集规则及完整性状态；本包`complete=false`                            |
| `report.json`              | 按仓库及原因汇总采集、导出、排除、失败等情况                                                                    |
| `decisions.json`           | 数据构造过程的 PR 纳入/排除决定与原因；**不是 LLM 的三分类标签**                                          |
| `alignment_failures.json`  | 评论不能可靠对应到所选版本和行号的记录，方便检查定位失败                                                        |
| `unavailable_history.json` | 无法取得或恢复的历史提交/材料记录，解释一些 PR 为什么不能完成构造                                               |

这里的 `samples.json` 是 **原始评论语料**。原始导出阶段不执行语义筛选、AI 补充或缺陷确认。后续 LLM 标注单独保存，没有直接覆盖原始评论。

## 11. data/annotation：LLM 看了什么、输出了什么

### 11.1 两次运行

- `pilot-200-20260926/`：先做 200 个线程试运行。包括 150 个均匀随机线程和 50 个定向复杂线程。
- `full-20260926/`：处理全部 34,822 个已导出线程，包含 34,822 个 inputs 和同数 results。
- 外层 `pilot-200-0050.json.tmp` 等六个文件：试运行过程留下的临时 JSON 文件，不是正式最终汇总。

日期后缀是运行批次标识，不意味着其中每个文件都在当天最后更新。

### 11.2 通用文件与子目录

| 文件/目录                     | 用途                                                                               |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| `inputs/<编号>.json`        | 模型实际收到的单线程材料，含当前评论及回复、代码上下文和必要的相邻线程             |
| `results/<同编号>.json`     | 对应输入的模型判断，包含 decision、理由、证据评论 ID、提炼出的问题、候选类别和位置 |
| `assignments/worker-*.json` | 逻辑任务分配清单；worker 文件数量不自动等于实际同时运行的模型数量                  |
| `manifest.json`             | 输入索引、摘要、模型、范围、抽样或全量规则，以及任务列表                           |
| `execution.json`            | 执行配置与记录：模型、并发、队列、复用、修复和人工验收状态等                       |
| `thread_assessments.jsonl`  | 通过结构校验的逐线程判断汇总，每行一条记录；是检查 LLM 标签的主要索引              |
| `candidate_issues.jsonl`    | 具有通过校验的位置的候选意见，可一线程多意见；未定位候选不进入此文件               |
| `needs_review.jsonl`        | 上下文不足、未定位候选，以及在相应运行状态下的无效或缺失结果等待核查记录           |
| `report.json`               | 分类完成度、decision 数量、候选数量和校验统计                                      |

JSON 是一份结构化对象或数组；JSONL 则是一行一个 JSON 对象，适合较大的记录集合。CSV 是可用 Excel 打开的表格。

### 11.3 全量目录额外文件

| 文件/目录                      | 用途                                                                                             |
| ------------------------------ | ------------------------------------------------------------------------------------------------ |
| `WORKER.md`                  | 给分类 worker 的操作和输出协议                                                                   |
| `queue.sqlite3`              | 正式标注任务队列，管理待处理、运行、完成和失败状态；与原始采集`state.sqlite3` 是两个不同数据库 |
| `queue.db`、`queue.sqlite` | 本包中两个 0 字节文件，不能当作正式队列数据库；不从空文件推断其形成原因                          |
| `feed_queue.py`              | 输入持续生成时，将新增任务增量导入队列                                                           |
| `watch_run.py`               | 定期记录进度；输出全部生成后触发汇总校验                                                         |
| `prepare.log`                | 输入准备日志                                                                                     |
| `feed.log`                   | 队列导入日志                                                                                     |
| `watch.log`                  | 监测日志；本包中为空                                                                             |
| `status.json`                | 某次记录的任务进度与校验状态                                                                     |
| `supervisor_status.json`     | 编排监督过程的状态快照；可能早于最终修复结果                                                     |
| `supervisor_events.jsonl`    | 编排监督事件记录                                                                                 |
| `progress_reports.jsonl`     | 多次进度报告的历史记录                                                                           |
| `outputs/`                   | 本包中为空；实际逐线程结果在`results/`                                                         |
| `repair-20260929/`           | 首轮无效标注修复的留档，见下一节                                                                 |

过程日志和旧状态快照不一定反映最终状态。最终含义要结合 `report.json`、`execution.json` 和修复记录判断。

### 11.4 200 线程试运行额外文件

| 文件/目录                          | 用途                                                |
| ---------------------------------- | --------------------------------------------------- |
| `README.md`                      | 试运行结果与逐条说明                                |
| `review_table.csv`               | 便于查看和逐条核对的表格                            |
| `output-sha256.json`             | 输出汇总文件的摘要记录                              |
| `initial_results/<编号>.json`    | 七个被修改样本的初始结果备份，供与最终 results 比较 |
| `reviews/spot-review-*.json`     | 模型抽查/复核记录；不等于人工专家验收               |
| `reviews/check-*-tasks.json`     | 复核任务材料或分配记录                              |
| `reviews/applied-revisions.json` | 复核后实际应用的修改记录                            |
| `reviews/summary.json`           | 复核汇总                                            |

### 11.5 三种 LLM decision 和四种 category

| 字段取值                        | 这里的意思                                                                               |
| ------------------------------- | ---------------------------------------------------------------------------------------- |
| `candidate_issue`             | 这个线程提出了有材料支持的具体问题或改进建议；包含维护性、可读性等建议，不保证是功能 bug |
| `no_issue`                    | 这个线程没有可保留的具体诉求，或质疑已被解释清楚；不表示整个 PR 没有缺陷                 |
| `needs_context`               | 材料不足、指代不明或有争议，需要补充背景                                                 |
| `code_defect`                 | 候选功能/正确性问题                                                                      |
| `security`                    | 候选安全问题                                                                             |
| `performance`                 | 候选性能问题                                                                             |
| `maintainability_readability` | 候选维护性、可读性、格式或注释建议                                                       |

模型判断的是“已有线程能否提炼出候选审查意见”。这是构建参考答案时的预处理标签，还不是评测被测模型的得分。

## 12. repair-20260929：修复了哪些模型输出

包内说明记录了 633 份首轮无效结果的修复。这个数字是历史记录，不代表本次重新人工验证了 633 个意见。

| 文件/目录                                                        | 用途                                                                                                   |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `README.md`                                                    | 修复范围、方式、最终状态和限制                                                                         |
| `scope.json`                                                   | 本轮修复范围                                                                                           |
| `summary.json`                                                 | 修复数量、类别和最终汇总摘要                                                                           |
| `initial_invalid.json`                                         | 修复开始时的无效条目与原因                                                                             |
| `repairs.jsonl`                                                | 633 条逐项修复记录，保留原因、字段变化和前后摘要                                                       |
| `review_packets.json`                                          | 无效样本的输入、原输出及错误信息快照                                                                   |
| `repair_groups.json`                                           | 分批修复的分组清单                                                                                     |
| `original_results/<编号>.json`                                 | 633 份修改前模型输出                                                                                   |
| `original_aggregates/`                                         | 修改前 thread_assessments、candidate_issues、needs_review、report、status、execution 六份汇总/状态备份 |
| `queue-before-validation.sqlite3`                              | 结束延后校验前的队列数据库备份                                                                         |
| `queue-validation.json`                                        | 队列独立校验的结果记录                                                                                 |
| `validation-deferred.before`                                   | 原延后校验状态的留档标记，0 字节                                                                       |
| `execution_scripts/edabench_repair.py`                         | 本轮临时修复脚本留档                                                                                   |
| `execution_scripts/edabench_repair_batch1.py` 至 `batch4.py` | 四批修复的执行脚本留档                                                                                 |
| `execution_scripts/edabench_assemble_cached.py`                | 使用预读材料重建汇总的执行脚本留档                                                                     |
| `execution_scripts/edabench_finalize_queue.py`                 | 最终队列校验/同步脚本留档                                                                              |

这些 execution_scripts 是历史执行材料，包内说明明确它们不是常规续跑入口。修复和模型复核不等于人工专家确认。

## 13. data/pr-candidates：最方便你开始看的五个文件

位置：`data/pr-candidates/full-20260926/`。

| 文件                    | 用途                                                                                                     |
| ----------------------- | -------------------------------------------------------------------------------------------------------- |
| `pr_candidates.jsonl` | 每行一个 PR revision，包含全部线程判断、候选问题、理由、位置、证据 ID 和来源；保留零候选 PR              |
| `pr_summary.csv`      | 每个 PR 一行的轻量表：PR 链接、source/target、改动行数、文件数、线程数、候选数量等；适合挑选人工检查样本 |
| `statistics.json`     | 仓库、主语言、后缀、候选类别、LOC、每 PR 意见数等完整统计                                                |
| `report.md`           | 上述统计的可读版，适合先快速认识数据规模                                                                 |
| `manifest.json`       | 本次聚合所用原始样本、线程标注、修复记录、脚本和输出的来源及摘要                                         |

本包记录：10,727 个 PR、34,822 个线程、67,556 条原始评论；8,680 个 PR 有候选意见，8,594 个 PR 有可定位候选意见；总计 26,512 条候选意见，其中 24,497 条可定位，2,015 条未定位。

`human_verified=false` 表示候选尚未经人工验收。`location_status=verified` 的 verified 表示位置通过校验，**不表示技术结论已经被专家确认**。

## 14. data/audit：包内已有的十例检查

位置：`data/audit/random-10-20260926/`。

| 文件                                     | 用途                       |
| ---------------------------------------- | -------------------------- |
| `README.md`                            | 这次十例抽查的说明与结果   |
| `manifest.json`                        | 抽样和来源信息             |
| `samples.json`                         | 被抽中的十个 PR 样本       |
| `item-01.json` 至 `item-10.json`     | 分别保存每个样本的检查材料 |
| `checks.json`                          | 检查项目及结果汇总         |
| `review-01-05.md`、`review-06-10.md` | 两批样本的审阅说明         |

这些记录原本就在学长发来的包里，不是本次新增的独立人工检查，不能据此宣布已经完成学长要求的抽查。

## 15. data 根目录的脚本、日志和状态文件

| 文件                              | 用途                                                                                                               |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `index_worker.py`               | 历史索引采集入口：先用小仓库检查采集接口，再扫描名单仓库                                                           |
| `watch_space.py`                | 原运行环境的磁盘空间保护脚本，低于阈值时向采集进程发送正常中断信号；使用 Linux`/proc`，不应当成 Windows 通用入口 |
| `full-run.json`                 | 某轮全量采集的启动参数、时间、进程和日志信息                                                                       |
| `full-run.log`                  | 全量采集的详细运行日志                                                                                             |
| `index.log`                     | 索引阶段日志                                                                                                       |
| `pre-speedup.json`              | 提速改动前的状态快照                                                                                               |
| `speedup-smoke.log`             | 提速后的小规模验证运行日志                                                                                         |
| `smoke.log`                     | 早期小规模运行日志                                                                                                 |
| `smoke-history.log`             | 历史材料相关的小规模运行日志                                                                                       |
| `smoke-final.log`               | 以该批次命名的小规模运行日志                                                                                       |
| `smoke-additional.log`          | 补充小规模运行日志                                                                                                 |
| `rebuild-after-fix.log`         | 修复后重新构建导出的日志                                                                                           |
| `openroad-archive-cleanup.json` | 历史 OpenROAD 归档缓存清理清单和结果                                                                               |

日志名只说明运行用途，不自动证明测试通过；若要评价正确性，需要读取内容并核对实际产物。

## 16. tests：各测试文件检查什么

| 文件                            | 测试覆盖的功能                                                               |
| ------------------------------- | ---------------------------------------------------------------------------- |
| `test_client.py`              | API 分页、缓存恢复、重试、认证、额度节奏、并发上限和 Excel 输入              |
| `test_collect.py`             | GraphQL 嵌套分页、接口数量上限、采集与材料构造流水线、取消/失败/恢复         |
| `test_material.py`            | 完整 diff、仓库树校验、归档回退、不可用历史、异常归档和临时文件清理          |
| `test_revisions.py`           | 线程投票、机器人、过时/多行/重命名评论位置、旧式位置、源码规则和后续改动证据 |
| `test_build.py`               | 导出结构、完整性、纯文档排除和离线重复构建稳定性                             |
| `test_annotation_prepare.py`  | 随机/复杂抽样、全量输入、恢复和试运行结果复用                                |
| `test_annotation_assembly.py` | 无效证据、编造位置、摘要不符、缺失结果和汇总分组等                           |
| `test_annotation_queue.py`    | 并发领取、任务租约、恢复、失败重试、延后校验与提交后领取                     |
| `test_pr_candidates.py`       | PR 与标注的关联、零候选、多意见、未定位、统计、来源一致性和导出可重复性      |

有测试文件说明作者设计了这些检查，不意味着本次已重跑或所有数据的语义已验证。

## 17. reference：论文和 AACR 官方参考项目

### 17.1 来源文件

| 文件                   | 用途                                                  |
| ---------------------- | ----------------------------------------------------- |
| `2601.19494v3.pdf`   | AACR-Bench 论文 PDF                                   |
| `aacr-source.json`   | 官方 GitHub 仓库、固定参考 commit、下载地址和归档摘要 |
| `input-sources.json` | PPT、Excel、论文的来源路径、字节数和摘要              |

### 17.2 aacr-bench 子目录

这是下载保存的官方参考项目，**不应把这里的官方评测代码误认为已经在 EDA 数据上跑出了评测结果**。

| 文件/目录                                                                | 用途                                             |
| ------------------------------------------------------------------------ | ------------------------------------------------ |
| `README.md`、`README.zh-CN.md`                                       | AACR 官方项目介绍                                |
| `dataset/positive_samples.json`                                        | 官方正样本数据                                   |
| `dataset/negative_samples.json`                                        | 官方负样本数据                                   |
| `docs/metrics.md`、`docs/zh/metrics.md`                              | 官方评测指标说明                                 |
| `evaluation/README.md`、`README.zh-CN.md`                            | 官方评测流水线的操作说明                         |
| `evaluation/pipeline.py`                                               | 官方评测的流程编排                               |
| `evaluation/evaluate.py`                                               | 官方评测命令入口                                 |
| `evaluation/judge.py`                                                  | 模型审查意见与参考意见的判定逻辑                 |
| `evaluation/schema.py`                                                 | 评测输入、发现和结果等数据结构                   |
| `evaluation/config.py`                                                 | 官方评测配置的读取与管理                         |
| `evaluation/repo_utils.py`                                             | 为评测准备仓库版本和上下文的工具                 |
| `evaluation/converters/aacr_bench.py`                                  | 将 AACR 原始数据转换成评测格式                   |
| `evaluation/reviewers/codex.py`、`claude.py`、`ocr.py`             | 不同代码审查系统的适配器                         |
| `evaluation/mcp_finding_server.py`、`mcp_codex_finding_server.py`    | 为评测中的 agent 提供结构化发现提交接口          |
| `evaluation/hooks/on_stop_failure.py`                                  | 停止/失败场景的处理钩子                          |
| `evaluation/benchmark/AACR-Bench/positive_samples.meta.json`           | 转换评测数据的元信息                             |
| `evaluation/pyproject.toml`、`requirements.txt`、`.python-version` | 官方评测环境的依赖及 Python 版本配置             |
| `evaluation/.env.example`                                              | 官方环境变量配置示例                             |
| 各级`__init__.py`                                                      | Python 包初始化文件                              |
| `imgs/*.png`、`*.jpg`                                                | 文档插图，展示类别、上下文、评论分布和方法概览等 |
| `CONTRIBUTING.md`、`CONTRIBUTING.zh-CN.md`                           | 贡献说明                                         |
| `CONTRIBUTORS.md`                                                      | 贡献者名单                                       |
| `LICENSE`                                                              | 开源许可                                         |
| `.gitignore`、`evaluation/.gitignore`                                | 官方参考项目的忽略规则                           |
| `evaluation/.gitattributes`                                            | Git 对文件属性的配置                             |

## 18. 缓存、版本历史和空目录

| 路径                                                          | 用途                                                                                                |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `.git/`                                                     | 这个数据采集项目自己的版本历史，包括对象、分支指针、日志、索引和钩子示例；不是所采集仓库的 API 数据 |
| `__pycache__/*.pyc`                                         | Python 自动生成的字节码缓存；与同名`.py` 对应，不是另一份核心实现                                 |
| `.pytest_cache/v/cache/nodeids`                             | pytest 记录的测试标识                                                                               |
| `.pytest_cache/v/cache/lastfailed`                          | pytest 记录的上次失败项                                                                             |
| `.pytest_cache/README.md`、`CACHEDIR.TAG`、`.gitignore` | 测试缓存说明和标记                                                                                  |
| `results/`                                                  | 项目根目录下的空目录；本包没有放置 EDA 被测模型评测得分                                             |

## 19. 下载外层文件：哪些是这次下载产生的

以下文件位于本地 `data/edabench_initial_2026-10-05/`，不属于原项目实现。

| 文件/目录                                 | 用途                                                                     |
| ----------------------------------------- | ------------------------------------------------------------------------ |
| `edabench.tar.gz`                       | 学长分享的原始项目包                                                     |
| `edabench.tar.gz.sha256`                | 本地下载文件的 SHA-256 摘要；是本地完整性记录，不是独立提供方签名        |
| `source_metadata.json`                  | 来源链接、预期大小及当时分析状态；其中停止分析字段记录的是此前的指令状态 |
| `download_status.json`                  | 下载最终状态，目前为 complete                                            |
| `download.log`、`download_errors.log` | 下载进度与错误日志；错误日志为空                                         |
| `download.pid`                          | 当时后台下载进程的编号记录，不能据此认为该进程仍在运行                   |
| `download_archive.py`                   | 分块下载、验证响应范围、合并压缩包和计算摘要的辅助程序                   |
| `download_page.html`                    | 获取大文件公开下载入口时保存的网页                                       |
| `probe_download.py`                     | 检查公开链接是否支持按范围下载                                           |
| `probe_headers.txt`                     | 探测时的 HTTP 响应头，属于下载排查材料                                   |
| `probe.bin`                             | 16 字节的下载探测内容                                                    |
| `preview/`                              | 下载尚未完成时形成的早期预览文件；配置预览已脱敏                         |
| `extracted/`                            | 选择性解出的阅读材料；并非全部项目                                       |
| `inspect_archive_prefix.py`             | 当时从已下载前缀读取少量目录/源码的辅助程序                              |
| `extract_audit_inputs.py`               | 当时提取原始导出、已有十例检查与候选汇总的辅助程序                       |
| `scan_archive_prefix.py`                | 当时扫描下载前缀并核对相关 diff 摘要的辅助程序                           |
| `archive_prefix_manifest.json`          | 下载未完成时的前缀目录记录，不能作为完整目录清单                         |
| `extraction_selection.json`             | 当时选择性提取的文件清单                                                 |
| `diff_hash_checks.json`                 | 当时对关联 diff 的摘要核对记录；摘要一致不代表代码意见正确               |
| `inventory_project.py`                  | 本次完整目录扫描与选择性解出阅读材料的辅助程序                           |
| `archive_inventory.json`                | 本次完整压缩包目录清单：路径、类型和大小                                 |
| `build_file_catalog.py`                 | 本次生成逐文件职责清单的辅助程序                                         |
| `project_file_catalog.csv`              | 本次生成的 88,767 行完整文件清单，含路径、大小、用途和解释依据           |

## 20. 你接下来检查一个 case，可以沿这条链找文件

1. 在 `pr_summary.csv` 找到一个 PR，记下仓库、PR 编号、source SHA 和 target SHA。
2. 在 `pr_candidates.jsonl` 找到该 PR，查看每个线程的 decision、reason、issue 和来源记录。
3. 根据 provenance 找对应 `annotation/full-20260926/inputs/<编号>.json` 和 `results/<编号>.json`，比较模型读到的材料与输出。
4. 在 `dataset/samples.json` 核对原始评论、线程和所选版本；需要更原始材料时查 `state.sqlite3`。
5. 打开对应 `diffs/<owner>/<repo>/<source>..<target>.diff`，核对文件、改动和行号。
6. 如果该结果被修复过，对照 `repair-20260929/repairs.jsonl` 和 `original_results/` 看前后变化。
7. 对照 `docs/thread-annotation.md` 判断标签是否符合项目的既定口径，再判断这套口径与你要复现的 AACR 方法有哪些差异。

这条链分别支持两种检查：**材料是否收集、关联正确**，以及 **LLM 是否正确理解评论**。技术意见是否真的成立，还需阅读足够代码背景或做进一步验证。

本次只完成目录职责梳理，没有执行包内程序、重新采集 GitHub、调用标注模型或完成新的人工 case 审查。
