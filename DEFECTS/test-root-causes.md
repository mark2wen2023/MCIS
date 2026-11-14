# Test root causes — independent disposition

## W9.2 environment fixture / package authorization

**Accepted for the scoped test-only correction** at parent `f2eff95`; frozen module hash verified. Independently reproduced original module **12 failed / 57 passed** and candidate **70 passed**. Original failures parse 403 FORBIDDEN JSON as ZIP because seeded demo recommendation/consultation content requires stricter full-export permission.

Module-local synthetic unseeded case removes unrelated content, and export helper asserts HTTP 200 before parsing. All original test functions/parameters remain; a new seeded-case regression preserves 403 FORBIDDEN. Product/permission code unchanged. This is not a whole-suite resolution or permission relaxation.

Full evidence, exact commands, baseline relocation details and limits: [independent report](../tests_acceptance/test-root-causes-independent/REPORT.md). Baseline snapshot is retained as `.py.source` to avoid accidental pytest discovery. No push/merge/deployment by independent reviewer.
