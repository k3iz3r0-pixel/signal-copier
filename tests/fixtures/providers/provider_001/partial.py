"""NO_SIGNAL and PARTIAL outcomes for provider_001."""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "empty_message",
        "raw_text": "",
        "outcome": "NO_SIGNAL",
    },
    {
        "name": "chat_text",
        "raw_text": "hello everyone how are you today",
        "outcome": "NO_SIGNAL",
    },
    {
        "name": "direction_only_partial",
        "raw_text": "BUY",
        "outcome": "PARTIAL",
        "fragments": {"DIRECTION": "BUY"},
        "unresolved": ["ENTRY", "ENTRY_GEOMETRY", "ENTRY_TRIGGER"],
    },
)