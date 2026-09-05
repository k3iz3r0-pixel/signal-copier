"""Parser engine safety layer (design §15, §16; ADR 0007).

Static regex safety is the PRIMARY guarantee: patterns are validated at
PROFILE LOAD TIME, never at parse time. Only patterns that pass
:func:`check_pattern_safe` are compiled (:func:`compile_safe`).

The validator is a STRUCTURAL safety analysis, not a blacklist. It parses
the pattern into a syntax tree and rejects every combination that can
produce unbounded backtracking:

* nested unbounded quantifiers (``(a+)+``, ``(a*)*``);
* a variable-width quantifier (``?``, ``*``, ``+``, ``{m,n}`` with
  ``m != n``) inside an unbounded-quantified operand — the iteration
  boundaries become ambiguous (``(?:ab?)*c``);
* an operand that can match empty under an unbounded quantifier
  (``(?:a|)*``);
* an ambiguous alternation anywhere inside an unbounded-quantified
  operand: two branches whose FIRST sets overlap (``(a|a)*b``,
  ``(?:ab|a)*c``), whose FIRST sets are statically unknown (character
  classes, ``.``, escapes such as ``\\d`` — rejected conservatively), or
  which can match empty.

Fixed-width quantifiers (``{k}``) are allowed inside unbounded operands:
every iteration consumes exactly ``k`` characters, so the split of the
input across iterations is unique and backtracking stays linear.

The analysis is intentionally conservative: when a first-set is not
statically computable, the pattern is rejected. False rejections are
safe (§15.3: only patterns that pass are compiled).

The parser does NOT promise a hard wall-clock preemption of a running
``re`` call (§15.5). The guarantee is deterministic bounded work: static
pattern safety + bounded input + the count bounds declared here.
"""

from __future__ import annotations

import re

# Engine-level deterministic bounds (design §15.3; defaults documented there).
MAX_NUMERIC_TOKENS_PER_MESSAGE = 64
MAX_NUMERIC_TOKENS_PER_FIELD = 16
MAX_RULE_MATCHES = 200
MAX_CANDIDATES = 256
REPETITION_RUN_LIMIT = 4096
MAX_PATTERN_LENGTH = 256
MAX_DIGIT_RUN = 13

# Fixed normalization character classes (§5.5.1). Shared by the message
# normalizer (pipeline) and by section-divider load-time validation
# (profiles): a declared divider must be a fixed point of these transforms,
# otherwise it can never match normalized text (ADR 0013, Phase 2F).
ZERO_WIDTH_CHARS = frozenset("\u200b\u200c\u200d\ufeff")
BIDI_CONTROL_CHARS = frozenset("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")
MARKDOWN_CHARS = frozenset("*_`~[]#>|")
DASH_VARIANTS = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"


