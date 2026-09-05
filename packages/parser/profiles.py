"""Profile loading and deterministic effective-RuleSet resolution (§12.5).

Profiles are declared as plain data (dict) per design §22.1 and converted
into the frozen Phase 2A contracts. Any violation is a deterministic
profile load error (:class:`ProfileLoadError` with a stable ``code``); a
broken profile is rejected IN ITS ENTIRETY (§12.5).

The effective RuleSet is computed at profile load time (§12.5) and frozen
into a :class:`ProfileRuntime` together with all compiled artifacts
(§15.3: compiled once, never per message).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from packages.parser.enums import (
    ConditionKind,
    Constraint,
    DeleteBehavior,
    EditBehavior,
    FollowUpBehavior,
    MatcherKind,
    OccurrenceSelection,
    ReplyRequirement,
    ScopeKind,
    SemanticTarget,
)
from packages.parser.safety import (
    BIDI_CONTROL_CHARS,
    DASH_VARIANTS,
    MARKDOWN_CHARS,
    REPETITION_RUN_LIMIT,
    ZERO_WIDTH_CHARS,
    compile_safe,
)
from packages.parser.types import (
    Anchor,
    MatcherSpec,
    ProviderCapabilities,
    ProviderProfile,
    ProviderRule,
    RuleSet,
    RuleSetResolutionError,
    ScopeSpec,
)

SUPPORTED_PROFILE_VERSIONS = ("2B",)
SUPPORTED_DECIMAL_FORMATS = ("dot",)

_CAPABILITY_FLAGS = (
    "close_full",
    "close_half",
    "profit_close",
    "move_sl_breakeven",
    "remove_sl",
    "cancel_pending",
    "trigger_pending",
    "move_sl_number",
    "move_sl_conditional",
    "move_tp_conditional",
    "move_entry_conditional",
    "edit_handling",
    "delete_handling",
    "reply_required",
    "negative_keywords",
    "last_signal_execution",
    "trailing",
    "multi_signal",
    "multi_message",
)

_DECIMAL_FORMAT_PATTERNS = {
    "dot": r"\d{1,13}(?:\.\d{1,12})?",
}


class ProfileLoadError(ValueError):
    """Deterministic profile load error (§12.5); ``code`` is stable."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _as_str_list(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ProfileLoadError("invalid_profile_data", f"{name} must be a list")
    return tuple(value)


def _section_divider(value: object) -> str:
    """Validate one section divider (ADR 0013).

    Dividers match the NORMALIZED text (post whitespace-collapse), so a
    divider consisting only of whitespace could never match and always
    indicates a profile-authoring error; it is rejected at load time.
    """
    if not isinstance(value, str) or not value:
        raise ProfileLoadError(
            "invalid_profile_data", "section dividers must be non-empty strings"
        )
    if all(ch.isspace() for ch in value):
        raise ProfileLoadError(
            "invalid_profile_data",
            "section dividers must not be whitespace-only (dividers match "
            "whitespace-collapsed normalized text and could never match)",
        )
    return value


def _validate_divider_matchable(
    divider: str, field_separators: tuple[str, ...]
) -> None:
    """Reject dividers that message normalization would rewrite (ADR 0013,
    Phase 2F adversarial audit).

    Dividers match the NORMALIZED message text. The normalization pipeline
    (§5.5.1) deletes zero-width/bidi characters, NFKC-expands, strips
    markdown characters, collapses whitespace runs to single spaces, and
    canonicalizes separator characters. A declared divider that is not a
    fixed point of those character transforms can never match and would
    SILENTLY disable multi-block segmentation for the provider — a
    fail-open configuration error that must be rejected at load time.
    """
    text: list[str] = [
        ch
        for ch in divider
        if ch not in ZERO_WIDTH_CHARS and ch not in BIDI_CONTROL_CHARS
    ]
    text = [out for ch in text for out in unicodedata.normalize("NFKC", ch)]
    text = [ch for ch in text if ch not in MARKDOWN_CHARS]
    collapsed: list[str] = []
    for ch in text:
        if ch.isspace():
            if collapsed and collapsed[-1] == " ":
                continue
            collapsed.append(" ")
        else:
            collapsed.append(ch)
    text = collapsed
    if field_separators:
        canonical = field_separators[0]
        variants = {ch for sep in field_separators[1:] for ch in sep}
        variants.update(ch for ch in DASH_VARIANTS if ch != canonical)
        text = [out for ch in text for out in (canonical if ch in variants else ch)]
    run = 1
    for i, ch in enumerate(text):
        run = run + 1 if i and text[i - 1] == ch else 1
        if run > REPETITION_RUN_LIMIT:
            raise ProfileLoadError(
                "invalid_profile_data",
                f"section divider {divider!r} contains a character run that "
                f"normalization would truncate; use its post-normalization form",
            )
    if "".join(text) != divider:
        raise ProfileLoadError(
            "invalid_profile_data",
            f"section divider {divider!r} would be rewritten by message "
            f"normalization and could never match; declare its "
            f"post-normalization form instead",
        )


