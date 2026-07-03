# Quickstart: AI 龙头选股系统 V1

## 1. Environment

```powershell
uv sync
$env:TUSHARE_TOKEN = "set-token-locally"
```

Do not paste tokens into chat, reports, commits, or logs.

## 2. Initialize Database

```powershell
python -m trading_x init-db
```

Expected result:

- Creates `data/trading_x.db`.
- Creates all V1 tables, including inactive `trade_logs`.

## 3. Run Capability Doctor

```powershell
python -m trading_x doctor
```

Expected result:

- Prints available APIs.
- Prints unavailable APIs.
- Prints fallback modes.
- Prints report capability: `FULL`, `BASIC`, or `DEGRADED`.
- Writes `data_capabilities`.

## 4. Update Daily Data

```powershell
python -m trading_x update --date 20260701
```

Expected result:

- Loads P0 market data when available.
- Records limit prices in `stk_limit_prices`.
- Does not fabricate limit event fields from `stk_limit`.

## 5. Generate Report

```powershell
python -m trading_x report --date 20260701
```

Expected files:

```text
reports/20260701_report.json
reports/20260701_report.md
```

Expected behavior:

- `DEGRADED`: no candidates, clear missing P0 reason.
- `BASIC`: candidates allowed, confidence downgrades shown.
- `FULL`: candidates allowed with normal confidence labels.

## 6. Run Tests

```powershell
pytest
```

Required V1 coverage:

- Doctor with missing token.
- Doctor with partial API permissions.
- P0 missing blocks candidates.
- P1 missing downgrades confidence.
- P2 missing does not block reports.
- A-class downgrade to `A_LITE`.
- Theme confidence downgrade.
- 10 consecutive no-candidate trading-day reports.
- JSON file equals SQLite report snapshot.
