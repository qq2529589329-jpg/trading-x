from datetime import datetime

from trading_x.capabilities import ApiCheckResult
from trading_x.tushare_adapter import TushareUnavailableError


class TushareCapabilityAdapter:
    def __init__(self, token: str) -> None:
        try:
            import tushare as ts
        except ImportError as exc:
            raise TushareUnavailableError("tushare is not installed") from exc
        self._pro = ts.pro_api(token)

    def check_api(self, api_name: str) -> ApiCheckResult:
        trade_date = datetime.now().strftime("%Y%m%d")
        try:
            match api_name:
                case "stock_basic":
                    self._pro.stock_basic(exchange="", list_status="L", fields="ts_code")
                case "trade_cal":
                    self._pro.trade_cal(exchange="", start_date=trade_date, end_date=trade_date)
                case "daily":
                    self._pro.daily(trade_date=trade_date)
                case "daily_basic":
                    self._pro.daily_basic(trade_date=trade_date)
                case "stk_limit":
                    self._pro.stk_limit(trade_date=trade_date)
                case "top_list":
                    self._pro.top_list(trade_date=trade_date)
                case "limit_cpt_list":
                    self._pro.limit_cpt_list(trade_date=trade_date)
                case "moneyflow":
                    self._pro.moneyflow(trade_date=trade_date)
                case "margin":
                    self._pro.margin(trade_date=trade_date)
                case _:
                    return ApiCheckResult(
                        api_name=api_name,
                        available=False,
                        error_code="unknown_api",
                        error_msg=f"{api_name} is not configured",
                    )
        except Exception as exc:
            return ApiCheckResult(
                api_name=api_name,
                available=False,
                error_code=exc.__class__.__name__,
                error_msg=str(exc),
            )
        return ApiCheckResult(api_name=api_name, available=True)
