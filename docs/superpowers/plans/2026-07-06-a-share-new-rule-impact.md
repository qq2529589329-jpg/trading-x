# A股 2026-07-06 交易新规影响改造清单

> **For agentic workers:** implement this as a rule-compatibility change before adding new strategy logic. Do not treat the new rules as a reason to loosen risk filters.

**Goal:** Make the AI 选股与盯盘系统 compatible with the 2026-07-06 A-share trading rule changes.

**Architecture:** Keep the existing 龙头战法 framework. Add a date-versioned trading-rule layer, split ordinary-stock emotion from ST speculation, and treat 15:05-15:30 post-close fixed-price trading as an observation phase, not as a new buy phase.

**Tech Stack:** Existing Python CLI, SQLite, Tushare daily data, replay CSV flow, report Markdown/JSON outputs.

---

## 结论

这次新规不要求推翻龙头战法，但要求系统升级为“规则版本化”。

核心改动不是追 ST，也不是盘后乱买，而是：

- 涨跌停规则按日期查表，不能硬编码。
- ST 继续一票否决，并且从普通短线情绪中剥离。
- 成交额拆成 `regular_amount`、`post_close_amount`、`total_amount`。
- 15:05-15:30 进入时间轴，但只做观察和风险提示，不触发新买入。
- 回测必须按 `rule_version = 2026_07_06` 切开，避免新规污染历史。

## 新规相关事实

基于用户提供的 `C:\Users\Administrator\Desktop\A股新规.txt`，与系统最相关的规则变化是：

- 自 2026-07-06 起，沪深交易规则修订实施。
- 沪深主板风险警示股票，也就是 ST / *ST，涨跌幅限制由 5% 调整为 10%。
- 盘后固定价格交易扩展到全部 A 股和 ETF，时间为 15:05-15:30，按当日收盘价成交。
- 深交所创业板引入做市商机制，创业板协议大宗交易成交确认时间有调整。
- 上交所基金收盘阶段交易方式调整为收盘集合竞价。

## 必须新增的系统概念

### 1. `rule_regime_at_signal`

已有研究计划中准备加入：

```text
market_regime_at_signal
```

新规后还要加：

```text
rule_regime_at_signal
rule_version_at_signal
```

含义：

- `market_regime_at_signal`：市场状态，如 `BULL`、`RANGE`、`BEAR_GRIND`、`PANIC`、`REPAIR`。
- `rule_regime_at_signal`：制度环境，如 `pre_20260706`、`post_20260706`。
- `rule_version_at_signal`：具体交易规则版本，如 `2026_07_06`。

交易、候选、回测、日报都必须能追溯当时使用的规则版本。

### 2. `TradingRuleRegistry`

新增一个按日期查询交易规则的注册表。

必须支持：

```text
trade_date
board
is_st
is_etf
price_limit_ratio
after_hours_enabled
post_close_trade_start
post_close_trade_end
rule_version
```

禁止继续写：

```text
if is_st:
    limit_ratio = 0.05
```

必须改成：

```text
rule = TradingRuleRegistry.lookup(ts_code, trade_date)
limit_ratio = rule.price_limit_ratio
```

## 需要改动的地方

### 1. 涨跌停判断

改动点：

- 所有涨跌停判断都从 `TradingRuleRegistry` 取比例。
- `stk_limit` 仍作为官方涨跌停价来源，但系统要能检查它是否符合当前规则。
- 2026-07-06 前主板 ST 按 5%。
- 2026-07-06 后主板 ST 按 10%。

影响模块：

- 日线更新。
- 涨停收盘判断。
- 跌停不可卖判断。
- 一字涨停不可买判断。
- A 类空间板判断。
- 回测成交模型。

### 2. ST 过滤

改动点：

- ST / *ST 继续一票否决。
- ST 不进入 A/B 候选池。
- ST 不参与空间板排序。
- ST 不参与普通股 `DragonScore`。
- ST 不作为市场总龙头。
- ST 只作为风险情绪观察项。

日报应该明确写：

```text
ST 投机情绪：升温 / 降温
交易结论：不因 ST 活跃提高普通龙头战法仓位
```

### 3. 市场情绪拆分

原来混合情绪指标容易被 ST 污染。新规后拆成两套：

```text
core_market_emotion_score
st_speculation_score
```

普通股情绪字段：

```text
normal_limit_up_count
normal_limit_down_count
normal_break_limit_rate
normal_highest_board
normal_limit_premium
```

ST 风险情绪字段：

```text
st_limit_up_count
st_limit_down_count
st_highest_board
st_speculation_score
```

交易开关只能看：

```text
core_market_emotion_score
```

不能因为 ST 涨停多而提高 A/B 类仓位。

### 4. 盘后固定价格交易阶段

时间轴从原来的交易日结构升级为：

```text
09:15-09:25 开盘集合竞价
09:30-11:30 连续竞价
13:00-14:57 连续竞价
14:57-15:00 收盘集合竞价
15:05-15:30 盘后固定价格交易
```

系统规则：

- 15:00 前照常做盘中风控和尾盘提醒。
- 15:05-15:30 不发 `BUY_TRIGGER`。
- 15:05-15:30 不新增候选。
- 15:05-15:30 只允许观察盘后成交、持仓风险、次日预案降级。

允许输出：

```text
【盘后固定价格交易提示】
XX 股今日收盘弱势，15:05-15:30 可按收盘价尝试卖出。
注意：仅适用于已有可卖持仓，不作为新买入信号。
```

### 5. 成交额口径

新增成交额字段：

