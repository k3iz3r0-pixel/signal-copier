"""Phase 2B parser engine (contracts + deterministic pipeline).

The frozen contract layer (design §5, §26.2) lives in :mod:`packages.parser.types`
and :mod:`packages.parser.enums`. The deterministic pipeline
(normalize → tokenize → extract → evaluate → resolve → build result) lives in
:mod:`packages.parser.pipeline`. The profile loader and effective-RuleSet
resolution (design §12.5) live in :mod:`packages.parser.profiles`. The static
regex safety layer (design §15) lives in :mod:`packages.parser.safety`. The
OUTPUT ADAPTER (design §25 step 5; IR → Signal / SignalInstruction /
non-signal) lives in :mod:`packages.parser.output_adapter`.

The parse outcome has exactly one owner: ``ParseResult.outcome`` (§13.3).
The ``derive_outcome(ir)`` helper is a Phase 3+ engine behaviour and is
intentionally not part of this contract layer; the outcome is computed
exactly once per parse, in the engine, and never re-derived from the IR.
"""

from packages.parser.enums import (
    AmbiguityKind,
    BlockSeparatorKind,
    CandidateSlot,
    ConditionKind,
    ConflictKind,
    Constraint,
    ContextReferenceKind,
    ContextRequirement,
    CorrelationRequestKind,
    DeleteBehavior,
    EditBehavior,
    FollowUpBehavior,
    FragmentState,
    MatcherKind,
    MediaKind,
    MessageEvent,
    OccurrenceSelection,
    ParseResultState,
    ReplyRequirement,
    ScopeKind,
    SemanticTarget,
    TokenCategory,
)
from packages.parser.output_adapter import (
    AdapterOutput,
    AdapterOutputKind,
    adapt_parse_result,
)
from packages.parser.pipeline import parse
from packages.parser.profiles import (
    ProfileLoadError,
    ProfileRuntime,
    load_profile,
)
from packages.parser.types import (
    Ambiguity,
    Anchor,
    BlockParse,
    Candidate,
    CandidateGraph,
    CanonicalParserIR,
    Condition,
    Conflict,
    ContextReference,
    CorrelationRequest,
    EditDelta,
    MatcherSpec,
    MatchEvidence,
    MessageBlock,
    MessageMetadata,
    NormalizedMessage,
    ParsedFragment,
    ParseResult,
    ProviderCapabilities,
    ProviderProfile,
    ProviderRule,
    RawMessage,
    RuleMatch,
    RuleSet,
    RuleSetResolutionError,
    ScopeSpec,
    SourceMap,
    SourceSpan,
    Token,
)

__all__ = [
    "AdapterOutput",
    "AdapterOutputKind",
    "Ambiguity",
    "AmbiguityKind",
    "Anchor",
    "BlockParse",
    "BlockSeparatorKind",
    "Candidate",
    "CandidateGraph",
    "CandidateSlot",
    "CanonicalParserIR",
    "Condition",
    "ConditionKind",
    "Conflict",
    "ConflictKind",
    "Constraint",
    "ContextReference",
    "ContextReferenceKind",
    "ContextRequirement",
    "CorrelationRequest",
    "CorrelationRequestKind",
    "DeleteBehavior",
    "EditBehavior",
    "EditDelta",
    "FollowUpBehavior",
    "FragmentState",
    "MatchEvidence",
    "MatcherKind",
    "MatcherSpec",
    "MediaKind",
    "MessageBlock",
    "MessageEvent",
    "MessageMetadata",
    "NormalizedMessage",
    "OccurrenceSelection",
    "ParseResult",
    "ParseResultState",
    "ParsedFragment",
    "ProfileLoadError",
    "ProfileRuntime",
    "ProviderCapabilities",
    "ProviderProfile",
    "ProviderRule",
    "RawMessage",
    "ReplyRequirement",
    "RuleMatch",
    "RuleSet",
    "RuleSetResolutionError",
    "ScopeKind",
    "ScopeSpec",
    "SemanticTarget",
    "SourceMap",
    "SourceSpan",
    "Token",
    "TokenCategory",
    "adapt_parse_result",
    "load_profile",
    "parse",
]
