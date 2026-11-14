# Exact recorded sample preservation (main-based content candidate)

Read-only GitHub main last verified3aba2bf03e393909c611489ae573a887087637ac.
This isolated directory materializes service/contracts from the previously verified
main snapshot a771b23; every pre-edit file was matched by Git blob SHA to actual main
inventory combo-main-baseline.json. This is NOT a local Git branch with genuine
upstream ancestry: local repositories lack that actual commit object. Do not push
synthetic history. Parent must create any eventual branch with verified actual
upstream parent, or obtain an authenticated full clone first.

Only production diff is four lines in cases/service.py: inside the existing
ordered-pair loop, an exact t==b.timeSec returns dict(b) before interpolation.
First sample/out-of-range behavior remains unchanged. At duplicate times first
encountered original wins, preserving existing ordered traversal rather than
silently merging conflicting records. No sorting, approximate-time snapping,
7-minute default, gap policy or identity/API change.

The dict copy retains all original scalar/missing/extra fields. As with preexisting
boundary paths it is shallow, not a deep immutable clone. The function does not
mutate input; callers must not assume nested values are detached.

Tests: first/interior/final exact samples, missing metadata/HDG, duplicates,
outside-range boundaries, empty/single, nextafter near exact t and long-gap
interpolation still unchanged; actual COLREG _pairs_at helper numeric regression.
No C# core/Unity/browser/real AIS/model execution claim. Known broader long-gap,
nonexact UTC/source lineage and outside-coverage behavior remain separate issues.

Reproduce from ais-exact-main:
`PYTHONPATH=service ../mcis-work/service/.venv/bin/python -m pytest -q tests_acceptance/EXACT_SAMPLE`

Independent14/14 pass (10 author +4 independent), including actual GET tracks
stepSec with production ORM rows unchanged. Note that existing route explicitly
recomputes UTC even for an exact point, so API-wide byte-for-byte UTC preservation
is NOT claimed; state_at itself now returns the recorded UTC. Other fields preserved.
Final production SHA256: e17e1c5709ec510cf5e443961039092d0315ad64f0342c67c38de684c706ebdf.
Post-test scan versus main blob inventory: only cases/service.py differs among
materialized service/contracts files (ignoring Python cache files).

## Publication ancestry
For remote publication, use GitHub's complete base tree
2d15b3b1773e24f76e5de010bc86e74cb3a5aa0f and sole actual parent
3aba2bf03e393909c611489ae573a887087637ac, not the local materialized
snapshot's synthetic history. Local preparation notes above remain historical.
Portable test command with the project's installed dependencies:
`PYTHONPATH=service python -m pytest -q tests_acceptance/EXACT_SAMPLE`.

## Coordinator regression boundary
The coordinator independently reran the 14 focused tests successfully.
An additional baseline test_cases_timeline run produced 6 setup errors because
reports/yangze22/case.json was absent from that isolated checkout. This is an
uncompleted baseline regression, not a passing full suite and not evidence of
an interpolation regression. Duplicate-time database secondary ordering remains
unspecified; outside-range clamping and long-gap behavior remain unchanged.
