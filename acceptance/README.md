# W19 knowledge-card reviewed search and source (acceptance only)

Pin: origin/main `94d5e38c926fda232bb987b60fa9145e4bcf01a7` (GitHub-verifiable
default branch). This SHA already contains the existing knowledge-card
review lifecycle and `GET /api/v1/knowledge/cards` search.

Search type: literal case-folded substring over title/summary/body/
applicability/tags (`search_text.contains`). This is ordinary keyword
search, not vector or semantic similarity. The contract
(`contracts/W19.1-knowledge-cards.md`) states the same. No model or
embedding is invoked.

This harness starts a real 127.0.0.1 service process. HTTP results are
HTTP, not a browser result. It does not redo the 8183226 template-change
Chromium regression and is not a W19 whole-package claim.

Record count: three synthetic cards in one fixture scenario (knowledge
cards on this SHA are not case-scoped). Dot's text said "两条"; three
is the minimum to hold Published, Candidate, and Withdrawn in one
usable-search snapshot. No product source is changed.
