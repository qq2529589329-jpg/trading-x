from collections.abc import Collection
from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn


class ProviderSource(StrEnum):
    MOOTDX = "mootdx"
    TENCENT_SNAPSHOT = "tencent_snapshot"


class ProviderSourceDisabledError(RuntimeError):
    reason_code: str

    def __init__(self, source: ProviderSource) -> None:
        self.reason_code = f"PROVIDER_SOURCE_DISABLED: {source}"
        super().__init__(self.reason_code)


@dataclass(frozen=True, slots=True)
class DisabledProviderAdapter:
    source: ProviderSource

    def snapshots(self, symbols: Collection[str]) -> NoReturn:
        raise ProviderSourceDisabledError(self.source)
