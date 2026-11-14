# PR93 + font-test PR94 local combination

Base main94d5e38c926fda232bb987b60fa9145e4bcf01a7. PR93 verified open/draft
head09400ef7df3cbc50bb3ea2ec987c188485b18e2a. PR94 newly created open/draft
head78256f42736adbdd6239fe9686252f0ca5e4ad30.

Isolated full worktree /workspace/mcis-report-cause-font-combined, branch
integration/report-cause-font-combined starts at PR93 head; applies the exact
PR94 test/process/evidence delta. Shared preinstalled Python environment reused;
test databases/files use isolated temporary directories. This is not a separate
machine or independently executed reviewer session. Only one development line.

Both candidate non-document files match their original heads byte-for-byte.
REQUESTS/ROADMAP preserve full PR93 docs and exact font-candidate append relative
to main. All2407 other tracked main files remain byte-identical. In particular,
existing evidence/Intake and report-bundle download permissions are intact.
Both frozen manifests pass; font still Git blob102a717709c10b1ffcfdc4bb35fb335124319e85.
See tree.json. No product/policy/font/renderer changes beyond original PR93 source.

Actual full combination selection:
service/.venv/bin/pytest -q
 service/tests/test_report_cause_provenance.py
 service/tests/test_reports_w16_sources.py
 service/tests/test_reports_w162_access.py
 service/tests/test_report_bundle_attachment_access.py
 service/tests/test_reports_font_coverage.py
 'service/tests/test_report_output.py::test_real_single_render_bundle_and_legacy_archive[pdf]'
 service/tests/test_report_output.py::test_real_concurrent_renderers_and_legacy_export

120 passed in30.54s (tests.txt):5 provenance,12 sources,80 report access,
15 copied-bundle access,4 font+denial and4 genuine PDF output/concurrency cases.
No skips or failures in this selection. The original2 Investigator failures are
not erased: PR94 now uses allowed identity for font checks and explicitly tests
Investigator denial. Old logs describe old snapshots, not this new combination.

PR94 description distinguishes developer103 selection from coordinator-reported
independent97 permission checks; independent review did not repeat full103.
The new combined120 is developer verification only, requires independent review,
and is not full repository or CI acceptance. No new reviewer agent was spawned.

No genuine browser/visual layout, real AIS/model/HFACS or production SSO test.
Real PDFs/text extraction are narrower than visual inspection. Synthetic roles
and local fixtures are not actual investigation findings. Cause labels remain
unverified; citation targets current register, not historical version/digest.
Report+recommendation archive remains blocked. Existing lock/memory constraints
unchanged. No software installation, protection bypass, merge or deployment.
Combination remains local for review; no update to either PR head.
