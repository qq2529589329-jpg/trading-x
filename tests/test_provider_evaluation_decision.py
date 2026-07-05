from trading_x.provider_decision import (
    ComplianceUseStatus,
    ProviderEvaluationDecision,
    ProviderEvaluationEvidence,
    ProviderEvaluationStatus,
    decide_provider_evaluation,
)
from trading_x.provider_evaluation import (
    ProviderSnapshotSample,
    ProviderSource,
    ValidationStatus,
)


def _sample(
    ts_code: str = "300001.SZ",
    validation_status: ValidationStatus = ValidationStatus.ACCEPTED,
    reason_codes: tuple[str, ...] = (),
) -> ProviderSnapshotSample:
    return ProviderSnapshotSample(
        trade_date="20260704",
        quote_time="09:35:00",
        ts_code=ts_code,
        price=10.5,
        amount_since_open=1050000.0,
        volume_since_open=100000.0,
        bar_high=10.6,
        bar_low=10.1,
        source=ProviderSource.MOOTDX,
        latency_ms=25,
        validation_status=validation_status,
        reason_codes=reason_codes,
    )


def test_provider_volume_missing_disables_buy_trigger() -> None:
    evidence = ProviderEvaluationEvidence(
        requested_symbols=("300001.SZ",),
        samples=(
            _sample(
                validation_status=ValidationStatus.REJECTED,
                reason_codes=("PROVIDER_VOLUME_MISSING",),
            ),
        ),
        compliance_use_status=ComplianceUseStatus.APPROVED,
    )

    decision = decide_provider_evaluation(evidence)

    assert decision.status == ProviderEvaluationStatus.DISABLED_FOR_BUY_TRIGGER
    assert decision.reason_codes == ("PROVIDER_VOLUME_MISSING",)


def test_provider_timestamp_untrusted_disables_live_watch() -> None:
    evidence = ProviderEvaluationEvidence(
        requested_symbols=("300001.SZ",),
        samples=(_sample(),),
        compliance_use_status=ComplianceUseStatus.APPROVED,
        timestamp_order_trusted=False,
    )

    decision = decide_provider_evaluation(evidence)

    assert decision.status == ProviderEvaluationStatus.DISABLED_FOR_LIVE_WATCH
    assert decision.reason_codes == ("PROVIDER_TIMESTAMP_UNTRUSTED",)


def test_provider_partial_coverage_is_recorded_and_disabled() -> None:
    evidence = ProviderEvaluationEvidence(
        requested_symbols=("300001.SZ", "600001.SH"),
        samples=(_sample("300001.SZ"),),
        compliance_use_status=ComplianceUseStatus.APPROVED,
    )

    decision = decide_provider_evaluation(evidence)

    assert decision.status == ProviderEvaluationStatus.DISABLED_FOR_LIVE_WATCH
    assert decision.symbols_missing == ("600001.SH",)
    assert decision.reason_codes == ("PROVIDER_COVERAGE_PARTIAL",)


def test_provider_unknown_compliance_keeps_source_disabled() -> None:
    evidence = ProviderEvaluationEvidence(
        requested_symbols=("300001.SZ",),
        samples=(_sample(),),
        compliance_use_status=ComplianceUseStatus.UNKNOWN,
    )

    decision = decide_provider_evaluation(evidence)

    assert decision == ProviderEvaluationDecision(
        status=ProviderEvaluationStatus.DISABLED_FOR_LIVE_WATCH,
        reason_codes=("PROVIDER_COMPLIANCE_UNKNOWN",),
        symbols_missing=(),
    )
