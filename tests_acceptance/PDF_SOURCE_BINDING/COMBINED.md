# Combined internal candidate

This is a content candidate based on actual main3aba2bf and its unchanged public report bytes. It combines only the internal text-layer candidate and source binding, not PR97 or any runtime feature stack. Main production code, database tables, routes and custody implementation are untouched.

Run from repository root with installed pytest and Poppler:
PYTHONPATH=tests_acceptance/PDF_TEXT_LAYER_CANDIDATE:tests_acceptance/PDF_SOURCE_BINDING python -m pytest --import-mode=importlib -q tests_acceptance/PDF_TEXT_LAYER_CANDIDATE tests_acceptance/PDF_SOURCE_BINDING

Original31 lifecycle and28 binding tests remain; one new pure combined public-PDF success/failure test checks supplied source state/currentSha and empty custody events remain unchanged. This is NOT an ORM test or proof about a live database currentSha: no database is touched by design. Original PDF bytes remain unchanged. Source identity/state IDs are synthetic; source PDF is the official public report already present on main.

No API/SSO/OCR/LLM or production sandbox claims. Binding hashes do not authenticate extracted text; host must run the trusted derivative pipeline and provide current source binding. Exclusive child-reaper ownership, inherited environment and lack of CPU/RSS/escaped-process isolation remain documented in the text-layer README and lifecycle review.
