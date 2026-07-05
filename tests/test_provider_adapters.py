from pathlib import Path

import pytest

from trading_x.provider_adapters import (
    DisabledProviderAdapter,
    ProviderSource,
    ProviderSourceDisabledError,
)


def test_mootdx_adapter_boundary_stays_disabled() -> None:
    adapter = DisabledProviderAdapter(ProviderSource.MOOTDX)

    with pytest.raises(ProviderSourceDisabledError) as error:
        adapter.snapshots(("300001.SZ",))

    assert error.value.reason_code == "PROVIDER_SOURCE_DISABLED: mootdx"


def test_tencent_snapshot_adapter_boundary_stays_disabled() -> None:
    adapter = DisabledProviderAdapter(ProviderSource.TENCENT_SNAPSHOT)

    with pytest.raises(ProviderSourceDisabledError) as error:
        adapter.snapshots(("300001.SZ",))

    assert error.value.reason_code == "PROVIDER_SOURCE_DISABLED: tencent_snapshot"


def test_watch_runtime_does_not_import_disabled_provider_sources() -> None:
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            Path("src/trading_x/cli.py"),
            Path("src/trading_x/intraday_watch.py"),
        )
    )

    assert "provider_adapters" not in source_text
    assert "ProviderSource" not in source_text


def test_provider_evaluation_runbook_documents_manual_command() -> None:
    runbook = Path("specs/004-real-provider-evaluation/provider-evaluation-runbook.md")

    text = runbook.read_text(encoding="utf-8")

    assert (
        "uv run python -m trading_x provider-evaluate --source mootdx "
        "--date YYYYMMDD --symbols 300001.SZ,600001.SH"
    ) in text
