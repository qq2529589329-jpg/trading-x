# Provider Evaluation Runbook

## Current Boundary

Real provider adapters remain disabled in this specification. `watch` still uses fake replay-style input only.

## Manual Evaluation Command

When network/source access is available in a later implementation, run provider evaluation explicitly:

```powershell
uv run python -m trading_x provider-evaluate --source mootdx --date YYYYMMDD --symbols 300001.SZ,600001.SH
uv run python -m trading_x provider-evaluate --source tencent_snapshot --date YYYYMMDD --symbols 300001.SZ,600001.SH
```

The command must write provider evaluation artifacts only. It must not write `intraday_alerts`, `intraday_alert_locks`, `intraday_plans`, orders, positions, or watch alerts.
