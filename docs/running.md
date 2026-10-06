# 运行与恢复

在仓库根目录执行（Python 3.11+）：

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python -m edabench run --repo olofk/serv --pr 57 --pr 60 --pr 79 --pr 146
python -m edabench run
```

--repo 可重复指定，但必须来自 Excel；--pr 用于小样本验证，必须搭配单个 --repo。
不带这两个选项时扫描 Excel 的所有仓库。默认 --excel docs/final_repository.xlsx、
--config config/github.yaml、--data data。small-sample 运行不会将全量状态标成完成。

```bash
python -m edabench status
python -m edabench collect       # 原始 API 与完整 diff 材料，断点恢复
python -m edabench build         # 完全离线重建导出，无需凭据或网络
```

输出在 data/dataset/samples.json、manifest.json、report.json、decisions.json、
alignment_failures.json 和 unavailable_history.json。原始数据库为 data/state.sqlite3，
完整 diff 位于 data/diffs，必要归档位于 data/archives。数据、运行日志、参考源码和
token 配置均被 Git 忽略。不要只复制 SQLite 主文件而遗漏仍在写入的 WAL；备份时
停止写进程或使用 SQLite backup API。

data/archives 中的历史缓存仍可复用；新下载的整仓归档放在本次构造的临时目录，
构造成功或失败后释放，长期保留原始 API、完整 diff 和构造结果。离线 build 不需要
这些临时归档。已确认 archive_tree_hash_mismatch 的任务保持失败记录，普通续跑
不自动重复下载同一批固定 SHA；改进恢复方法后可显式将对应任务重置为 pending。

全量采集使用独立的 4 个 PR 采集 worker 和 4 个材料构造 worker。采集完成后，
将待构造任务写入 SQLite；构造较慢时，采集可以继续推进，待处理材料保存在磁盘，
不会把原始响应堆积在内存队列中。每个阶段同时处理的 PR 数均最多为 4。
--pr 小样本命令仍按指定列表顺序执行。

默认最多 8 个 API 请求和 2 个归档下载。REST 初始间隔 0.8 秒（约 4,500 次/小时），
并根据实际 remaining/reset 留出 10% 余量；GraphQL 单独读取 cost/remaining/reset。
两个阶段共用同一个 API 客户端和限流状态，拿到 HTTP 并发槽后再按共享节奏发送，
遵守 Retry-After，等待时每至多 30 秒交回事件循环。重启时恢复保存的额度状态。
归档完整性检查及本地 Git diff 在线程执行，避免阻塞其他 worker 的网络请求。
临时失败有限重试，认证/权限错误立即停止。额度窗口等待是正常行为，请查日志及
status 的 quotas。失败任务保留原因，重新运行相同命令可恢复；固定 SHA 的不可用
响应不会被伪装成成功。

归档损坏或包含指向解包目录之外的链接时，仍执行安全解包检查，将该 PR 的材料
任务记录为失败（原因以 archive_error 开头），其他 PR 继续处理。不会跳过不安全
成员后将不完整的源码树视为成功，也不会因单个归档异常终止整轮采集。

断点恢复覆盖两个阶段：已完成采集的 PR 直接进入待构造队列；已完成构造的 PR
跳过；被中断、未执行或其他失败的任务重新尝试。单次运行中失败任务只尝试一次，
不会在队列中反复重试。正常取消将正在执行的任务标为 pending；异常退出遗留的
running 状态也会在下次运行时恢复。使用同一数据目录即可：

```bash
python -m edabench run
```

退出码：0 表示命令执行结束（仍应检查 manifest.complete），2 表示存在失败任务
或输入/本地错误，3 表示认证/授权错误，130 表示中断。Ctrl-C 不删除缓存。不要
启动多个写进程；单写锁会拒绝重复启动，status 可随时运行。

长期运行可使用终端会话管理器或后台进程。当前真实运行的 PID 和日志位置记录在
验证记录中；重新启动前先检查旧进程是否仍存活，避免并发写入。
