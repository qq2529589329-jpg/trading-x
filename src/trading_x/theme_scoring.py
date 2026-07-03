from collections.abc import Callable, Sequence

from trading_x.theme_models import ThemeAggregate


def strength_scores(aggregates: Sequence[ThemeAggregate]) -> dict[str, float]:
    limit_scores = _rank_scores(aggregates, lambda item: item.weighted_limit_up_count)
    avg_scores = _rank_scores(aggregates, lambda item: item.weighted_avg_pct_chg)
    amount_scores = _rank_scores(aggregates, lambda item: item.weighted_total_amount)
    candidate_scores = _rank_scores(aggregates, lambda item: item.candidate_count)
    return {
        item.theme_name: round(
            limit_scores[item.theme_name] * 0.35
            + avg_scores[item.theme_name] * 0.25
            + amount_scores[item.theme_name] * 0.25
            + candidate_scores[item.theme_name] * 0.15,
            2,
        )
        for item in aggregates
    }


def _rank_scores(
    aggregates: Sequence[ThemeAggregate],
    value: Callable[[ThemeAggregate], float],
) -> dict[str, float]:
    if len(aggregates) == 1:
        return {aggregates[0].theme_name: 100.0}
    ordered = sorted(aggregates, key=value, reverse=True)
    scale = len(ordered) - 1
    return {
        item.theme_name: round((scale - index) / scale * 100, 2)
        for index, item in enumerate(ordered)
    }
