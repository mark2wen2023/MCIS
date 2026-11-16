# PR95 + PR96/98/102 integration candidate

New independent branch integration/pr95-pr96-pr98-pr102 starts at preserved
1502fa9916952bc0804ce553fb2a5daffa37666d. Merge7c013f5 adds exact PR95
0c182570107079794af048bfaf4e19a64b70dd63 (OPEN at inspection).
PR95 chain0c18257 -> a2dcc757 ->09400ef ->main94d5e38. It already incorporates
PR93 ancestry and PR94 content; neither PR93 nor PR94 was separately merged.
Remote main remains94d5e38c926fda232bb987b60fa9145e4bcf01a7. Both source remote
heads remained exact on final reread; prior integration branches unchanged.

Only REQUESTS.md/ROADMAP.md paths overlap between PR95 and1502fa9. Verified PR95
files are exact main prefix + additions; resolved existing1502bytes + those
additions, retaining all progress history. All other files from both input heads
are byte-identical, including inherited reports and tests. PR95 adds only10lines
to reports/sources.py at runtime; no policy or renderer changes. Ordinary report
fixture change and cause-label content change can interact semantically, so the
combined test selection reruns them together rather than assuming disjoint paths
prove compatibility. Report cause labels remain unverified; citations still open
current register, not a versioned historical source. Archive limitation unchanged.

Font Git blob102a717709c10b1ffcfdc4bb35fb335124319e85 verified in complete checkout.
Report-source/font freeze manifests pass. Entire web tree hash matches1502:
98cd11640bc4bbab7a8f7b5adc43549d18171af4. Its prior32SSR/numbering/build results
remain prior developer evidence; no redundant frontend build/browser run here.

## Actual combined command (service/)

    ./.venv/bin/pytest -q tests/test_reports_w16_direct.py tests/test_reports_w161_snapshot.py tests/test_shared_trajectory.py tests/test_tracks_import_w102.py tests/test_report_cause_provenance.py tests/test_reports_w16_sources.py tests/test_reports_w162_access.py tests/test_report_bundle_attachment_access.py tests/test_reports_font_coverage.py 'tests/test_report_output.py::test_real_single_render_bundle_and_legacy_archive[pdf]' tests/test_report_output.py::test_real_concurrent_renderers_and_legacy_export tests/test_align_preview_w41.py -rs

Uses preinstalled dependencies and isolated synthetic temporary cases/SQLite.
PDF/DOCX bytes and text assertions are actual renderer output, not visual-layout
inspection. Existing normal access regressions retain synthetic role/failure
fixtures, not authenticated SSO; no restricted historical-integrity/security/ECFC
operations were retried. Core outputs in ordinary align-preview tests are mocks,
not actual alignment/model execution. No dependency installation or protection
settings query performed.

## Limits retained

No full CI, browser, PDF visual layout, real AIS/Unity/HFACS/LLM, production load
or identity validation. No product schema/permissions changed. Parent related
190selection remains historical187passed/3failed with identical baseline failures;
not rerun here, and not declared repaired. Existing report+recommendation archive
still blocked, labels not causally verified, lock/memory constraints unchanged.
No merge into main, PR closure, forcepush, deployment or source branch rewrite.
Local combined candidate only; independent combined review still needed.

Final result:333passed1skipped69.18s. Skip is existing
 tests/test_align_preview_w41.py::test_real_cli_csv_preview, line66,
'real CLI SDK required'. No new skips/xfails.333includes184prior-focused +120PR95
selection +29align adapter tests; previous runs/reviewer counts are not additive.
This complete selection ran on the merged code tree7c013f5; subsequent commit only
adds this report/log hash. All five source freeze manifests pass unchanged.
Local raw log:/tmp/mcis-four-pr-tests.txt; SHA256 stored alongside, no raw fixture
dump added to Git. Parent branch remote remains1502fa9, PR95remote0c18257.
