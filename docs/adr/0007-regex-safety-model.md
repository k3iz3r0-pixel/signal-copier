# ADR 0007 — Regex Safety Model

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §15

## Context

Provider messages are untrusted input. The parser uses
Python's `re` module (standard library; no third-party
regex library). The `re` module is susceptible to
catastrophic backtracking on adversarial input
(e.g., `((((((a)))))))` patterns, or `\d+-\d+-\d+` with
mismatched groups).

In a financial system, a 5-second parse freeze is a
disaster. The parser must:

- Bound regex execution WORK deterministically (not via a wall-clock
  timer that preempts a running `re` call, which standard-library `re`
  cannot do in-process).
- Reject pathological input deterministically.
- Avoid catastrophic backtracking by construction.
- Not require third-party dependencies (no `regex` library).

## Decision

The parser enforces the following guarantees:

1. **Single-tokenizer pattern per Profile**: each Profile
   declares a single `tokenizer_pattern` that is a
   compiled alternation of bounded, non-overlapping
   branches. Each branch has a fixed structure that does
   not allow backtracking into exponential alternatives.
2. **No nested quantifiers**: patterns may not contain
   `(a+)+`, `(a*)*`, `(a+)*` and similar exponential
   shapes. A Profile validator (Phase 3+) rejects such
   patterns at load time.
3. **Anchored where possible**: token patterns are
   anchored to a word boundary or to specific punctuation.
4. **No backreferences in hot-path rules**.
5. **Length-bounded patterns**: `\d{1,12}` not `\d+`;
   `[A-Z]{1,16}` not `[A-Z]+`.
6. **Runtime timeout guarantee (NARROWED).** The parser does NOT claim a
   per-regex 50ms / per-message 100ms hard wall-clock guarantee. A hard
   wall-clock timeout that preempts a RUNNING `re` match cannot be
   implemented in-process with the standard library: `signal.SIGALRM` is
   POSIX-only, main-thread-only, and unsafe in threaded processes; a
   `threading.Thread` cannot be safely killed; `re` exposes no timeout
   parameter. The guarantee is replaced by (a) deterministic bounded work
   via items 1-5, 7-9 below, and (b) an optional per-message cooperative
   budget checked OUTSIDE the pure parser by the Phase 3+
   ingestion/correlation layer. See the Amendment below.
7. **Message length bound**: messages longer than
   `ProviderProfile.max_message_length` (default 8000
   chars) are rejected as `MALFORMED` with evidence
   `message_too_long`. The raw text is NOT truncated.
8. **Numeric overflow bound**: numbers exceeding
   `ProviderProfile.max_numeric_value` (default 1e12)
   are rejected as `MALFORMED` with evidence
   `numeric_overflow`.
9. **Adversarial repetition bound**: long runs of the
   same character (>4096) are truncated and flagged.

## Amendment (2026-08-31) — Runtime Timeout Guarantee Narrowed

The prior revision promised a hard per-regex 50ms / per-message 100ms
wall-clock bound with "SIGALRM on POSIX, threading elsewhere" as a
deferred mechanism. That promise is NOT implementable in-process with
the standard library and has been NARROWED:

- The deterministic guarantee is **bounded work**: static pattern safety
  (items 1-5) + bounded input (item 7) + numeric/token/candidate/match
  count bounds → every regex execution completes in finite, statically
  boundable work on ANY hardware, with no timer.
- A hard wall-clock preemption of a running `re` call is NOT promised.
  An OPTIONAL per-message cooperative budget may be checked BETWEEN
  pipeline stages by the Phase 3+ ingestion/correlation layer, OUTSIDE
  the pure parser. It is an availability/DoS backstop, is explicitly
  non-deterministic in outcome, and does not emit `regex_timeout` from
  the pure parser.

## Consequences

Positive:

- Catastrophic backtracking is prevented by construction.
- A adversarial message cannot freeze the parser (bounded work).
- Profile authors cannot accidentally introduce ReDoS.
- The guarantee is deterministic and platform-agnostic (no timers).

Negative:

- A hard wall-clock timeout is no longer guaranteed; availability
  under a future pattern bug is delegated to the Phase 3+ supervisor
  layer rather than enforced inside the pure parser.
- The Profile validator (static pattern safety) is a new component to
  implement and test.
- Pathological inputs that are "valid" (e.g., 8000 chars of legitimate
  signal text) must fit within the static work bounds; Phase 3+
  benchmarks will confirm the bounds are comfortably safe.

Reversibility: medium. The length and count bounds are tunable
parameters. Changing the pattern validation contract (no nested
quantifiers) is a large refactor.
