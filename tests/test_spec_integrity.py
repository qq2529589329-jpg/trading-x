import re
from pathlib import Path


SPEC_PATH = Path("specs/002-intraday-replay-mvp/spec.md")


def test_spec_acceptance_scenarios_have_contiguous_numbers() -> None:
    spec = SPEC_PATH.read_text(encoding="utf-8")
    for block in spec.split("**Acceptance Scenarios**:")[1:]:
        scenario_text = block.split("### User Story", maxsplit=1)[0]
        scenario_text = scenario_text.split("## Requirements", maxsplit=1)[0]
        numbers = [
            int(number)
            for number in re.findall(
                r"^(\d+)\. \*\*Given\*\*",
                scenario_text,
                flags=re.MULTILINE,
            )
        ]

        assert numbers == list(range(1, len(numbers) + 1))


def test_spec_requirement_and_success_criteria_ids_are_contiguous() -> None:
    spec = SPEC_PATH.read_text(encoding="utf-8")
    for prefix in ("FR", "SC"):
        numbers = [
            int(number)
            for number in re.findall(rf"\*\*{prefix}-(\d+)\*\*", spec)
        ]

        assert numbers == list(range(1, len(numbers) + 1))
