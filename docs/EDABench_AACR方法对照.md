# EDABench 与 AACR-Bench 方法对照

日期：2026-10-06（Asia/Shanghai）；本批：20261006_b；范围：交接阶段 D。执行者为 LLM，`human_verified=false`。阶段 A/B/C 的独立核查继续引用 20261005_a 的原始证据，没有改写原代码、评论、标注或旧报告。

**EDABench 已建立可追溯的 PR、审查版本、完整 diff 和已有讨论的 LLM 候选整理链路；它尚未完成 AACR-Bench 的新问题补充、语义去重、真人专家金标准和 reviewer/judge 评测流程。** 原始格式相近、分类名称相同，只能说明部分环节对应。仓库选取、PR 筛选和版本计票存在明确的项目自定义规则。

## 来源与核查范围

本次读取了 [论文 v3][paper-web] 的方法、附录和评测提示，重点为 PDF 第 3–5、12–18、25–29 页；提取全部 41 页文本，并渲染检查第 3、4、15、17、18 页。完整 [本地 PDF][paper]、逐页文本和图片保存在独立批次中。页码均为 PDF/正文的同号页码。

固定官方参考 commit 为 [`68a569759289a83654a59d06db2a72910edf0a4a`][official-web]。安全提取 38 个参考文件，排除图片和环境示例；对官方 schema、converter、repo、pipeline、reviewer 输入构造、judge 和指标代码作静态检查。未运行其中的采集、转换、reviewer 或评测入口，未调用被测模型或 judge。

通过公开固定 commit 的 codeload 归档独立核对，已提取的官方仓库文件逐一字节一致，下载包 SHA-256 与原来源记录一致：`7eeab15e44a046dbd3b86921e2067dec570584b91109764f5459ab73a7bd3aa7`。公开 arXiv v3 PDF 与本地 PDF 字节一致，SHA-256 为 `adc40e7877b2d478a69c12c1729f80a4c5e4eb9ff846a014e70e9eb2b86a6528`。见 [代码来源核对][source-check]、[论文来源核对][paper-check]。GitHub 无认证 API 曾返回 403 限流，随后采用公开归档验证；没有读取或使用归档中的 GitHub 凭据。

依据分成三个层次：**论文描述的方法、固定官方工具实际支持的行为、EDA 包中实际完成的产物**。论文的真人标注和正确率描述是作者报告，本次没有独立验收其全部金标准；官方工具支持某阶段，也不能作为 EDABench 已执行的证明。

## 先校正参考数据的计数口径

独立解析固定版的两个 dataset JSON 文件，得到以下计数，见 [官方数据计数及摘要][official-data]。

| 项目 | 论文 v3 | 固定版实际文件 |
|---|---:|---:|
| 核心 PR | 200 | positive 文件 196；negative 文件 155；并集 200、交集 151 |
| 有效参考意见 | 1,505 | positive 文件 1,506 |
| 原讨论增强 / AI 新生成的有效意见 | 391 / 1,114 | positive 的 is_ai_comment=false/true 为 392 / 1,114 |
| 四类别：缺陷 / 维护 / 性能 / 安全 | 709 / 626 / 117 / 53 | positive 为 710 / 626 / 117 / 53 |
| 所需上下文：Diff / File / Repo | 754 / 518 / 233 | positive 为 754 / 518 / 234 |
| 另一个文件中的意见 | 未用于上述 1,505 分母 | negative 文件 639；两文件意见合计 2,145 |

因此，固定版数据与论文有效集相差一条，变化落在非 AI、code defect、repo context 的计数上；本次不能确定增减原因或变更时间，不擅自删除这一条。README 的 2,145 与两文件总量相符，不能拿它替代有效集分母。README 的语言列表出现 Ruby；论文及两个实际文件的主语言为 C 等十种，没有 Ruby，方法对照采用论文和实际字段。

正负文件在 PR 上大量重叠，**不是训练/测试拆分，也不是互斥的“有缺陷 PR / 无缺陷 PR”集合**。本项目的 `no_issue` 是线程判断，零候选 PR 也不能直接当作 clean PR 负样本。

论文另有一处筛选阈值不一致：第 4 页写 inline comments `>2`，第 15 页写至少两条。报告保留这个歧义；若严格重建论文采样，应先明确采用哪一口径。

