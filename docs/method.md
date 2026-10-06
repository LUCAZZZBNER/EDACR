# 构造规则与完整性边界

本文描述根目录 README 中选定的原始数据采集口径，不执行 AACR 的语义标注或评测。
独立的线程候选标注试运行见 [thread-pilot-validation.md](thread-pilot-validation.md)，不改写本文的数据产物。
Excel 的 44 行 full_name 为唯一仓库来源，不用 stars/主语言筛选。保留输入行号、
去重标记、GitHub 规范名称及 Excel SHA-256。首次 collect 固定 UTC 截止时间，
后续恢复沿用它；如需新一轮截止时间，请使用新的 --data 目录。

## 原始采集

先完整分页扫描 closed PR 和仓库 inline 评论，再对有至少一条非明确机器人 inline 评论的闭合 PR
补充详情、commits、files、reviews、inline/replies、issue discussion。GraphQL
分页获取 reviewThreads（含线程内部 comments 游标）及 head/base force-push、
base ref change 事件。PR commits 接口达到 250 或与计数不符时使用分页 compare
补齐并核对总数；final PR files 达到 3,000 或数量不符时补建最终版本完整 diff。
compare commits 按 total_commits 验证；compare files 达到 300 就视为可能截断。

SQLite responses 保存每页 API JSON/文本、有限响应头和 fetched_at；api_request
实体保存无凭据的 URL、参数、GraphQL 请求与 cache key。entities 保存可直接
按仓库/PR/评论 ID 查询的原始 JSON。tasks 保存索引、PR、材料构造的执行状态。
已完成页面立即缓存，按页提交实体；重复执行按主键覆盖，不会重复插入。
collect/run/build 通过文件锁保证每个数据目录仅一个写进程；status 可同时读取。

原始采集与材料构造各使用 4 个独立 worker，待构造队列保存在 SQLite。采集完成后
即持久化待构造状态；恢复时也会检查已完成采集却尚未完成构造的 PR，补入队列。
两个阶段共用最多 8 个 HTTP 并发槽和同一限流器，归档下载最多 2 个并发；归档
完整性检查及本地 diff 使用线程，不阻塞异步网络调度。

恢复会重做未完成任务并复用完成页面。不可获取的历史 SHA 保存 unavailable
及 HTTP 状态；认证失败直接停止。状态为 running 但进程已停止的任务也会恢复。

API 不能提供事务性历史快照：截止时间过滤 PR 的创建/关闭时间和评论创建时间，
字段正文、resolved/outdated 等是各次请求时观察到的值；编辑、删除和重开可能影响
列表。manifest 明示此边界，不声称恢复了截止时间时刻的完整 GitHub 状态。

## 线程、revision 与定位

从 REST in_reply_to_id 递归找到根评论，按根的 original_commit_id 归组。
每个含至少一条非明确机器人的独立线程一票；并列按最早根审查时间、SHA 排序。
回复数不会增加线程票数，回复自身的 original_commit_id 不改变线程归组。
只根据 user.type=Bot 或 login 的 [bot] 后缀排除机器人；身份缺失保留。
缺根/循环回复关系不猜测，记录原因。选中线程中的全部非机器人原文均保留。

优先使用 original_line/original_start_line 和原始 diff_hunk；原始 hunk 允许
GitHub 截断到评论位置。LEFT 映射 source，RIGHT 映射 target，重命名时分别使用
旧/新路径。旧式 original_position 仅在完整 diff 和原始 hunk 文本一致时接受。
跨 side 的多行范围、缺失行号或无法校验的锚点不填造位置。可导出 PR 内无法定位
的选中评论仍保留，from_line/to_line=null，metadata 给出原因；每个导出 PR 至少
含一条 verified 评论。所有定位失败另列 alignment_failures.json。

## 基线与完整 diff

以 PR API base SHA 和选中 target 的 merge base 为 source 候选。若审查后 base
被 force-push，使用首个相关事件的 beforeCommit；base ref 改名没有可信历史 SHA
时明确无法构造。检查评论原始 hunk 的两侧行文本；与候选基线冲突的 PR 不导出。
没有发生 base ref change、且 GitHub 暴露的信息没有冲突，也不等于证明所有未公开
历史事件都已恢复；baseline_method 记录实际使用的验证方法。

先验证 compare 每个 patch 的 hunk 长度和增删计数，再读取 diff 媒体类型的完整
响应，校验文件数、路径、每个 patch 和计数，保留模式变更等 diff 头部。
达到文件上限、patch 缺失/截断、二进制或校验失败时，下载 source/target 固定 SHA
归档，以本地 Git 重建。树接口截断则递归获取子树；补入 gitlink 后，重建 tree SHA
必须与 GitHub commit tree SHA 完全一致，才能使用 diff。归档因 export-ignore 等
缺失内容、历史对象失效或无法下载时明确失败。归档解包不会执行仓库代码。

既有归档缓存可复用，新下载的整仓归档仅在当前构造期间保存，退出构造后释放；
校验完成的 diff、统计和原始 API 仍持久化，离线重建不依赖整仓归档。已明确的树
哈希不匹配保持失败状态，不在普通续跑时重复下载。安全解包拒绝越界链接或损坏
归档时记录 archive_error，其他 PR 继续处理，不关闭解包检查。

additions/deletions/changed_loc/changed_files/hunks 全部来自选中的 source→target，
不用 PR 最终版本统计。diff 按 SHA 缓存并保存 SHA-256；build 重新验证文件摘要。
二进制文件无文本 LOC，但计入文件数，完整 Git binary patch 保存在 diff 中。
源码策略为 revisions.py 中明确列出的源码/HDL/测试/构建/约束扩展名和文件名；
不以语言识别模型推断，未知扩展名可能需要后续规则修订。纯文档变更排除，
格式变更保留；不排除混合文档与源码的 PR。

resolved/outdated 是独立观测信号。后续区域修改证据只比较选中 target 与最终 head
之间可验证的累计文本变化，排除 hunk 上下文行；不声称覆盖中间修改后回退的情况。
LEFT 锚点、非祖先（例如 force-push）、后续二进制内容或下载失败标记 not_assessed/
unavailable，不推出“未采纳”。任何信号都不会生成已采纳或已验证缺陷标签。

## 导出与完成状态

samples.json 使用 AACR JSON 数组及原有核心字段，side 为小写 left/right。
category/context/source_model 留空，原始 GitHub 非机器人评论 is_ai_comment=false；
这不是正文语义或作者是否使用 AI 的判定。metadata 关联 PR、线程、原始评论、
source/target、完整 diff、revision 投票及独立证据。未执行语义标注。

manifest.json 包含输入摘要、参考版本、截止时间、规则和完成状态；report.json
按仓库列原始数量、导出数量、过滤/定位原因、未完成和失败任务。
unavailable_history.json 单独列出不可恢复历史 SHA；unrecoverable_with_cached_material
区分现有缓存无法补齐的历史/归档问题。complete=false 不能解读为全量采集完成。

同一份缓存上反复 build 不发网络请求，导出 JSON 字节稳定。build 不读取 token。
SQLite 使用 WAL 和 synchronous=NORMAL；正常中断可恢复，系统断电可能需要重采
最后的事务，但不会用部分任务充当已完成任务。
