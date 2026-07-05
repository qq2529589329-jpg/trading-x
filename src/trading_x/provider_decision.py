from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, assert_never

from trading_x.provider_evaluation import ProviderSnapshotSample


_LIVE_WATCH_BLOCKING_REASONS: Final = frozenset(
    {
        "PROVIDER_TIMESTAMP_UNTRUSTED",
        "PROVIDER_COVERAGE_PARTIAL",
        "PROVIDER_COMPLIANCE_REJECTED",
        "PROVIDER_COMPLIANCE_UNKNOWN",
    }
)


class ComplianceUseStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class ProviderEvaluationStatus(StrEnum):
    DISABLED_FOR_LIVE_WATCH = "disabled_for_live_watch"
    DISABLED_FOR_BUY_TRIGGER = "disabled_for_buy_trigger"
    CANDIDATE_ONLY = "candidate_only"


@dataclass(frozen=True, slots=True)
class ProviderEvaluationEvidence:
    requested_symbols: tuple[str, ...]
    samples: tuple[ProviderSnapshotSample, ...]
    compliance_use_status: ComplianceUseStatus
    timestamp_order_trusted: bool = True


@dataclass(frozen=True, slots=True)
class ProviderEvaluationDecision:
    status: ProviderEvaluationStatus
    reason_codes: tuple[str, ...]
    symbols_missing: tuple[str, ...]


def decide_provider_evaluation(
    evidence: ProviderEvaluationEvidence,
) -> ProviderEvaluationDecision:
    symbols_seen = {sample.ts_code for sample in evidence.samples}
    symbols_missing = tuple(
        symbol for symbol in evidence.requested_symbols if symbol not in symbols_seen
    )
    reason_codes = _reason_codes(evidence, symbols_missing)

    if _has_live_watch_blocker(reason_codes):
        status = ProviderEvaluationStatus.DISABLED_FOR_LIVE_WATCH
    elif "PROVIDER_VOLUME_MISSING" in reason_codes:
        status = ProviderEvaluationStatus.DISABLED_FOR_BUY_TRIGGER
    else:
        status = ProviderEvaluationStatus.CANDIDATE_ONLY

    return ProviderEvaluationDecision(
        status=status,
        reason_codes=reason_codes,
        symbols_missing=symbols_missing,
    )


def _reason_codes(
    evidence: ProviderEvaluationEvidence,
    symbols_missing: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not evidence.timestamp_order_trusted:
        reasons.append("PROVIDER_TIMESTAMP_UNTRUSTED")
    if symbols_missing:
        reasons.append("PROVIDER_COVERAGE_PARTIAL")

    match evidence.compliance_use_status:
        case ComplianceUseStatus.APPROVED:
            pass
        case ComplianceUseStatus.REJECTED:
            reasons.append("PROVIDER_COMPLIANCE_REJECTED")
        case ComplianceUseStatus.UNKNOWN:
            reasons.append("PROVIDER_COMPLIANCE_UNKNOWN")
        case unreachable:
            assert_never(unreachable)

    reasons.extend(_sample_reason_codes(evidence.samples))
    return tuple(dict.fromkeys(reasons))


def _sample_reason_codes(samples: Iterable[ProviderSnapshotSample]) -> tuple[str, ...]:
    reasons: list[str] = []
    for sample in samples:
        reasons.extend(sample.reason_codes)
    return tuple(reasons)


def _has_live_watch_blocker(reason_codes: tuple[str, ...]) -> bool:
    return bool(_LIVE_WATCH_BLOCKING_REASONS.intersection(reason_codes))
