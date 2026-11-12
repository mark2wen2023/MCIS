# CORE_FINITE independent acceptance

## CF-01: non-finite child JSON reaches downstream processing
Python's default JSON decoder accepts NaN/Infinity and overflowing float literals even though the strict HTTP response serializer rejects them. The process-response boundary now rejects such values anywhere in the final envelope with existing CORE_BAD_OUTPUT/502. Legal finite JSON and domain mappings are unchanged.

Independent acceptance: 43 passed, including HTTP redaction/no database mutation, exact numeric boundary preservation and 400 deterministic random comparisons in one test item. No blocking defect found. See logs/core-finite-independent-review.md. Resource budgets, deep nesting, raw align path access and authentication are outside this fix.
