# Source version assertions for issue writes

Selected sources now freeze both incarnation UUID and SHA256. Journal compares these inside the same reserved write transaction and repeats source validation before commit. A changed source refuses the record rather than silently rebinding; the UI preserves text and asks for fresh selection on the specific correlated rollback response.

Same-operation retry with original pins returns an already committed history even if sources later change; changed pins under that operation conflict. Unknown save outcomes retain the original pending command. No migration or archive schema change. Old direct unpinned API callers retain old semantics, but new host source-bearing writes require pins.

Independent backend5 plus prior5, frontend pin22 plus source24/DOM29/host15/main flow, strict TypeScript and actual fictional stdio/SQLite integration passed. No merge, deployment, production browser/login acceptance or LLM claims.

Final related backend regression:285 passed,zero skipped,159.33s (one pre-existing warning); independent audits complete. Counts include overlapping suites above.