## 逐项对照

下表“已对应”只针对列出的环节和证据，不表示完整复现或真人验收。“未实现”包括本项目明确未做、也没有实际产物的阶段；“证据不足”表示无法由现有材料证明。每行均给出论文/固定实现、EDA 位置、实际证据、差异、影响和建议。

### 来源、版本、材料与候选构造

| 编号 / 环节 / 判断 | 论文与固定实现依据 | EDA 实现位置与实际证据 | 差异及影响 | 建议 |
|---|---|---|---|---|
| D01 仓库来源：自定义差异 | [p4 §3.2][P4]、[p12 B.1][P12]：十语言，每语言按新增 stars/closed PR 活跃度候选选五仓库，共 50。 | [method:5–7][E-method]、[inputs:8][E-input]；Excel 44 行输入，实际贡献 34 仓库，[EDA 计数][eda-data]。 | EDA 采用课题仓库名单，非论文活跃度/语言配额采样；这是研究范围调整，不是采集错误。 | 冻结 EDA 仓库纳入标准，记录 RTL、EDA 工具、验证/构建代码各自覆盖。 |
| D02 时间范围：自定义差异 | [p12–13 B.1][P12]：2024-12-01 至 2025-12-01 的来源窗口。 | [collect:87][E-collect]、[method:32][E-method-time]；截止 2026-09-21，8,271 个 PR 的 closed_at 早于 2024-12-01，[EDA 计数][eda-data]。 | 广泛历史 PR 与论文近期窗口不同；API 字段仍是请求时观察值，不能声称截止时刻事务快照。 | 记录 created/closed/review/observed 时间；按时间分层，独立说明模型训练污染风险。 |
| D03 PR 纳入过滤：自定义差异 | [p4][P4]、[p15][P15]：英文、LOC≤1,000、主语言一致、足够 inline、至少一条导致修改的意见、语义有效。两处 inline 阈值有歧义。 | [build:18][E-build]、[method:74][E-code-policy]；保留含代码改动且有可靠锚点的 closed PR；1,049 个 LOC>1,000，1,056 个未合并 PR，[EDA 计数][eda-data]。 | 不要求英文、LOC 上限或采纳；HDL/构建/约束文件属于项目代码政策。规模不能直接与论文筛后 200 PR 比质量。 | 建立可选严格子集和 EDA 扩展子集；冻结尺寸、语义、采纳证据规则，禁止仅凭 Done 判采纳。 |
| D04 分层与均衡：未实现 | [p13][P13] Table 6、[p15][P15]：按仓库、问题域、改动尺寸分层至 200 PR。 | [PR 聚合:186][E-aggregate] 保存总体，不重采样；OpenTitan 6,153/10,727=57.36%，[EDA 计数][eda-data]。 | 已有总体不具备论文分层设计；大仓库对总体指标影响大。 | 最终评测集按仓库/代码种类/尺寸分层，同时报告仓库宏平均和总体统计。 |
| D05 审查版本 R2：自定义差异 | [p4][P4]、[p13][P13]：每 PR 选 inline 评论最多的 revision；固定 converter 只消费已给定 SHA，[converter:169][A-convert]。 | [revisions:30–60][E-revision]：每个含非 bot 的独立根线程一票，回复继承根 SHA，平票按最早根时间再 SHA。15 例独立重算一致，[前批材料核对][prior-material]。 | 评论数与根线程数是不同权重，选出的版本不保证相同；不能称严格照搬论文。论文未给出可验证的完整计票/平票实现。 | 保留当前防止长回复放大权重的理由；若需比较，另算评论权重版本并留差异，不覆盖现有 R2。 |
| D06 B/R2 与完整 diff：已对应 | [p18 C.1][P18]：固定 base/target，提取所有 hunks；[repo:120][A-repo-prepare] 准备这两个 commit。 | [method:51–72][E-baseline]、[material:259][E-material]；固定 SHA、merge-base/事件/hunk 验证；15 个 diff 独立摘要和解析一致，[前批材料核对][prior-material]。 | 核心版本关联对应；EDA 明确记录历史恢复边界。没有独立恢复所有 Git 历史，不能证明全部历史基线正确。 | 保留 baseline_method、原始事件和 diff 摘要；历史无法重建者继续隔离。 |
| D07 完整仓库上下文：证据不足 | [p18][P18]：完整仓库、target 代码索引；[repo:47–74][A-repo] clone/fetch 并确保 commit。 | [method:66–69][E-archive] 明示构造后释放部分归档。完整 inventory 核对：双快照 808、仅 B 229、仅 R2 176、均无 9,514，[逐 PR 覆盖表][archive-coverage]。 | 只有 984 PR 保存 R2 包；9,743 缺 R2 包。808 是归档存在性计数，未逐一验证树/依赖，不是“808 已可评测”。可用 diff 不等于已有整仓上下文。 | 对计划进入评测的 PR 恢复并验证 B/R2 文件树、模式、gitlinks 与依赖；暂不可恢复者只用于明确受限的语料用途。 |
| D08 评论定位与空位置：自定义差异 | [p18][P18] 要求片段和 left/right；固定 positive 的 1,506 条均非 null，含 8 条 left，[官方计数][official-data]。 | [method:44–49][E-location] 保留无法证实的位置为 null；原始评论 1,711 条 left、6,617 条有 null 端点；候选 issue 未定位 2,015，[EDA 计数][eda-data]、[聚合统计][eda-boundary]。 | 正确保留 unknown 有利于追溯，但并非都能进入行号匹配；评论与 issue 分母不同。15 例 30 根可定位、7 根 null 均核对一致。 | 将未定位候选留在待核查集，另定义文本级评估；禁止造行号或混入行号准确率。 |
| D09 已有讨论提炼：已对应 | [p15–16][P15]、Fig8：读多轮线程，去噪、增强原意见；同线程多个问题分别提炼。 | [rubric:12–19][E-rubric]、[packet:68][E-packet]：完整当前线程、原 hunk、文件 patch、窗口、四同文件邻居；34,822 输入/结果结构检查通过，[前批全量检查][prior-full]。 | 对应已有意见整理这一阶段；语义正确性仍需确认。最近四同文件邻居会遗漏跨文件引用，case-07 已给出具体证据，[15例报告][prior-cases]。 | 增加显式评论链接解析与固定 SHA 上下文；优先处理缺背景和有争议线程。 |
| D10 AI 新问题补充：未实现 | [p4][P4]、[p17][P17]：六模型、内部审查/Claude Code 两框架补充新问题；论文有效新意见 1,114。 | [full-run:9][E-full] 明确不增加新问题；当前候选均来源已有线程，[全量说明][E-full]、[聚合统计][eda-boundary]。 | 26,512 个候选 issue 不是模型独立发现的新问题；没有论文扩展覆盖的阶段。 | 金标准建设时另行生成、验证新问题，并保留模型/框架/版本来源；不得把“首轮整理模型”计为 reviewer 实验。 |
| D11 跨线程语义去重：未实现 | [p17][P17]：按仓库/PR/文件/hunk 分组、两两语义判断、五次判断投票。 | [PR 聚合:186][E-aggregate] 是关联和汇总；case-05 根 305632253/305632267 的 core/hart 建议同义，[15例报告][prior-cases]。 | 线程一对一汇总没有完成语义去重。重复参考会改变 Recall 分母和一对一匹配结果。 | 在 PR 级生成去重 issue_id，保留全部来源 root IDs，合并需审阅，不能直接丢原线程。 |
| D12 真人专家及一致性：未实现 | [p4][P4]、[p17][P17]：80 余专业工程师、每意见至少两人独立、双盲轮次、六人核心争议裁决。 | [full-run:32][E-full-human] 和前批 [audit_summary][prior-summary] 均 human_verified=false；首轮 gpt-5.6-luna/max，后续修复为 Codex 复核。 | 原输出、程序验证、再次 LLM 审阅均没有完成真人专家验收；不能继承论文质量声明或 95% 增强准确率。 | 建立实名/匿名可追溯的独立双标、专家资质与冲突裁决记录；报告一致性、裁决量和剩余 unknown。 |
| D13 四类候选政策：自定义差异 | [p17][P17] Table 7 包含维护/可读性；[p25–29][P25] 非 Agent/Agent 提示对风格意见限制有所不同。 | [rubric:12,46][E-rubric] 包含格式/注释、不要求功能 bug；全量 20,415/26,512 为维护/可读性，[前批全量检查][prior-full]。 | 四类名称对应，技术门槛和运行角色不完全相同。不能因 AACR 有 code defect 就把全部维护建议排除，也不能把全部候选叫功能缺陷。 | 分清功能缺陷、设计维护、纯风格/格式；按可操作性和项目规则作专家裁决，冻结评测纳入政策。 |
| D14 上下文需求标签：未实现 | [p3][P3] Table1、[p17][P17]：专家标注 Diff/File/Repo 所需上下文。 | 原 samples 的 67,556 条 context 均为空；逐线程候选 schema 只有类别/锚点/证据，不提供专家 context 标签，[EDA 计数][eda-data]、[rubric][E-rubric]。 | 无法复现按所需上下文深度分组的评测；“输入有邻居”不等于“已标上下文需求”。 | 在专家标注中独立记录最小充分上下文及理由，核对固定版本的依赖证据。 |