def build_rule_set(data: Mapping[str, Any], name: str) -> RuleSet:
    """Build a frozen :class:`RuleSet` from plain data (§7.2, §5.18)."""
    try:
        rules_data = data["rules"]
        if not isinstance(rules_data, (list, tuple)):
            raise ProfileLoadError(
                "invalid_profile_data", f"{name}.rules must be a list"
            )
        rules = tuple(
            build_rule(rule_data, f"{name}.rules[{i}]")
            for i, rule_data in enumerate(rules_data)
        )
        parent = data.get("parent")
        overrides: tuple[tuple[str, str], ...] = ()
        for o in data.get("overrides", ()):
            if not isinstance(o, (list, tuple)) or len(o) != 2:
                raise ProfileLoadError(
                    "invalid_profile_data",
                    f"{name}.overrides entries must be (rule_id, inherited_rule_id)",
                )
            overrides = overrides + ((str(o[0]), str(o[1])),)
        exclusions = _as_str_list(data.get("exclusions", ()), f"{name}.exclusions")
        return RuleSet(
            rules=rules, parent=parent, overrides=overrides, exclusions=exclusions
        )
    except RuleSetResolutionError as exc:
        raise ProfileLoadError(exc.code, str(exc)) from exc


def build_rule(data: Mapping[str, Any], origin: str) -> ProviderRule:
    """Build a frozen :class:`ProviderRule` from plain data (§7.2)."""
    try:
        matcher_data = data["matcher"]
        scope_data = data["scope"]
        matcher = MatcherSpec(
            kind=MatcherKind[matcher_data["kind"]],
            params=_kv_pairs(matcher_data.get("params", {})),
        )
        anchors = tuple(Anchor(text=str(a)) for a in scope_data.get("anchors", ()))
        scope = ScopeSpec(kind=ScopeKind[scope_data["kind"]], anchors=anchors)
        return ProviderRule(
            id=str(data["id"]),
            category=str(data["category"]),
            matcher=matcher,
            scope=scope,
            constraints=tuple(Constraint[c] for c in data.get("constraints", ())),
            target=SemanticTarget[data["target"]],
            priority=int(data["priority"]),
            occurrence=OccurrenceSelection[data.get("occurrence", "FIRST")],
        )
    except KeyError as exc:
        raise ProfileLoadError(
            "invalid_profile_data", f"{origin}: missing/unknown key {exc}"
        ) from exc


def _kv_pairs(raw: object) -> tuple[tuple[str, object], ...]:
    if isinstance(raw, Mapping):
        return tuple((str(k), v) for k, v in raw.items())
    if isinstance(raw, (list, tuple)):
        return tuple((str(k), v) for k, v in raw)
    raise ProfileLoadError("invalid_profile_data", "params must be a mapping")


def build_capabilities(data: Mapping[str, Any]) -> ProviderCapabilities:
    """Build :class:`ProviderCapabilities`; all 19 flags required (§5.16)."""
    kwargs: dict[str, bool] = {}
    for flag in _CAPABILITY_FLAGS:
        value = data.get(flag)
        if not isinstance(value, bool):
            raise ProfileLoadError(
                "invalid_profile_data", f"capability {flag!r} must be bool"
            )
        kwargs[flag] = value
    return ProviderCapabilities(**kwargs)