class UnsafePatternError(ValueError):
    """A regex pattern outside the statically-safe subset (design §15.3)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# ---------------------------------------------------------------------------
# Structural pattern AST (analysis-only; never executed)
# ---------------------------------------------------------------------------

_EPS = "\u0000__EPS__"


class _Node:
    __slots__ = ()


class _Literal(_Node):
    __slots__ = ("char",)

    def __init__(self, char: str) -> None:
        self.char = char


class _Unknown(_Node):
    """An element whose first set is statically unknown (class, dot, escape)."""

    __slots__ = ()


class _Empty(_Node):
    """An element that matches the empty string (anchor, inline flags)."""

    __slots__ = ()


class _Sequence(_Node):
    __slots__ = ("elements",)

    def __init__(self, elements: tuple[_Node, ...]) -> None:
        self.elements = elements


class _Alternation(_Node):
    __slots__ = ("branches",)

    def __init__(self, branches: tuple[_Sequence, ...]) -> None:
        self.branches = branches


class _Group(_Node):
    """capturing | non_capturing | positive/negative lookahead.

    Lookahead groups are zero-width (they can be empty); other groups
    recurse into their body for emptiness/first-set purposes.
    """

    __slots__ = ("body", "zero_width")

    def __init__(self, body: _Alternation | _Sequence, zero_width: bool) -> None:
        self.body = body
        self.zero_width = zero_width


class _Quantified(_Node):
    """``operand`` repeated ``min_req``..``max_req`` times; max_req=None is
    unbounded. ``lazy``/``possessive`` modifiers are recorded and ignored
    (they change preference order, not the safety shape)."""

    __slots__ = ("max_req", "min_req", "operand")

    def __init__(self, operand: _Node, min_req: int, max_req: int | None) -> None:
        self.operand = operand
        self.min_req = min_req
        self.max_req = max_req


class _PatternParser:
    """Recursive-descent parser for the structural subset of ``re`` syntax.

    It never executes the pattern; unknown constructs raise
    :class:`UnsafePatternError` (conservative rejection).
    """

    def __init__(self, pattern: str) -> None:
        self._pattern = pattern
        self._pos = 0

    def parse(self) -> _Alternation:
        result = self._parse_alternation()
        if self._pos != len(self._pattern):
            raise UnsafePatternError(f"unparsed trailing input at index {self._pos}")
        return result

    # -- helpers ------------------------------------------------------------

    def _peek(self) -> str | None:
        if self._pos < len(self._pattern):
            return self._pattern[self._pos]
        return None

    def _take(self) -> str:
        ch = self._pattern[self._pos]
        self._pos += 1
        return ch

    # -- grammar ------------------------------------------------------------

    def _parse_alternation(self) -> _Alternation:
        branches: list[_Sequence] = [self._parse_sequence()]
        while self._peek() == "|":
            self._take()
            branches.append(self._parse_sequence())
        return _Alternation(tuple(branches))

    def _parse_sequence(self) -> _Sequence:
        elements: list[_Node] = []
        while True:
            ch = self._peek()
            if ch is None or ch in "|)":
                break
            elements.append(self._parse_element())
        return _Sequence(tuple(elements))

    def _parse_element(self) -> _Node:
        atom = self._parse_atom()
        return self._parse_quantifiers(atom)

    def _parse_quantifiers(self, atom: _Node) -> _Node:
        node = atom
        quantified = False
        while True:
            ch = self._peek()
            if ch == "*":
                self._take()
                node = _Quantified(node, 0, None)
                quantified = True
            elif ch == "+":
                self._take()
                node = _Quantified(node, 1, None)
                quantified = True
            elif ch == "?":
                self._take()
                node = _Quantified(node, 0, 1)
                quantified = True
            elif ch == "{":
                min_req, max_req = self._parse_bound()
                node = _Quantified(node, min_req, max_req)
                quantified = True
            else:
                return node
            # at most ONE lazy/possessive modifier may follow a quantifier
            nxt = self._peek()
            if nxt in ("?", "+"):
                self._take()
                nxt = self._peek()
            if quantified and nxt in ("*", "+", "?", "{"):
                raise UnsafePatternError(
                    f"multiple quantifiers on one operand at index {self._pos}"
                )

    def _parse_bound(self) -> tuple[int, int | None]:
        end = self._pattern.find("}", self._pos)
        if end == -1:
            raise UnsafePatternError("unterminated { quantifier")
        body = self._pattern[self._pos + 1 : end]
        self._pos = end + 1
        parts = body.split(",")
        if not 1 <= len(parts) <= 2 or body == "":
            raise UnsafePatternError(f"invalid quantifier bound {body!r}")
        try:
            lo = int(parts[0]) if parts[0].strip() != "" else 0
            hi: int | None = (
                int(parts[1]) if len(parts) == 2 and parts[1].strip() != "" else None
            )
        except ValueError:
            raise UnsafePatternError(f"invalid quantifier bound {body!r}") from None
        if lo < 0 or (hi is not None and hi < lo):
            raise UnsafePatternError(f"invalid quantifier bound {body!r}")
        if len(parts) == 1:
            return lo, lo  # {k} — fixed width
        return lo, hi

    def _parse_atom(self) -> _Node:
        ch = self._take()
        if ch == "(":
            return self._parse_group()
        if ch == "\\":
            return self._parse_escape()
        if ch == "[":
            return self._parse_class()
        if ch == ".":
            return _Unknown()
        if ch in "^$":
            return _Empty()
        if ch in "*+?":
            raise UnsafePatternError(f"quantifier {ch!r} with no operand")
        if ch in "){":
            raise UnsafePatternError(f"unexpected {ch!r}")
        return _Literal(ch)

    def _parse_group(self) -> _Node:
        if self._peek() == "?":
            self._take()
            nxt = self._peek()
            if nxt is None:
                raise UnsafePatternError("unterminated group")
            if nxt == ":":
                self._take()
                return self._parse_group_body("non_capturing")
            if nxt == "P":
                self._take()
                third = self._peek()
                if third == "<":
                    self._take()
                    while self._peek() not in (">", None):
                        self._take()
                    if self._peek() != ">":
                        raise UnsafePatternError("unterminated named group")
                    self._take()
                    return self._parse_group_body("capturing")
                raise UnsafePatternError("unsupported (?P...) construct")
            if nxt == "=":
                self._take()
                return self._parse_group_body("lookahead_positive")
            if nxt == "!":
                self._take()
                return self._parse_group_body("lookahead_negative")
            if nxt == "#":
                while self._peek() not in (")", None):
                    self._take()
                if self._peek() != ")":
                    raise UnsafePatternError("unterminated comment group")
                self._take()
                return _Empty()
            # inline flags: (?i) / (?i:...) / (?im-sx:...)
            flag_chars: list[str] = []
            while self._peek() not in (")", ":", None):
                flag_chars.append(self._take())
            marker = self._peek()
            if marker == ")":
                self._take()
                return _Empty()
            if marker == ":":
                self._take()
                return self._parse_group_body("non_capturing")
            raise UnsafePatternError("unsupported inline flag construct")
        return self._parse_group_body("capturing")

    def _parse_group_body(self, kind: str) -> _Node:
        body = self._parse_alternation()
        if self._peek() != ")":
            raise UnsafePatternError("unterminated group")
        self._take()
        return _Group(body, kind.startswith("lookahead"))

    def _parse_escape(self) -> _Node:
        if self._pos >= len(self._pattern):
            raise UnsafePatternError("dangling escape")
        ch = self._take()
        if ch.isdigit():
            raise UnsafePatternError("backreferences are forbidden")
        if ch in "dDwWsS":
            return _Unknown()
        if ch in "bBAZz":
            return _Empty()
        if ch == "x" and self._pattern[self._pos : self._pos + 2] != "":
            hex_digits = self._pattern[self._pos : self._pos + 2]
            self._pos += 2
            try:
                return _Literal(chr(int(hex_digits, 16)))
            except ValueError:
                raise UnsafePatternError("invalid \\x escape") from None
        if ch == "u" and len(self._pattern) - self._pos >= 4:
            hex_digits = self._pattern[self._pos : self._pos + 4]
            self._pos += 4
            try:
                return _Literal(chr(int(hex_digits, 16)))
            except ValueError:
                raise UnsafePatternError("invalid \\u escape") from None
        return _Literal(ch)

    def _parse_class(self) -> _Node:
        start = self._pos
        while self._pos < len(self._pattern):
            ch = self._pattern[self._pos]
            if ch == "\\":
                self._pos += 2
                continue
            if ch == "]":
                self._pos += 1
                return _Unknown()
            self._pos += 1
        raise UnsafePatternError(f"unterminated character class at {start - 1}")


# ---------------------------------------------------------------------------
# FIRST-set / emptiness analysis
# ---------------------------------------------------------------------------


def _can_be_empty(node: _Node) -> bool:
    if isinstance(node, (_Literal, _Unknown)):
        return False
    if isinstance(node, _Empty):
        return True
    if isinstance(node, _Sequence):
        return all(_can_be_empty(el) for el in node.elements)
    if isinstance(node, _Alternation):
        return any(_can_be_empty(b) for b in node.branches)
    if isinstance(node, _Group):
        return node.zero_width or _can_be_empty(node.body)
    if isinstance(node, _Quantified):
        return node.min_req == 0 or _can_be_empty(node.operand)
    return False


def _first(node: _Node) -> tuple[set[str] | None, bool]:
    """Return (first_atoms, can_be_empty).

    ``first_atoms is None`` means statically UNKNOWN (conservative). Atoms
    are literal characters. ``can_be_empty`` mirrors :func:`_can_be_empty`.
    """
    if isinstance(node, _Literal):
        return ({node.char}, False)
    if isinstance(node, _Unknown):
        return (None, False)
    if isinstance(node, _Empty):
        return (set(), True)
    if isinstance(node, _Sequence):
        atoms: set[str] | None = set()
        eps = True
        for el in node.elements:
            if not eps:
                break
            el_atoms, el_eps = _first(el)
            if atoms is None or el_atoms is None:
                atoms = None
            else:
                atoms = atoms | el_atoms
            eps = el_eps
        return (atoms, eps)
    if isinstance(node, _Alternation):
        union: set[str] | None = set()
        eps = False
        for branch in node.branches:
            b_atoms, b_eps = _first(branch)
            if union is None or b_atoms is None:
                union = None
            else:
                union = union | b_atoms
            eps = eps or b_eps
        return (union, eps)
    if isinstance(node, _Group):
        if isinstance(node.body, _Alternation):
            return _first(node.body)
        # lookahead bodies are zero-width assertions
        return _first(node.body)
    if isinstance(node, _Quantified):
        atoms, eps = _first(node.operand)
        return (atoms, eps or node.min_req == 0)
    return (None, False)


def _contains_unbounded(node: _Node) -> bool:
    if isinstance(node, _Quantified):
        if node.max_req is None:
            return True
        return _contains_unbounded(node.operand)
    if isinstance(node, _Sequence):
        return any(_contains_unbounded(el) for el in node.elements)
    if isinstance(node, _Alternation):
        return any(_contains_unbounded(b) for b in node.branches)
    if isinstance(node, _Group):
        return _contains_unbounded(node.body)
    return False


def _contains_variable_width(node: _Node) -> bool:
    """True when the tree contains any quantifier whose min != max."""
    if isinstance(node, _Quantified):
        if node.min_req != node.max_req:
            return True
        return _contains_variable_width(node.operand)
    if isinstance(node, _Sequence):
        return any(_contains_variable_width(el) for el in node.elements)
    if isinstance(node, _Alternation):
        return any(_contains_variable_width(b) for b in node.branches)
    if isinstance(node, _Group):
        return _contains_variable_width(node.body)
    return False


def _alternation_is_ambiguous(alt: _Alternation, ignore_case: bool) -> bool:
    """True when two branches of ``alt`` can start with the same input.

    Branch FIRST sets that are statically unknown, overlap, or include the
    empty match make the alternation ambiguous.
    """

    def _fold(atoms: set[str]) -> set[str]:
        if ignore_case:
            return {ch.lower() for ch in atoms}
        return atoms

    seen: list[tuple[set[str] | None, bool]] = []
    if len(alt.branches) < 2:
        return False  # a single branch is a deterministic sequence
    for branch in alt.branches:
        atoms, eps = _first(branch)
        if eps:
            return True
        if atoms is None:
            return True
        folded = _fold(atoms)
        for prev_atoms, _prev_eps in seen:
            if prev_atoms is None:
                return True
            if _fold(prev_atoms) & folded:
                return True
        seen.append((atoms, eps))
    return False


def _contains_ambiguous_alternation(node: _Node, ignore_case: bool) -> bool:
    if isinstance(node, _Alternation):
        if _alternation_is_ambiguous(node, ignore_case):
            return True
        return any(
            _contains_ambiguous_alternation(b, ignore_case) for b in node.branches
        )
    if isinstance(node, _Sequence):
        return any(
            _contains_ambiguous_alternation(el, ignore_case) for el in node.elements
        )
    if isinstance(node, _Group):
        return _contains_ambiguous_alternation(node.body, ignore_case)
    if isinstance(node, _Quantified):
        return _contains_ambiguous_alternation(node.operand, ignore_case)
    return False


# ---------------------------------------------------------------------------
# Static safety check
# ---------------------------------------------------------------------------


def check_pattern_safe(pattern: str) -> None:
    """Reject patterns outside the statically-safe subset (§15.3).

    Structural analysis: the pattern is parsed into a syntax tree and
    every unbounded quantifier's operand is checked for (a) nested
    unbounded quantifiers, (b) variable-width inner quantifiers (ambiguous
    iteration boundaries), (c) empty matches (infinite loop), and (d)
    ambiguous alternation (overlapping / unknown FIRST sets). Backreferences,
    lookbehind, and over-long patterns are rejected outright. Deterministic;
    false rejections are safe.
    """
    if not isinstance(pattern, str):
        raise UnsafePatternError("pattern must be str")
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise UnsafePatternError(f"pattern longer than {MAX_PATTERN_LENGTH} chars")
    if re.search(r"\\[0-9]|\(\?P=", pattern):
        raise UnsafePatternError("backreferences are forbidden")
    if "(?<=" in pattern or "(?<!" in pattern:
        raise UnsafePatternError("lookbehind is forbidden")

    ignore_case = "(?i" in pattern
    tree = _PatternParser(pattern).parse()
    _check_node(tree, ignore_case)


def _check_node(node: _Node, ignore_case: bool) -> None:
    if isinstance(node, _Quantified):
        _check_node(node.operand, ignore_case)
        if node.max_req is None:
            _check_unbounded_operand(node.operand, ignore_case)
        elif node.max_req >= 2 and _contains_ambiguous_alternation(
            node.operand, ignore_case
        ):
            # Fixed-width repetition with k >= 2 multiplies the backtracking
            # paths of an ambiguous inner alternation by branches^k, which
            # is exponential in the (pattern-bounded) repetition count.
            raise UnsafePatternError(
                "ambiguous alternation under repetition "
                "(overlapping or unanalyzable branch first-sets)"
            )
        return
    if isinstance(node, _Sequence):
        for el in node.elements:
            _check_node(el, ignore_case)
        return
    if isinstance(node, _Alternation):
        for branch in node.branches:
            _check_node(branch, ignore_case)
        return
    if isinstance(node, _Group):
        _check_node(node.body, ignore_case)


def _check_unbounded_operand(operand: _Node, ignore_case: bool) -> None:
    if _contains_unbounded(operand):
        raise UnsafePatternError(
            "nested unbounded quantifier inside unbounded quantifier"
        )
    if _contains_variable_width(operand):
        raise UnsafePatternError(
            "variable-width quantifier inside unbounded quantifier "
            "(ambiguous iteration boundaries)"
        )
    if _can_be_empty(operand):
        raise UnsafePatternError(
            "unbounded quantifier over an operand that can match empty"
        )
    if _contains_ambiguous_alternation(operand, ignore_case):
        raise UnsafePatternError(
            "ambiguous alternation under unbounded quantifier "
            "(overlapping or unanalyzable branch first-sets)"
        )


def compile_safe(pattern: str) -> re.Pattern[str]:
    """Validate then compile once (load time; never per message)."""
    check_pattern_safe(pattern)
    return re.compile(pattern)


__all__ = [
    "BIDI_CONTROL_CHARS",
    "DASH_VARIANTS",
    "MARKDOWN_CHARS",
    "MAX_CANDIDATES",
    "MAX_DIGIT_RUN",
    "MAX_NUMERIC_TOKENS_PER_FIELD",
    "MAX_NUMERIC_TOKENS_PER_MESSAGE",
    "MAX_PATTERN_LENGTH",
    "MAX_RULE_MATCHES",
    "REPETITION_RUN_LIMIT",
    "ZERO_WIDTH_CHARS",
    "UnsafePatternError",
    "check_pattern_safe",
    "compile_safe",
]
