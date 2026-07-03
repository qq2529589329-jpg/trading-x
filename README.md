# 龙头战法 AI 选股系统

项目根目录是 `龙头战法`。V1 是盘后规则化日报系统，负责市场判断、A/B 类候选、风控否决和次日预案。

V1 不自动下单，不接券商交易，不做外部大模型，不做秒级盘中盯盘。本系统只用于研究和纪律执行，不构成投资建议。

## 快速开始

首次使用：

```powershell
Copy-Item .env.example .env
uv run python -m trading_x init-db
uv run python -m trading_x doctor
```

把 `.env` 里的 `TUSHARE_TOKEN` 改成你自己的 Tushare Pro token。不要把 token 写进报告、日志、截图或提交记录。

每日盘后：

```powershell
uv run python -m trading_x daily --date 20260701
uv run python -m trading_x acceptance --last-complete-n 10
```

`daily` 会依次执行 `doctor -> update -> report`，并输出市场状态、是否允许交易、候选数量、报告路径、题材覆盖率和推荐验收命令。

## 常用命令

```powershell
uv run python -m trading_x doctor
uv run python -m trading_x update --date 20260701
uv run python -m trading_x report --date 20260701
uv run python -m trading_x daily --date 20260701
uv run python -m trading_x acceptance --last-complete-n 10
uv run python -m trading_x acceptance --dates 20260615,20260616,20260617
uv run python -m trading_x acceptance --list-incomplete
uv run python -m trading_x themes import --file data/theme_members.csv
uv run python -m trading_x themes coverage --date 20260701
```

`acceptance --last-complete-n 10` 是正式验收路径，只选择 P0 数据和报告文件都完整的最近 10 个交易日。

`acceptance --last-n 10` 是原始诊断路径，会直接检查最近 10 份报告快照；如果库里有 P0 不完整的脏快照，它会失败并暴露问题。

`acceptance --list-incomplete` 只读列出 P0 数据或报告文件不完整的快照日期和缺失项，不会删除或修复数据。

## 数据能力

`doctor` 会检测 Tushare token 与接口权限，并把结果写入 `data_capabilities`。

- `FULL`：P0 可用，P1 核心数据可用，候选置信度正常。
- `BASIC`：P0 可用，P1 部分缺失，候选可生成但置信度下降。
- `BASIC_WITH_THEME_FALLBACK`：P0 可用，缺少高质量题材接口，但启用本地题材映射。
- `DEGRADED`：P0 缺失，不生成候选，只生成数据不足结论或直接失败。

P0 包括股票列表、交易日历、日线、每日指标、涨跌停价和基础风险标记。P1/P2 缺失不能导致日报崩溃，但必须在报告里降级说明。

## 题材映射

V1 使用本地 CSV 作为题材 fallback：

```text
data/theme_members.csv
```

导入后系统会写入 SQLite，并在更新数据时聚合每日题材强度。CSV 维护入口字段包括：

```text
ts_code,name,industry,theme_primary,theme_tags,theme_source,confidence,updated_at,notes
```

## 输出文件

日报固定生成：

```text
reports/YYYYMMDD_report.json
reports/YYYYMMDD_report.md
```

JSON 是机器复盘真相，Markdown 给人阅读。每只候选至少包含策略类型、候选等级、主线题材、入池理由、否决项、买入观察条件、放弃条件、最大追高限制、结构止损位、建议仓位、最大亏损、数据置信度、`theme_confidence` 和 `event_confidence`。

## 本地运行产物

以下文件是本机运行结果，不作为人工维护源数据：

```text
data/trading_x.db
data/qa_*.db
reports/
```

`data/theme_members.csv` 是例外，它是 V1 本地题材映射入口，需要人工维护并保留。`qa_*.db` 是开发烟测数据库，可重建；如果要清理，我会先确认再删除。

## 验收标准

连续 10 个完整交易日必须满足：

- P0 数据可更新且无重复脏数据。
- JSON + Markdown 报告可生成。
- P0 缺失时不生成假候选。
- 每日报告有市场状态和允许/观察/禁止结论。
- 候选数量为 0-5。
- 每只候选都有入池理由、否决项和次日预案。
- 无候选时明确输出禁买原因。
- 重复运行同一天结果稳定。
- 缺少 P1/P2 接口时可降级，不崩溃。

## V1+ 暂缓

`trade_logs` 已建表，但 V1 不启用交易日志导入。后续 V1+ 再接 CSV 导入、复盘统计、盘中盯盘和看板扩展。
