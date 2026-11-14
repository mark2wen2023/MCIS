# W19 duplicate candidate preview — native subagent implementation

Baseline: 254167e3e957784fd9d2d136a275731f33314d9b. Dedicated isolated files; original working directories untouched.

Implemented POST /api/v1/knowledge/duplicates:preview. Exact canonical content and exact source type/URL/locator/excerpt matches across all card states, bounded scan and result counts with explicit incompleteness flags. No fuzzy or semantic quality claim; no network, model, audit write, deletion, merge, approval or case mutation. Uses existing development declared-role boundary, not production identity. No UI is added by this slice.

Primary 20 + independent 11 = 31 tests passed. Independent review found malformed stored card IDs were returned when both row/doc had been corrupted; fixed with exact KC-32hex validation, original red test unchanged and passing. Related W19/W19.2/archive regression has a known pre-existing route contract mismatch: timeline/registered-align-preview is absent from OpenAPI. The same test fails on a separate clean baseline copy with the original router and original OpenAPI. This unrelated failure is not suppressed or treated as passing; new duplicate route is present in the contract. Final full selected results are in logs/knowledge-duplicates-regression.txt.

Fixtures are synthetic, only ASGI/TestClient and temporary SQLite. This is not browser, real LLM, external API, production identity, CI or end-to-end full-system acceptance. No deployment/merge. Stored/source labels are assertions, not authentic provenance, and duplicates are only prompts for manual comparison. Zero matches never certifies uniqueness.
