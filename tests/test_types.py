from trading_x.types import CandidateGrade, Confidence, DataCapabilityLevel, StrategyType


def test_v1_enums_expose_required_values() -> None:
    assert DataCapabilityLevel.FULL == "FULL"
    assert DataCapabilityLevel.BASIC == "BASIC"
    assert DataCapabilityLevel.BASIC_WITH_THEME_FALLBACK == "BASIC_WITH_THEME_FALLBACK"
    assert DataCapabilityLevel.DEGRADED == "DEGRADED"
    assert Confidence.UNAVAILABLE == "UNAVAILABLE"
    assert StrategyType.A_SPACE_LEADER == "A_SPACE_LEADER"
    assert StrategyType.B_CAPACITY_LEADER == "B_CAPACITY_LEADER"
    assert CandidateGrade.A_STRONG == "A_STRONG"
    assert CandidateGrade.A_LITE == "A_LITE"
