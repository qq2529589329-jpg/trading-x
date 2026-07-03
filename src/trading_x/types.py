from enum import StrEnum


class DataCapabilityLevel(StrEnum):
    FULL = "FULL"
    BASIC = "BASIC"
    BASIC_WITH_THEME_FALLBACK = "BASIC_WITH_THEME_FALLBACK"
    DEGRADED = "DEGRADED"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNAVAILABLE = "UNAVAILABLE"


class StrategyType(StrEnum):
    A_SPACE_LEADER = "A_SPACE_LEADER"
    B_CAPACITY_LEADER = "B_CAPACITY_LEADER"


class CandidateGrade(StrEnum):
    A_STRONG = "A_STRONG"
    A_LITE = "A_LITE"
    B_CORE = "B_CORE"
    B_WATCH = "B_WATCH"
