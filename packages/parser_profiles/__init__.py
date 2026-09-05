"""Provider profile registry (design §12, §22.1, §25.6).

Profiles are PLAIN DATA. Adding provider #21 requires only a new data
module here plus fixtures — no engine change (extensibility acceptance
test, design §19, ADR 0011).
"""

from __future__ import annotations

from packages.parser.profiles import ProfileRuntime, load_profile

from .data.common import COMMON_RULE_SET
from .data.provider_001 import PROVIDER_001
from .data.provider_002 import PROVIDER_002
from .data.provider_003 import PROVIDER_003
from .data.provider_004 import PROVIDER_004
from .data.provider_005 import PROVIDER_005
from .data.provider_006 import PROVIDER_006
from .data.provider_007 import PROVIDER_007
from .data.provider_008 import PROVIDER_008
from .data.provider_009 import PROVIDER_009
from .data.provider_010 import PROVIDER_010
from .data.provider_011 import PROVIDER_011
from .data.provider_012 import PROVIDER_012
from .data.provider_013 import PROVIDER_013
from .data.provider_014 import PROVIDER_014
from .data.provider_015 import PROVIDER_015
from .data.provider_016 import PROVIDER_016
from .data.provider_017 import PROVIDER_017

RULE_SETS: dict[str, dict[str, object]] = {
    "common": COMMON_RULE_SET,
}

PROFILES: dict[str, dict[str, object]] = {
    "provider_001": PROVIDER_001,
    "provider_002": PROVIDER_002,
    "provider_003": PROVIDER_003,
    "provider_004": PROVIDER_004,
    "provider_005": PROVIDER_005,
    "provider_006": PROVIDER_006,
    "provider_007": PROVIDER_007,
    "provider_008": PROVIDER_008,
    "provider_009": PROVIDER_009,
    "provider_010": PROVIDER_010,
    "provider_011": PROVIDER_011,
    "provider_012": PROVIDER_012,
    "provider_013": PROVIDER_013,
    "provider_014": PROVIDER_014,
    "provider_015": PROVIDER_015,
    "provider_016": PROVIDER_016,
    "provider_017": PROVIDER_017,
}


def profile_names() -> tuple[str, ...]:
    return tuple(sorted(PROFILES))


def get_profile(name: str) -> ProfileRuntime:
    """Load (resolve + compile) a profile by name. Deterministic; fresh
    instance per call (no global cache — the parser stays pure, §4.4)."""
    if name not in PROFILES:
        raise KeyError(f"unknown provider profile {name!r}")
    return load_profile(PROFILES[name], RULE_SETS)


__all__ = ["PROFILES", "RULE_SETS", "get_profile", "profile_names"]
