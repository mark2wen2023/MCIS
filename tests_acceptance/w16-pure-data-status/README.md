# W16 pure data classification / formal GISIS call

Parent: 94d5e38c926fda232bb987b60fa9145e4bcf01a7.

Run with existing Python (stdlib only):

    python3 -I -B tests_acceptance/w16-pure-data-status/check.py

Three tests directly import production build_gisis/validate_gisis and the extracted
classification functions, with synthetic SYN-XREPO-001 dictionaries. No AST,
module replacements, application, database, seed import, network or files exported.
The two function bodies are unchanged verbatim. Existing constant identifiers
are preserved; no public case documents are loaded. service.py re-exports the
same names so existing import callers remain compatible. This is classification,
not an authorization decision or permission grant.

Observed: 3 tests passed on Linux. Formal GISIS projection retains missing UTC,
zero deaths and false pollution; input is unchanged. Strict True classification
and import isolation are checked. Exact original function-body and constant
comparison separately passed. Full service import was deliberately not run.

Not tested: full app/HTTP, existing public-case generation, PDF/DOCX, persistence,
archive, real accounts or browser. No report was generated, saved or finalized.
Local review candidate only; no merge/deployment/CI.
