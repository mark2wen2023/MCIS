# ECFC archive proposal — isolated design prototype

This directory preserves the 2026-11-13 design checkpoint, not production archive support. Existing export guards remain unchanged. No .mcase version is allocated.

Run locally using only Python standard library: `python -m unittest discover -s research/ecfc-archive-proposal -p 'test_prototype.py' -v`.

The 17 synthetic tests passed and were independently rerun. The callbacks are stubs: this validates relationships only, not real ECFC document semantics, digest authenticity or evidence bytes. Coordinated alteration of hash and next prevHash may pass; this is a known prototype limitation, not a security guarantee. The equal-count duplicate receipt branch was independently checked but is not yet a dedicated test in this checkpoint.

Not implemented or validated: bounded strict archive parsing, real digest verification, evidence preservation, atomic DB/filesystem restore, generation-isolated replay protection, concurrent save/export, real C# or browser acceptance. No production implementation changed. Do not remove the existing export refusal based on these tests.
