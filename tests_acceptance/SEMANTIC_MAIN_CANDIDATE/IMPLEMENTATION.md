# Main-based offline semantic worksheet candidate — 2026-11-14

A fresh clone fetched remote main and created codex/semantic-main-candidate-20261114
at3aba2bf03e393909c611489ae573a887087637ac. A second ls-remote confirmed the same
main SHA before acceptance. PR56 head254167e is not an ancestor. No preview commit
was cherry-picked or merged: only the40 explicitly hashed source files were copied.
Production service/web files and entry points were not changed.

The seven runtime files are pinned unchanged. Only three of them come from PR56;
the other four are the PR57 runtime delta. source-manifest.json names original
commits and exact SHA256 for all40 imported files, distinguishing runtime, tests,
fixtures and historical documentation. contracts/semantic-offline-main-candidate.md
and research/semantic_support/MAIN_CANDIDATE.md supply current boundaries and usage.
The42-entry candidate freeze includes the40 source files plus these two new docs.
Original reports/freezes describe their historical branches, not this candidate.

Validation:

- `PYTHONPATH=research/semantic_support service/.venv/bin/pytest --import-mode=importlib -q research/semantic_support tests_acceptance/SEMANTIC_BROWSER_EXPORT`: **122 passed**, zero skips.
- Freeze42/42 verified; git diff --check passed; source paths limited to research,
tests, logs and defect evidence. No production source has changed.
- Prior extraction feasibility probe additionally generated the page from only7
runtime files using python -S with socket creation rejected, checked0600 output and
rejected overwrite; a separate manifest-reconstructed directory repeated122 tests.
Those are prior engineering evidence, not new model or browser acceptance.

Limits: current actual Chromium sandbox startup is unavailable; no native file
chooser/download or real CSP enforcement acceptance is claimed. Node adapters run
actual generated script with simulated controls. Original historical Jiangxin9 model
output/receipts are retained unmodified and unverified; no new model call or PDF
fetch. No real author identity, source authenticity or case facts are established.
This has no relationship to production authentication or attachment fixes.

Review-only local candidate. No report-citation PR retry, merge or deployment.

Independent audit uses original source Git objects to verify byte equality. A shallow
checkout without PR56/PR57 objects must obtain those exact objects before running the
Git-origin audit assertions; the runtime and ordinary offline tests do not need Git.
