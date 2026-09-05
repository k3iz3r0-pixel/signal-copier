# Per-Provider Fixture Data

This directory holds synthetic fixture examples for each provider. The
fixtures are NOT verbatim copies of any real provider's messages; they are
constructed to exercise the parser's contract (design §17.2).

Per the design §17.2 fixture content requirements, each fixture entry has:

- `raw_text` — the input message;
- `outcome` — expected ParseResultState;
- `fragments` — expected slot/value mapping;
- (optional) `unresolved_fields` for PARTIAL outcomes;
- (optional) `evidence` entries for provenance assertions;
- (optional) `context` for correlation requirements.

The actual parse assertions live in
`tests/parser/providers/<provider>/test_<provider>.py`; the fixture files
here are the structured data the tests consult.

NOTE (Phase 2C): providers 013-017 are REAL-fixture providers — their
`canonical.py` texts are VERBATIM excerpts from the owner-supplied corpus
`docs/corpus/real-messages.md` (classification and evidence model:
`docs/corpus/EVIDENCE.md`). Providers 001-012 remain synthetic.

This is the steady-state path for adding provider #N: create the fixture
data here + register the provider profile in
`packages/parser_profiles/data/`; no engine change is required.