### 正负集、评测角色、匹配与泄漏控制

| 编号 / 环节 / 判断 | 论文与固定实现依据 | EDA 实现位置与实际证据 | 差异及影响 | 建议 |
|---|---|---|---|---|
| D15 正负与数据拆分：证据不足 | [p3][P3] 按 PR 评测；固定正负文件有 151 个共同 PR，[官方计数][official-data]；[converter:50][A-default] 默认读取 positive。未找到正式 train/test 方案。 | [PR 聚合][E-aggregate] 保留零候选 PR；candidate/no_issue/needs_context 是线程状态，[rubric][E-rubric]。 | 无 EDA 专家正负集或冻结拆分；不能用线程 no_issue/零候选 PR 证明整 PR 无缺陷。论文/固定代码也不提供可直接照抄的严格训练隔离证明。 | 区分“被否定的意见”和“评估为无有效问题的 PR”；若设开发/测试，按仓库及同代码版本组隔离，避免同一 B/R2 跨集。 |
| D16 导出格式与来源保存：已对应 | 固定 [converter:164–213][A-convert] 映射 PR URL、source/target、note、path、side/range 到 [schema:92][A-schema]。 | [method:85–88][E-format] 使用相同原始核心字段，额外 metadata 保留线程、diff、原评论和构造证据；10,727 个 PR 聚合重建一致，[前批聚合核对][prior-aggregate]。 | 原始字段可对接，但不代表 comments 已是金标准。固定 converter 会保留所有有 note/path 的评论，并丢 title/body、类别/context、原 provenance。 | 新建经过专家筛选的 gold 导出层；保留原始语料和来源侧表、扩展评测 schema，不直接转换原 samples 当参考答案。 |
| D17 PR 唯一标识：自定义差异 | [converter:172–176][A-convert-id] 使用 repo@head 前七位；[schema:193–220][A-schema-load] 拒绝重复 ID。 | EDA 以 repository/PR 关联；实际三对不同 PR 共用相同完整 B/R2，生成官方 ID 重复，[冲突六 PR][id-collisions]。 | 直接按官方规则接入会被 loader 拒绝。这里是同一版本复用，不是 SHA 短前缀偶然碰撞，也不说明原 PR 汇总错误。 | ID 加 PR 编号和完整 R2；在拆分/采样时把相同 B/R2 作为一个代码组，同时保留不同 PR 的讨论来源。 |
| D18 reviewer 与上下文实验：未实现 | [p5 §4.1][P5]：五被测模型，NoContext/BM25/Embedding(top3)/Claude Code Agent；[p18][P18] target 索引，所有模式提供 PR title/body。固定 [pipeline:366][A-pipeline] 暴露 OCR/Claude/Codex 三适配器，并非整套论文实验网格。 | [full-run][E-full] 是已有线程分类；包内 results 无文件、未记录 reviewer metrics，[执行边界][eda-boundary]。 | 分类模型与被测 reviewer 角色不同，当前没有 EDA reviewer 结果。固定 schema/三适配器也没有显式传 title/body；外部 OCR 能力未在此独立验证。 | 先定义一套可重复的 EDA 实验配置；若复现论文网格，补检索/提示/PR 元数据，冻结模型、温度、预算和工具版本。 |
| D19 judge 语义匹配：未实现 | [p17 Fig9][P17]、[p18][P18]：带 diff hunk 的语义比较，Qwen3-235B-A22B-Instruct-2507；去重用 Thinking 模型，二者角色不同。固定 [judge:24–100][A-judge] 可配置且允许 Mock。 | 没有 EDA judge 产物，[执行边界][eda-boundary]。 | 固定 prompt 只传两段意见，不传 hunk；缺 API key 自动用文本相似度 Mock。工具能出数字，不证明是论文 judge 结果。 | 真实评测显式禁止 Mock，记录 judge 精确模型/参数/提示与原始判定；以 hunk 和必要代码做语义复核。 |
| D20 side/行号匹配：未实现 | [p18][P18] 定义区间重叠。固定 [evaluate:118–176][A-eval-side] 将三个 reviewer 结果写为 right；[judge:201–211][A-judge-null] 遇 null 跳过行约束，默认 k=1。 | EDA 已保留 left、null 和多行锚点，[location 规则][E-location]、[EDA 计数][eda-data]；未执行匹配。 | LEFT 会遭 side 拒配；null 可记 line_match；相邻不重叠区间在 k=1 下可通过。这是参考工具移植风险，不是本次观察到的 EDA 得分错误。 | 正确保留/映射 side；null 单列；严格论文模式 k=0，并显式区分容差模式。固定计分前用真实 LEFT/null/多行案例核对。 |
| D21 指标与失败分母：未实现 | [p5][P5]、[p18][P18]：Precision/Recall/F1。固定 [evaluate:271–298][A-eval-metric] 按匹配/生成/参考总数计算；[344–361][A-eval-missing] 缺结果跳过，单列 missing。 | annotation classification_complete 是结构状态，不是评测指标；没有 reviewer/judge 分数，[执行边界][eda-boundary]。 | 分母未冻结、漏结果排除可能使不同系统不可比；参考不足会把新真问题误判未匹配。34/37 decision 一致也不能称模型准确率。 | 冻结参考集和评测 PR；报告完成率、失败/超时政策、重复处理、类别/context 分组，明确 micro/macro 指标及新增真问题裁决。 |
| D22 未来版本/参考泄漏：证据不足 | [p18][P18] target-only 检索；固定 [repo:47–74][A-repo] clone/fetch 全历史并 checkout R2。检查的三 reviewer 适配器没有显式把 reference_comments 放入 prompt，[OCR][A-ocr]、[Claude][A-claude]、[Codex][A-codex]。 | 当前 LLM 任务是读取已有讨论构造参考，允许看到澄清；[method:78–81][E-followup] 保存后续区域变化。尚无隔离的被测 reviewer 环境，[执行边界][eda-boundary]。 | 构造参考的视野与被测 reviewer 视野不同。checkout R2 不能证明 future refs/网络不可访问；论文/固定实现也未给出已验证的严格未来历史隔离。没有观察到实际评测泄漏，因为本项目尚未评测。 | 给 reviewer 独立 B/R2 工作区与允许的 PR 元数据，隔离原讨论/gold/修复/最终 head；限制未来 Git 对象和外部访问，保存可审计工具访问记录。 |

