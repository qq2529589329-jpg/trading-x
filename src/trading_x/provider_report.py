from dataclasses import dataclass
from pathlib import Path
import json

from trading_x.provider_decision import (
    ProviderEvaluationDecision,
    ProviderEvaluationEvidence,
)


@dataclass(frozen=True, slots=True)
class ProviderEvaluationArtifacts:
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True, slots=True)
class ProviderEvaluationReport:
    trade_date: str
    source: str
    requested_symbols: tuple[str, ...]
    symbols_covered: tuple[str, ...]
    symbols_missing: tuple[str, ...]
    sample_count: int
    compliance_use_status: str
    timestamp_order_trusted: bool
    decision: str
    reason_codes: tuple[str, ...]

    def to_json_text(self) -> str:
        payload = {
            "trade_date": self.trade_date,
            "source": self.source,
            "requested_symbols": list(self.requested_symbols),
            "symbols_covered": list(self.symbols_covered),
            "symbols_missing": list(self.symbols_missing),
            "sample_count": self.sample_count,
            "compliance_use_status": self.compliance_use_status,
            "timestamp_order_trusted": self.timestamp_order_trusted,
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    def to_markdown_text(self) -> str:
        lines = [
            f"# Provider Evaluation: {self.source} {self.trade_date}",
            "",
            f"- decision: {self.decision}",
            f"- reason_codes: {', '.join(self.reason_codes)}",
            f"- requested_symbols: {', '.join(self.requested_symbols)}",
            f"- symbols_covered: {', '.join(self.symbols_covered)}",
            f"- symbols_missing: {', '.join(self.symbols_missing)}",
            f"- sample_count: {self.sample_count}",
            f"- compliance_use_status: {self.compliance_use_status}",
            f"- timestamp_order_trusted: {self.timestamp_order_trusted}",
            "",
        ]
        return "\n".join(lines)


def write_provider_evaluation_report(
    output_dir: Path,
    evidence: ProviderEvaluationEvidence,
    decision: ProviderEvaluationDecision,
) -> ProviderEvaluationArtifacts:
    sample = evidence.samples[0]
    stem = f"{sample.trade_date}_{sample.source}_provider_evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"

    report = ProviderEvaluationReport(
        trade_date=sample.trade_date,
        source=sample.source,
        requested_symbols=evidence.requested_symbols,
        symbols_covered=tuple(sorted({item.ts_code for item in evidence.samples})),
        symbols_missing=decision.symbols_missing,
        sample_count=len(evidence.samples),
        compliance_use_status=evidence.compliance_use_status,
        timestamp_order_trusted=evidence.timestamp_order_trusted,
        decision=decision.status,
        reason_codes=decision.reason_codes,
    )
    json_path.write_text(report.to_json_text(), encoding="utf-8")
    markdown_path.write_text(report.to_markdown_text(), encoding="utf-8")
    return ProviderEvaluationArtifacts(json_path=json_path, markdown_path=markdown_path)