def resolve_effective_rule_sets(
    registry: Mapping[str, RuleSet], leaf_name: str
) -> tuple[ProviderRule, ...]:
    """Resolve ONE deterministic effective RuleSet (§12.5).

    Steps: single-parent linearization leaf→root, missing-parent and
    cycle detection, root→leaf fold (re-declaration overrides by id),
    cumulative exclusions, renamed masking overrides. Chain-level
    violations raise :class:`ProfileLoadError` with the §12.5 codes.
    """
    chain: list[str] = []
    seen: set[str] = set()
    current: str | None = leaf_name
    while current is not None:
        if current not in registry:
            raise ProfileLoadError(
                "rule_set_parent_missing", f"unknown RuleSet {current!r}"
            )
        if current in seen:
            raise ProfileLoadError("rule_set_cycle", f"cycle at RuleSet {current!r}")
        seen.add(current)
        chain.append(current)
        current = registry[current].parent

    effective: dict[str, ProviderRule] = {}
    excluded: set[str] = set()
    masked_targets: dict[str, str] = {}
    for name in reversed(chain):
        rule_set = registry[name]
        for rule_id in rule_set.exclusions:
            if rule_id not in effective:
                raise ProfileLoadError(
                    "exclusion_unknown_rule",
                    f"{name}: exclusion {rule_id!r} names no inherited rule",
                )
            excluded.add(rule_id)
            effective.pop(rule_id, None)
        for own_id, inherited_id in rule_set.overrides:
            if own_id not in {r.id for r in rule_set.rules}:
                raise ProfileLoadError(
                    "conflicting_override",
                    f"{name}: override rule {own_id!r} not declared in own rules",
                )
            if inherited_id not in effective:
                raise ProfileLoadError(
                    "conflicting_override",
                    f"{name}: override target {inherited_id!r} not inherited",
                )
            if inherited_id in masked_targets:
                raise ProfileLoadError(
                    "conflicting_override",
                    f"{name}: {inherited_id!r} masked more than once",
                )
            masked_targets[inherited_id] = own_id
            effective.pop(inherited_id, None)
        for rule in rule_set.rules:
            effective[rule.id] = rule

    return sort_effective_rules(tuple(effective.values()))


def sort_effective_rules(rules: tuple[ProviderRule, ...]) -> tuple[ProviderRule, ...]:
    """Deterministic evaluation order (§7.3): category groups lexicographic,
    then (priority ascending, rule_id lexicographic)."""
    return tuple(
        sorted(rules, key=lambda r: (r.category, r.priority, r.id)),
    )


@dataclass(frozen=True, slots=True)
class ProfileRuntime:
    """A fully loaded, compiled, resolved provider (§12.5, §15.3)."""

    profile: ProviderProfile
    effective_rules: tuple[ProviderRule, ...]
    tokenizer: Any
    rule_patterns: dict[str, Any]
    number_pattern: Any
    symbol_table: dict[str, str]
    keyword_texts: tuple[str, ...]
    override_pairs: tuple[tuple[str, str], ...]


