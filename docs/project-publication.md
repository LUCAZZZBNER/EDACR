# 仓库与数据说明

2026-10-06 按要求保留原项目结构，把已测试修复直接覆盖到项目中，以此目录作为 Git 仓库根目录。覆盖前文件在原工作区的 `publication/source_before_merge` 备份，原始下载压缩包未改。

源码：[LUCAZZZBNER/EDACR](https://github.com/LUCAZZZBNER/EDACR)。完整数据：[Google Drive 目标文件夹](https://drive.google.com/drive/folders/1GMo1vTnPHk9KEGbGP4D9z_2AsUA6S7DH)。

Git 管理源码、脚本、测试、依赖配置、文档、PPT、Excel 仓库清单及参考来源记录。`.gitignore` 排除整个 `data/`、真实 GitHub 配置、环境缓存、大压缩包及下载的 AACR 参考源码副本。GitHub 不保存全量数据库、采集结果或源码快照。

数据包 `EDABench-data-20261006.tar.gz` 从完整原包中的 `EDABench/data/` 重新打包，归档路径以 `data/` 开头；加入本轮 `data/audit/20261006_c` 修订和试跑证据。原项目配置与代码不在数据包内，GitHub PAT 模式检查覆盖打包的数据字节。云盘同时保存 `data_manifest.json`、`checksums.sha256` 和 `DATA_README.md`。不要把按需解压的本地 data 目录当作完整原包。

拿到仓库和数据包后：

```bash
python -m pip install -e '.[test]'
sha256sum -c checksums.sha256
tar -xzf EDABench-data-20261006.tar.gz -C /path/to/EDABench
python -m edabench status
python -m pytest
```

完整测试使用 Linux；Windows 有既有测试夹具的换行与符号链接权限差异。直接覆盖后的 Linux 全套 80 项通过。

需要重新采集时，复制配置示例并填写新 token。旧原包中的真实 token 不应公开或复用。各审查报告中的“原文件未修改”是当时核查阶段的记录；本次是随后经用户明确授权的合并，覆盖前备份和摘要另行留存。历史实验中的本机绝对路径作为来源证据保留，迁移环境时应以项目内相对路径对应文件。

本轮原始标签保持不变。修订建议、人工复核空表和试跑输出在新增 audit 批次中；全部 `human_verified=false`。不能把云盘数据包或本轮匹配率直接当作已验收的正式 gold。
