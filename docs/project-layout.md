# 当前项目目录与迁移说明

迁移日期：2026-10-07。现在直接打开 `D:/Projects/researches/EDACR/`，这里就是项目及 Git 仓库根目录，不再使用旧 `extracted` 或 `work` 路径。

```text
EDACR/
├── .git/              原有提交历史与远端配置
├── config/            配置示例
├── edabench/          项目核心代码
├── scripts/           采集结果与标注整理脚本
├── tests/             原有测试及修复回归
├── docs/              文档、PPT、Excel
├── reference/         参考来源记录与本地参考材料
├── data/              本地部分数据，不提交 Git
│   ├── annotation/
│   ├── dataset/
│   ├── diffs/
│   ├── pr-candidates/
│   ├── audit/20261006_c/
│   │   ├── label_revision/       标签修订建议
│   │   ├── human_review/         人工复核表
│   │   ├── pilot/                真实试跑输入、输出和计分
│   │   ├── previous_audits/      两批独立核查及辅助材料
│   │   └── publication/          合并、发布、清理及覆盖前备份
│   └── provenance/layout_20261007/
│       ├── download/             原下载来源、校验摘要、目录清单和辅助记录
│       ├── outer_variants/       与项目版本不同的外部历史文件
│       ├── migration_manifest.json 逐文件保留与迁移核对
│       └── path_mapping.json     历史位置与当前位置对照
├── README.md
├── AGENTS.md
└── pyproject.toml
```

外部记录按内容摘要核对：已有相同副本的记录去重，独有文件归入对应的 audit 目录或 provenance。迁移前的 11,264 个项目文件和 475 项外部记录已在新根目录逐文件校验；Git 历史及对象检查通过，新根目录 Linux 全套 80 项测试通过。

原始 `edabench.tar.gz` 已按要求删除，学长云盘原包未改。以后需要完整数据库或其他未解出的材料时，从原始云盘重新下载，使用 `download/source_metadata.json` 中的来源和 `download/edabench.tar.gz.sha256` 校验。原包解压得到 `EDABench/`，只将所需的数据合入本项目的 `data/`，保留已有新增记录和修复代码。

数据上传已取消。本地 audit 和 provenance 都不随 Git 提交，学长原包也没有本轮新增结果，需要另行备份。历史记录中的绝对路径和摘要保留，阅读时通过路径对照找到当前文件；旧报告描述的是当时阶段，当前目录以本文为准。