def load_profile(
    profile_data: Mapping[str, Any], rule_set_registry: Mapping[str, Mapping[str, Any]]
) -> ProfileRuntime:
    """Validate, resolve (§12.5), and compile a provider profile."""
    provider_name = profile_data.get("provider_name")
    if not isinstance(provider_name, str) or not provider_name:
        raise ProfileLoadError("invalid_profile_data", "provider_name required")
    version = profile_data.get("version")
    if version not in SUPPORTED_PROFILE_VERSIONS:
        raise ProfileLoadError(
            "unsupported_profile_version",
            f"{provider_name}: version {version!r} not in {SUPPORTED_PROFILE_VERSIONS}",
        )
    decimal_format = profile_data.get("decimal_format")
    if decimal_format not in SUPPORTED_DECIMAL_FORMATS:
        raise ProfileLoadError(
            "unsupported_decimal_format",
            f"{provider_name}: decimal_format {decimal_format!r} not in "
            f"{SUPPORTED_DECIMAL_FORMATS}",
        )

    capabilities = build_capabilities(profile_data.get("capabilities", {}))

    own_rule_set_data = profile_data.get("rule_set", {})
    own_name = str(own_rule_set_data.get("name", provider_name))
    registry: dict[str, RuleSet] = {}
    for rs_name, rs_data in rule_set_registry.items():
        registry[str(rs_name)] = build_rule_set(rs_data, str(rs_name))
    registry[own_name] = build_rule_set(own_rule_set_data, own_name)

    try:
        profile = ProviderProfile(
            provider_name=provider_name,
            capabilities=capabilities,
            rule_set=registry[own_name],
            symbol_aliases=tuple(
                (str(a), str(s)) for a, s in profile_data.get("symbol_aliases", ())
            ),
            tokenizer_pattern=str(profile_data.get("tokenizer_pattern", "")),
            field_separators=_as_str_list(
                profile_data.get("field_separators", ()), "field_separators"
            ),
            multi_value_separators=_as_str_list(
                profile_data.get("multi_value_separators", ()),
                "multi_value_separators",
            ),
            decimal_format=str(decimal_format),
            range_patterns=_as_str_list(
                profile_data.get("range_patterns", ()), "range_patterns"
            ),
            multiline_mode=bool(profile_data.get("multiline_mode", False)),
            reply_requirement=ReplyRequirement[
                profile_data.get("reply_requirement", "NONE")
            ],
            edit_behavior=EditBehavior[
                profile_data.get("edit_behavior", "REPARSE_DELTA")
            ],
            delete_behavior=DeleteBehavior[
                profile_data.get("delete_behavior", "CANCEL_TARGET")
            ],
            follow_up_behavior=FollowUpBehavior[
                profile_data.get("follow_up_behavior", "TARGET_LAST_SIGNAL")
            ],
            version=str(version),
            max_message_length=int(profile_data.get("max_message_length", 8000)),
            max_numeric_value=Decimal(
                str(profile_data.get("max_numeric_value", "1e12"))
            ),
            section_dividers=tuple(
                _section_divider(d)
                for d in _as_str_list(
                    profile_data.get("section_dividers", ()), "section_dividers"
                )
            ),
        )
    except RuleSetResolutionError as exc:
        raise ProfileLoadError(exc.code, str(exc)) from exc

    # Dividers match NORMALIZED text: a divider rewritten by the fixed
    # normalization pipeline can never match and would silently disable
    # multi-block segmentation (ADR 0013, Phase 2F). Reject at load time.
    for divider in profile.section_dividers:
        _validate_divider_matchable(divider, profile.field_separators)

    tokenizer_pattern = profile.tokenizer_pattern or _default_tokenizer_pattern(
        profile.decimal_format
    )
    number_pattern = compile_safe(_DECIMAL_FORMAT_PATTERNS[profile.decimal_format])

    effective_rules = resolve_effective_rule_sets(registry, own_name)

    # Structural validation runs over the EFFECTIVE ruleset so inherited
    # (parent chain) rules are covered too.
    for rule in effective_rules:
        if rule.scope.kind in (ScopeKind.REPLY, ScopeKind.QUOTED_MESSAGE):
            raise ProfileLoadError(
                "unsupported_scope",
                f"{provider_name}: rule {rule.id!r} uses scope {rule.scope.kind} "
                "(replied-text parsing is a Phase 3+ correlation capability)",
            )
        if rule.target is SemanticTarget.CONDITION:
            kind_raw = dict(rule.matcher.params).get("condition_kind")
            if (
                not isinstance(kind_raw, str)
                or kind_raw not in ConditionKind.__members__
            ):
                raise ProfileLoadError(
                    "invalid_profile_data",
                    f"{provider_name}: condition rule {rule.id!r} must declare a "
                    "valid 'condition_kind' matcher param "
                    f"(one of {tuple(ConditionKind.__members__)})",
                )
        if rule.matcher.kind is MatcherKind.REGEX:
            pattern = dict(rule.matcher.params).get("pattern")
            if not isinstance(pattern, str):
                raise ProfileLoadError(
                    "invalid_profile_data",
                    f"{provider_name}: regex rule {rule.id!r} needs 'pattern'",
                )

    rule_patterns: dict[str, Any] = {}
    for rule in effective_rules:
        if rule.matcher.kind is MatcherKind.REGEX:
            pattern = str(dict(rule.matcher.params)["pattern"])
            flags = re.IGNORECASE if dict(rule.matcher.params).get("ignore_case") else 0
            rule_patterns[rule.id] = compile_safe(
                pattern if flags == 0 else f"(?i){pattern}"
            )
    tokenizer = compile_safe(tokenizer_pattern)
    keywords: set[str] = set()
    for rule in effective_rules:
        if rule.matcher.kind is MatcherKind.LITERAL:
            value = dict(rule.matcher.params).get("value")
            if isinstance(value, str):
                keywords.add(value)
        params = dict(rule.matcher.params)
        declared_keywords_value = params.get("keywords", ())
        declared_keywords_iter: tuple[object, ...] = (
            tuple(declared_keywords_value)
            if isinstance(declared_keywords_value, (list, tuple))
            else ()
        )
        for constraint_keyword in declared_keywords_iter:
            keywords.add(str(constraint_keyword))
        for anchor in rule.scope.anchors:
            keywords.add(anchor.text)
    keyword_texts = tuple(sorted(keywords))

    return ProfileRuntime(
        profile=profile,
        effective_rules=effective_rules,
        tokenizer=tokenizer,
        rule_patterns=rule_patterns,
        number_pattern=number_pattern,
        symbol_table={alias: symbol for alias, symbol in profile.symbol_aliases},
        keyword_texts=keyword_texts,
        override_pairs=tuple(profile.rule_set.overrides),
    )


def _default_tokenizer_pattern(decimal_format: str) -> str:
    number = _DECIMAL_FORMAT_PATTERNS[decimal_format]
    return rf"{number}|[A-Za-z]{{1,16}}|\s|[^\sA-Za-z0-9]"


__all__ = [
    "SUPPORTED_DECIMAL_FORMATS",
    "SUPPORTED_PROFILE_VERSIONS",
    "ProfileLoadError",
    "ProfileRuntime",
    "build_capabilities",
    "build_rule",
    "build_rule_set",
    "load_profile",
    "resolve_effective_rule_sets",
    "sort_effective_rules",
]
