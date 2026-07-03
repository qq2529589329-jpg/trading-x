from trading_x.theme_models import ThemeAggregate
from trading_x.theme_scoring import strength_scores
from trading_x.types import Confidence


def test_strength_scores_rank_each_theme_metric() -> None:
    aggregates = [
        ThemeAggregate(
            theme_name="机器人",
            member_count=10,
            up_count=8,
            limit_up_count=3,
            avg_pct_chg=5.2,
            total_amount=100000.0,
            candidate_count=2,
            confidence=Confidence.MEDIUM,
            core_symbols="300124.SZ",
        ),
        ThemeAggregate(
            theme_name="AI应用",
            member_count=8,
            up_count=2,
            limit_up_count=0,
            avg_pct_chg=-1.0,
            total_amount=10000.0,
            candidate_count=0,
            confidence=Confidence.MEDIUM,
            core_symbols="002230.SZ",
        ),
    ]

    scores = strength_scores(aggregates)

    assert scores == {"机器人": 100.0, "AI应用": 0.0}