## 固定官方工具接入 EDA 前的具体核对

以上评测风险来自静态代码阅读及独立字段索引，没有运行官方评测。八项分支推演保存在 [reference_adapter_static_traces.json][adapter-traces]，源码片段和摘要保存在 [source_excerpts.json][excerpts]。例如：

- 参考位置为 null、生成意见在同文件第 900 行时，`judge.py:202` 不检查行号，后续分支可以记 `line_match=true`；语义是否相同仍取决于 judge，不能称已匹配。
- 参考区间 `[10,10]`、生成区间 `[11,11]` 在默认 k=1 下可通过，按论文区间重叠定义应不通过。
- 原 samples 中的感谢/Done 或未确认候选只要 note/path 非空，converter 就会纳入 reference_comments；它没有为 EDA 自动筛选 gold 的能力。

实际 ID 冲突为 OpenTitan #22459/#22460（`7a271fc…`）、#23555/#27284（`6970293…`）、Chipyard #587/#588（`b13168d…`）。每对完整 source 和 target SHA 都相同。解决 ID 唯一性以后，仍需避免相同代码跨开发/测试集；不能把不同 PR 的讨论历史直接删除。

## 对当前成果的准确表述

可以表述为：“EDABench 基于 AACR-Bench 的 PR 级审查思路，完成 EDA 仓库原始采集、固定审查版本/diff 构造及已有讨论的 LLM 候选整理；采用自定义仓库筛选、线程计票和候选门槛，尚待新问题补充、去重、真人专家确认与完整仓库评测。”