```text
regular_amount
post_close_amount
total_amount
post_close_amount_ratio
post_close_data_available
```

使用规则：

- `VolumeGate` 只能用盘中 `amount_since_open` 或 `regular_amount`。
- 日线流动性筛选可以看 `total_amount`，但要展示 `post_close_amount_ratio`。
- 题材强度默认用 `regular_amount`。
- `post_close_amount` 只做辅助复盘，不做买入依据。

如果 V1 没有盘后固定价格数据源，必须在报告里写：

```text
盘后固定价格交易数据：unavailable
成交额口径：可能包含盘后固定价格成交
```

### 6. Doctor 数据自检

新增 `DATA_RULE_MISMATCH` 检查。

检查日期从 `20260706` 开始。

检查项：

- 主板 ST 的 `stk_limit` 是否接近 `pre_close * 1.10 / 0.90`。
- 普通主板是否仍为 10%。
- 创业板是否仍为 20%。
- ST 股票是否仍被硬过滤。
- 盘后固定价格数据是否可用。
- 数据源如果仍按 ST 5% 返回，标记 `DATA_RULE_MISMATCH`。

规则切换初期，第三方数据源可能口径不同步。若检查失败，当天报告应降级为观察。

### 7. 回测规则版本化

回测不能用 2026-07-06 后的新规则重算过去。

必须记录：

```text
rule_version_at_signal
rule_version_at_entry
rule_version_at_exit
```

分层统计：

```text
pre_20260706 表现
post_20260706 表现
BULL + pre_20260706
BULL + post_20260706
BEAR_GRIND + pre_20260706
BEAR_GRIND + post_20260706
REPAIR + pre_20260706
REPAIR + post_20260706
```

新参数不能只因为旧规则环境表现好就进入生产。

### 8. 日报输出

日报顶部新增：

```text
【新规兼容检查】

交易规则版本：2026-07-06
主板 ST 涨跌幅：10%
盘后固定价格交易：全部 A 股 / ETF
普通股情绪是否剔除 ST：是
数据源涨跌停价是否匹配新规：是 / 否
盘后固定价格数据：available / unavailable
系统动作：允许正常生成日报 / 降级为观察
```

日报中市场情绪拆成：

```text
普通股短线情绪
ST 投机情绪
```

### 9. 盘中 Replay

Replay CSV 后续可扩展：

```text
market_phase
regular_amount
post_close_amount
post_close_amount_ratio
```

V1 不必立刻重做 replay 数据源。第一版只要确保：

- `POST_CLOSE_FIXED_PRICE` 阶段不触发买入。
- 盘后固定价格成交不污染 `VolumeGate`。
- 报告说明盘后数据是否缺失。

### 10. Agent Evolution

Agent 调参必须按规则版本分层。

Agent proposal 必须包含：

```text
rule_version_evidence
pre_20260706_metrics
post_20260706_metrics
regular_amount_assumption
post_close_data_available
```

禁止：

- 用新规前收益证明新规后参数有效。
- 因 ST 活跃提高普通股仓位。
- 把盘后固定价格成交当作次日必买信号。

## 建议新增表或字段

最小改动优先。

新增表：

```text
trading_rules
post_close_activity
```

已有表建议增加字段：

```text
rule_version_at_signal
rule_regime_at_signal
market_regime_at_signal
regular_amount
post_close_amount
post_close_amount_ratio
post_close_data_available
core_market_emotion_score
st_speculation_score
```

如果第一版拿不到盘后固定价格成交数据，不要新建复杂数据管道。先写：

```text
post_close_data_available = 0
```

并在报告里降级说明。

## 版本建议

建议定义一个小版本：

```text
Trading X V1.3-NewRule
```

范围：

- `TradingRuleRegistry` 支持 2026-07-06 新规。
- ST 涨跌幅按日期版本化。
- ST 情绪从普通情绪中剥离。
- 盘后固定价格交易进入交易日历。
- 成交额拆分 `regular_amount / post_close_amount / total_amount`。
- `doctor` 增加 `DATA_RULE_MISMATCH` 检查。
- 报告新增“新规兼容检查”板块。

## 最小第一步

不要一开始做大。

第一步只做这些：

1. 新增 `trading_rules` 或等价规则注册表。
2. 涨跌停判断全部从规则注册表取。
3. ST 继续硬过滤，并从普通情绪统计中剥离。
4. 日报新增“新规兼容检查”。
5. `doctor` 检查 20260706 后 ST 涨跌停价是否匹配 10%。
6. 如果盘后成交数据不可用，明确输出 `post_close_data_available = 0`。

这一步完成后，再考虑 `post_close_activity_score` 和更细的盘后成交复盘。

## Must Not Have

- 不因 ST 10% 就把 ST 放入候选池。
- 不把 ST 连板当作普通空间高度。
- 不把 ST 活跃当作普通短线情绪增强。
- 不把盘后固定价格交易当作买入信号。
- 不让盘后成交额污染早盘 `VolumeGate`。
- 不用新规后的涨跌停规则回填旧历史。
- 不在数据源口径未确认时生成强买入建议。

## Sources

- User file: `C:\Users\Administrator\Desktop\A股新规.txt`
- 上交所修订发布《上海证券交易所交易规则》: https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20260424_10816474.shtml
- 深交所交易规则（2026 年修订）: https://docs.static.szse.cn/www/lawrules/rule/trade/current/W020260424690713155663.pdf
- 上海证券交易所交易规则（2026年修订）: https://www.sse.com.cn/lawandrules/sselawsrules2025/trade/universal/c/c_20260424_10816492.shtml
