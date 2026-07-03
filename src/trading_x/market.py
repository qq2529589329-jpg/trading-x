from trading_x.candidate_models import CandidateReport
from trading_x.types import Confidence, DataCapabilityLevel


def market_status(
    level: DataCapabilityLevel,
    candidates: list[CandidateReport],
) -> str:
    if level == DataCapabilityLevel.DEGRADED:
        return "数据不足"
    if candidates:
        return "观察"
    return "弱"


def report_theme_confidence(
    candidates: list[CandidateReport],
    unavailable_apis: set[str],
) -> Confidence:
    if candidates:
        return Confidence(candidates[0].theme_confidence)
    return Confidence.LOW if "limit_cpt_list" in unavailable_apis else Confidence.MEDIUM