不宜表述为“已完整复现 AACR-Bench”“26,512 条已确认缺陷”“34,822 条真人验收通过”或“已有模型 benchmark 得分”。本次完成的是方法核查和差异证据；后续行动与分层有效性见 [核查结论与下一步][conclusion]。

[paper-web]: https://arxiv.org/abs/2601.19494v3
[official-web]: https://github.com/alibaba/aacr-bench/tree/68a569759289a83654a59d06db2a72910edf0a4a
[paper]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/2601.19494v3.pdf>
[P3]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/paper_pages/page-03.txt>
[P4]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/paper_pages/page-04.txt>
[P5]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/paper_pages/page-05.txt>
[P12]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/paper_pages/page-12.txt>
[P13]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/paper_pages/page-13.txt>
[P15]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/paper_pages/page-15.txt>
[P17]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/paper_pages/page-17.txt>
[P18]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/paper_pages/page-18.txt>
[P25]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/paper_pages/page-25.txt>
[source-check]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/official_reference_download_checks.json>
[paper-check]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/official_paper_checks.json>
[official-data]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/official_dataset_checks.json>
[eda-data]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/eda_artifact_checks.json>
[eda-boundary]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/eda_execution_boundary.json>
[archive-coverage]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/evidence/package_archive_coverage.json>
[id-collisions]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/evidence/official_id_collisions.json>
[adapter-traces]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference_adapter_static_traces.json>
[excerpts]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/evidence/source_excerpts.json>
[E-input]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/inputs.py:8>
[E-collect]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/collect.py:87>
[E-build]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/build.py:18>
[E-material]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/material.py:259>
[E-method]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/method.md:5>
[E-method-time]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/method.md:32>
[E-code-policy]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/method.md:74>
[E-revision]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/edabench/revisions.py:30>
[E-baseline]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/method.md:51>
[E-archive]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/method.md:66>
[E-location]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/method.md:44>
[E-format]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/method.md:85>
[E-followup]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/method.md:78>
[E-rubric]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/thread-annotation.md:12>
[E-full]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/thread-full-run.md:9>
[E-full-human]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/docs/thread-full-run.md:32>
[E-packet]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/prepare_thread_pilot.py:68>
[E-aggregate]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/extracted/EDABench/scripts/build_pr_candidates.py:186>
[A-default]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/converters/aacr_bench.py:50>
[A-convert]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/converters/aacr_bench.py:164>
[A-convert-id]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/converters/aacr_bench.py:172>
[A-schema]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/schema.py:92>
[A-schema-load]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/schema.py:193>
[A-repo]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/repo_utils.py:47>
[A-repo-prepare]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/repo_utils.py:120>
[A-pipeline]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/pipeline.py:366>
[A-judge]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/judge.py:24>
[A-judge-null]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/judge.py:201>
[A-eval-side]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/evaluate.py:118>
[A-eval-metric]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/evaluate.py:271>
[A-eval-missing]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/evaluate.py:344>
[A-ocr]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/reviewers/ocr.py:41>
[A-claude]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/reviewers/claude.py:161>
[A-codex]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261006_b/reference/aacr-bench/evaluation/reviewers/codex.py:218>
[prior-material]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/material_checks.json>
[prior-full]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/full_annotation_checks.json>
[prior-aggregate]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/aggregation_semantic_comparison.json>
[prior-summary]: <D:/Projects/researches/EDACR/data/edabench_initial_2026-10-05/independent_audit/20261005_a/audit_summary.json>
[prior-cases]: <D:/Projects/researches/EDACR/docs/EDABench_15例独立审阅.md>
[conclusion]: <D:/Projects/researches/EDACR/docs/EDABench_核查结论与下一步.md>
