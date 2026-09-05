"""Shared helpers for parser behaviour tests."""

from __future__ import annotations

from datetime import UTC, datetime

from packages.parser.enums import MessageEvent
from packages.parser.types import MessageMetadata, RawMessage
from packages.parser_profiles import get_profile
from packages.signal_core.enums import SourceType


def make_runtime(provider_name: str):
    return get_profile(provider_name)


def make_raw(text: str) -> RawMessage:
    return RawMessage(raw_text=text, media_refs=(), raw_payload_hash="")


def make_metadata(provider_name: str, event: MessageEvent = MessageEvent.CREATE) -> MessageMetadata:
    return MessageMetadata(
        provider_name=provider_name,
        source_type=SourceType.TELEGRAM,
        timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        message_event=event,
    )