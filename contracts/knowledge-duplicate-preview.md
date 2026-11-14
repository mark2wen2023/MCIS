# Knowledge candidate duplicate preview (development only)

POST `/api/v1/knowledge/duplicates:preview` accepts one unchanged knowledge-card content object. It uses the existing W19 internal role boundary (Investigator/LeadInvestigator), which is a local declared-role development boundary, NOT production authentication. No source URLs are fetched and no model is called.

Before inserting a candidate, the investigator can inspect exact matches among the latest 1000 locally stored knowledge cards of all statuses. A result can mean `exact_content` (canonical full content equality) and/or `same_source_excerpt` (exact source type, URL if present, locator and excerpt). No text normalization, fuzzy similarity, semantic matching, authenticity or approval is implied. Synthetic and public sources never match each other. The title and rights note are not part of the source-excerpt key; different rights assertions require human review.

Response returns inputDigest, matched card IDs/status/title/kind/contentDigest/reasons, scanned count, scanIncomplete and resultsTruncated, with at most 50 results. Every match remains a candidate for manual comparison. An empty list is NOT proof of uniqueness. The response does not expose audit actors, approval notes, source contents or filesystem paths. Malformed stored records fail closed without partial results. No create, merge, delete, review or publish occurs, and no audit is appended by this read-only preview.

This is an API slice only; UI, source authenticity, corpus-wide pagination, production authorization and semantic deduplication remain unimplemented. Test fixtures are explicitly synthetic and are not model evaluations.
