# Canonical-source fresh-root browser/HTTP revalidation

This NEW evidence supersedes assumptions that old local successful runs proved canonical upstream bytes work. Old logs remain unchanged and are valid only under their earlier local-source conditions.

Test root: `/workspace/scratch/d5cd4f6afdb1/canonical-source-snapshot-8680`, a validated source snapshot, NOT a full Git clone. service/web/tools/production C# source from this root. `mcis_service.__file__` verified `/workspace/scratch/d5cd4f6afdb1/canonical-source-snapshot-8680/service/mcis_service/__init__.py`. Only installed `.venv` and `node_modules` dependencies reused by symlink; no old data directory or old source module used. Each run allocates a new temporary data directory/SQLite database.

Canonical report source SHA256 before/after:
`bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2`.

New-root formal `tools/mcis-core/mcis-core.sh version` succeeded using shared official .NET8.0.428. Core build/provenance check executes before browser runs. New-root DLL SHA256 before/after:
`f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`.

Important exact launcher distinction: published browser scripts override external MCIS_CORE with ROOT/tests_acceptance/W6/mcis-core-norebuild.sh and ROOT/tools/mcis-core/out/mcis-core.dll. Therefore browser runs used new-root real prebuilt DLL via new-root no-rebuild wrapper after formal new-root build/provenance validation, NOT the old-root DLL and NOT the formal build-wrapper on every browser request. Scripts were kept unchanged as requested. Supplemental live HTTP service used new-root formal mcis-core.sh directly.

## Original scripts, new fresh data
- W4.1 actual browser: **35/35**, exit0. Published script SHA256 `5bb58a173ece40d10aa875a506aaf5a5ab6d7f9b76316a6a4bb8e3327432a72b` before/after unchanged.13frozen inputs verified. Evidence:canonical-w4.1-browser.json.
- W7.2 actual browser: **57/57**, exit0. Published script SHA256 `3b572be43710db4ff14897a35a0e662be833993884499e1afa20cc17a1123c36` before/after unchanged.8frozen inputs verified. Evidence:canonical-w7.2-browser.json.
- Explicit MCIS_REPO points to new snapshot in both. All real service/core computations, UI and browser use loopback only, no external requests. Browser official Chrome157.0.8103.50. Both1440/768 geometric assertions pass; new768screenshots locally reviewed. All PNGs stay local, never uploaded.
- W4 includes canonical freshseed plus5deg CSV/zero persistent database changes; W7 includes canonical freshseed plus full fictional consultation lifecycle and actually committed201response-loss recovery. These are the existing unchanged test scopes, not all project acceptance.

## Separate actual loopback HTTP report check
**13/13 checks passed**, fresh third database; no browser involved. Fresh EV-201 source hash canonical; actual cn-msa creation201 with source SHA in generated content; source sections present/public-case text; PDF and DOCX200, correct magic and X-SHA256 equal actual export bytes; DOCX XML contains canonical SHA; pdftotext yields readable long-river-estuary case text. Full metadata:canonical-yangze-report-http.json. This checks source-linked report generation/export availability, not complete textual/visual equivalence of every public-report excerpt or final legal approval. Generated exports remain local.

One initial launcher failure occurred after fresh service seed/build but before Chrome: shell changed cwd and a `$PWD`-relative Chrome path became wrong. It was corrected to absolute environment paths; failed run remains local. No source/script assertion modified to pass, no baseline tolerance changes, no old data substitution. Subsequent W4/W7 were complete successful fresh runs.

No stage,push,merge,deploy or image upload by reviewer. This does not establish clean full-clone reproducibility, production/mobile/user-device acceptance, or cross-client concurrency safety. Old bad-pin databases remain a separate migration concern; these results concern fresh canonical-source seeds only.

## Portable HTTP helper rerun
Added `tests_acceptance/source_correction/report_http.py` with optional MCIS_REPO(default repository relative to script), required MCIS_HTTP_OUT(new output directory), no private absolute path or external service. Only root/output configuration and explanatory docstring changed from local helper; all13assertions preserved. py_compile passed. Script SHA256:3bd956f43f29cadd4fe3dc202407e4d84cc7b5f710fe0630bf554af5eb67587e.

Reran portable helper with MCIS_REPO explicitly set to canonical-source-snapshot-8680 and a new output directory/fresh SQLite database. Actual result **13/13 passed**, exit0. New independent result `canonical-yangze-report-http-portable.json`; previous13-check result retained unchanged. Real service and core source still loaded from specified canonical snapshot. Run with `MCIS_REPO=/path/to/canonical-snapshot MCIS_HTTP_OUT=/path/to/new-output MCIS_DOTNET=/path/to/dotnet python tests_acceptance/source_correction/report_http.py` and appropriate DOTNET_ROOT/DOTNET_CLI_HOME. Requires installed service dependencies/fonts and local pdftotext. PDF/DOCX outputs remain local; no image uploads.
