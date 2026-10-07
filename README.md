# EDA review corpus

## 本仓库与完整数据

本仓库保留原下载项目的目录结构，并直接合入 2026-10-06 已核查的代码修复。当前代码在原项目位置的 Linux 全套测试为 80 passed。源码仓库：https://github.com/LUCAZZZBNER/EDACR。

2026-10-07 已将项目提到 `D:/Projects/researches/EDACR`，现在直接打开这个目录开发。外部独有记录全部归入项目，旧 `extracted` 层级和原始大压缩包已按要求删除。新根目录的 Linux 全套测试为 80 passed。目录、记录位置和数据恢复方式见 [项目目录与迁移说明](docs/project-layout.md)。

完整 `data/` 不提交到 Git，数据上传已取消；本地只有按需解出的数据，后续从学长提供的原始云盘恢复所需材料。下载来源、原包 SHA-256 和目录清单保存在本地 `data/provenance/layout_20261007/download/`。只将原包中所需的 `EDABench/data/` 内容合入当前项目的 `data/`，避免覆盖已修复的代码和新增记录。原包的真实凭证不能复用或公开。新增 `data/audit/20261006_c` 与 `data/provenance/` 不在原包中，也不随 Git 上传，需要另外备份；模型标签及试跑参考仍未经过真人专家确认。

API 采集前，将 `config/github.example.yaml` 复制为本地 `config/github.yaml` 并填入自己的 token；真实配置已被 Git 忽略。下载的 `reference/aacr-bench` 上游源码也不提交，固定来源与 commit 见 `reference/aacr-source.json`。完整说明见 [仓库与数据说明](docs/project-publication.md)。

采集 Excel 中的全部仓库，构造带版本对齐信息的原始审查数据集。参考 AACR
论文 §3.2、附录 B.1 和固定版本的公开 JSON；来源见
[reference/aacr-source.json](reference/aacr-source.json)。原始论文、Excel、PPT 和
`config/github.yaml` 不修改。下载的 AACR 完整源码仅在本地 reference/aacr-bench。

本项目保留全部历史已关闭 PR（包括未合并），不按 stars、主语言、自然语言、
LOC、文件数或采纳情况筛选。源码、测试、构建及约束文件算代码；格式修改保留，
纯文档 PR 排除。独立 inline 线程按根评论 original_commit_id 投票，每个 PR
只选一个 revision；并列按最早审查时间和 SHA 排序。只排除 GitHub Bot 类型
及 `[bot]` 账号，感谢、确认、作者回复和未知身份均保留。

原始采集与导出流程不执行语义改写、缺陷确认、LLM 增强、人工标注、问题分类、上下文
标注、分层抽样或训练测试划分。category/context 留空；resolved、outdated
及后续修改是独立证据，不表示意见已采纳。本产物不是已验证的缺陷基准。

另有独立的 [200 线程 LLM 候选标注试运行](docs/thread-pilot-validation.md)，
使用 gpt-5.6-luna / max 整理已有讨论；原始 samples.json 保持不变。
候选标注和模型复核均不等同于人工确认的缺陷金标准。
后续 [全量线程分类](docs/thread-full-run.md) 复用已验证的试运行结果，
通过独立任务队列执行并发领取、断点恢复和失败重试。

完成标注校验后，可离线生成 [PR 级候选集与分布统计](docs/pr-candidates.md)，
保留零候选 PR、未定位意见和来源记录：`python scripts/build_pr_candidates.py`。

## 安装与运行

```bash
python -m pip install -e '.[test]'
python -m edabench run
python -m edabench collect
python -m edabench build
python -m edabench status
python -m pytest
```

默认 Excel 为 docs/final_repository.xlsx，凭据文件为 config/github.yaml，
数据目录为 data。凭据只用于 API Authorization 头。build 完全离线。
实现、完整性规则及运行记录见 docs 下的说明。
