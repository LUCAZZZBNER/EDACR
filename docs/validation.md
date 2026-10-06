# 实际验证记录

验证日期：2026-09-21（Asia/Shanghai）。用户补充要求：完成代码、小样本测试成功后，
开始全部数据爬取。因此本记录确认全量已启动，不宣称全量已完成。

## 自动验证

`python -m pytest -q`：21 passed。覆盖 REST 多页/恢复/幂等、Retry-After、认证错误、
GraphQL 顶层和线程内游标、PR commits 250 上限及 compare 补齐、final files 3,000
上限标记、compare 300 文件上限和 patch 截断、线程投票与并列、未知身份和机器人
根下的人类回复、原文感谢/确认、LEFT/RIGHT、多行、过期锚点、重命名、旧 position、
历史 SHA 缺失、base ref 变更拒绝、不限制 1,000 行、纯文档排除、选中版本统计、
原始语义字段留空、离线稳定重建。Git 实例验证归档 tree SHA、二进制、执行权限、
符号链接、重命名，以及完整 diff 媒体类型保留模式变更。

## 真实小样本

命令（同一数据目录可恢复运行）：

```bash
python -m edabench run --repo olofk/serv --pr 57 --pr 60 --pr 79 --pr 146
python -m edabench run --repo olofk/serv --pr 29
```

| PR | 选中变更 LOC | 导出评论 | 位置验证通过 | 完整 diff 来源 |
|---|---:|---:|---:|---|
| olofk/serv#29 | 8 | 3 | 3 | 验证过的 compare diff |
| olofk/serv#57 | 58 | 8 | 8 | 验证过的 compare diff |
| olofk/serv#60 | 271 | 15 | 15 | 归档 tree SHA 校验 + 本地 Git |
| olofk/serv#79 | 531 | 10 | 10 | 归档 tree SHA 校验 + 本地 Git |
| olofk/serv#146 | 4,206 | 1 | 1 | 归档 tree SHA 校验 + 本地 Git |

共 5 个 PR、37 条评论，全部定位通过，无失败任务。前 4 个 PR 的选中 revision
不同于最终 head；已保存选中版本的统计与后续变更证据。#146 验证大于 1,000 行
仍可纳入。ZipCPU/wb2axip 的真实索引为零条 inline 评论，未伪造样本。

将 socket.socket 替换为禁止网络访问的实现，连续调用 build 两次；samples、
manifest、report、decisions、alignment_failures、unavailable_history 六份输出
的 SHA-256 全部相同。小样本 samples.json SHA-256：
`603190d252cda0a3237155a660a01c50c1a44ee29365ef0489a85b8d0ed52872`。

原始配置 SHA-256 与执行前一致。以实际 token 字节检查工程、测试、原始资料、
本地产物及全部已存在 Git 对象，未发现泄漏。配置内容不写入文档或日志。
原始 Excel/PPT/PDF 摘要见 reference/input-sources.json。

真实运行中修正了逐条 SQLite 提交导致的慢写入，改为按页批量写入和 WAL NORMAL；
加入单写锁、共享限流退避、归档同 SHA 下载锁和原子 diff 写入。进一步读取 API
完整 diff 媒体响应，避免只拼接 patch 时遗漏文件模式变更。

## 全量启动

2026-09-21 23:39:41 +08:00 已启动：

```bash
python -u -m edabench run
```

本次 PID：2453418；日志：data/full-run.log；启动信息：data/full-run.json。
作用域为 Excel 全部 44 个仓库，截止时间固定为 2026-09-21T15:21:52.199716Z。
程序先完成全部仓库索引，再采集候选 PR 并构造材料，最后更新导出。
全量期间现有 samples.json 仍是小样本结果，不能当成全量结果。

```bash
python -m edabench status
tail -f data/full-run.log
```

全量爬取需要跨额度窗口运行。应以实际进程、任务状态和最终 manifest.complete
为准，PID 只记录这次启动，不保证未来仍然有效。进程退出后可用同一 run 命令
恢复；不可恢复历史对象与临时失败均会在报告中明确列出。
