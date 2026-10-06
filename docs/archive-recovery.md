# 2026-09-23 归档异常修复与缓存清理

恢复前状态：44 个仓库索引完成；3,920 / 15,804 个候选 PR 完成原始采集；3,612 个
材料任务完成。上次进程于 2026-09-22 19:03 左右退出，错误来自 firesim/firesim#1791
归档中的 sim/chipyard-symlink：安全解包拒绝其指向目录之外的目标，但任务边界没有
捕获 tarfile.LinkOutsideDestinationError。

修复保留 filter='data'，在任务边界捕获 tarfile.TarError，记录
archive_error:<异常类型>:<原因>，令该任务失败并继续其他 PR。没有跳过不安全成员
后宣称完整，也没有关闭安全检查。认证错误和未预期的程序错误仍会终止运行。

验证：新增越界符号链接、越界硬链接及损坏归档的回归样例，修复前均会导致采集
流水线退出，修复后均只导致单个任务失败，且解包目录外的文件不变。使用缓存重放
真实 firesim/firesim#1791，禁止 HTTP 网络请求，成功记录 LinkOutsideDestinationError
并正常返回，已完成的对照 PR 保持完成。完整测试集 36 passed。

用户明确要求删除此前反复缓存的大仓库归档后，删除了
`data/archives/The-OpenROAD-Project/OpenROAD-flow-scripts`：533 个文件、208.66 GiB。
清单和删除结果保存在 data/openroad-archive-cleanup.json。完成时数据盘可用空间约
240.62 GiB。未删除其他仓库归档、原始 API、SQLite、完整 diff 或导出样本。

后续新下载归档改为本次构造的临时文件，在成功或失败后释放，仍复用现存缓存。
已确认 archive_tree_hash_mismatch 的固定 SHA 任务保留失败记录，普通续跑不再
重新下载同一批归档；其他待处理或失败任务仍按原有恢复机制处理。这避免清理后
立刻重建数百个相同缓存。测试同时覆盖临时文件在成功和失败时的清理，以及已知
树哈希不匹配任务不会自动重新下载。

继续沿用现有数据库、采集截止时间、4 个采集 worker、4 个构造 worker、8 个 HTTP
并发槽和 2 个归档下载并发。当前启动信息见 data/full-run.json，日志为 data/full-run.log。

全量续跑于 2026-09-23 09:51:34 +08:00 启动，采集 PID 为 2459254，低空间监测
PID 为 2459255。仍保留低于 10 GiB 时正常中断的保护。原始 token 配置摘要与最初
记录一致。启动后的任务状态确认已开始领取原断点后的 PR，已删除的 OpenROAD
归档目录没有被重新创建。
