from pathlib import Path
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError


CONTRACT_PATH = (
    Path(__file__).parents[1]
    / "specs"
    / "001-ai-stock-selection-v1"
    / "contracts"
    / "agent-proposal-schema.json"
)


def test_agent_proposal_contract_accepts_rule_version_split_evidence() -> None:
    payload = _proposal()

    _validator().validate(payload)


def test_agent_proposal_contract_requires_post_rule_metrics() -> None:
    payload = _proposal()
    del payload["post_20260706_metrics"]

    with pytest.raises(ValidationError):
        _validator().validate(payload)


def test_agent_proposal_contract_requires_post_close_data_assumption() -> None:
    payload = _proposal()
    del payload["post_close_data_available"]

    with pytest.raises(ValidationError):
        _validator().validate(payload)


def _validator() -> Draft202012Validator:
    schema = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _proposal() -> dict[str, str | bool | dict[str, float]]:
    return {
        "proposal_id": "proposal-001",
        "rule_version_evidence": "split_by_rule_version",
        "pre_20260706_metrics": {"sample_count": 20.0, "win_rate": 0.55},
        "post_20260706_metrics": {"sample_count": 5.0, "win_rate": 0.4},
        "regular_amount_assumption": "VolumeGate uses regular session amount only",
        "post_close_data_available": False,
        "recommendation": "review_only",
    }
