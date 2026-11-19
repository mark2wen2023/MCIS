# Developer-only normal read validation

Base 3a19c75221dc770042708972bf7a1a36d681e121. Command from repository root:

    python -B tests_acceptance/audio-reference-range/check.py

Three normal handcrafted cases passed: v2 declared bounds, v3 declared bounds, v3 explicit unknown. Same-text revisions 1 and 2 return their respective ranges; after adding 2, digest-pinned read of 1 returns its old bounds or null unknown. Exact read order is revision 0, exact human revision, designated evidence once. Default reference output/digest and input dictionaries unchanged. No range grants approval or retrieves audio.

Only named pure source modules are AST-loaded with explicit pure dependency injection; package initializers are not imported. The existing check.py fixture function is extracted, but none of its tests execute. Initial audio/version/source fields are handmade to match the actual persisted PCM contract. Reader is an in-memory double, not real SQLite/SQLAlchemy, authorization, actual snapshot or file byte verification.

No negative/permission/fault/tamper/missing-source tests run; error branches are static code only and remain unverified. No services, HTTP, Save, browser, model, original materials or seed. No existing paused test invoked. No product call-site integration. Source provenance and transactional guarantees must come from the future caller; see contracts/audio-reference-range.md. No claim of complete report export/reopen or playback acceptance.
