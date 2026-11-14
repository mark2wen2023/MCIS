> Historical local verification snapshot. Subsequently authorized for a dedicated remote review branch; no merge/deployment. Only the three-file main prerequisite, its tests/contracts, and review records are included. Combined-tree references describe local experiments, not included feature changes.

# Minimal safe-read and final-intake-authorization prerequisites

Date2026-11-14. Reviewable local proposal, NOT integration approval.
Remote refs and main unchanged; no deployment, merge, remote PR or push.
Local implementation branch: `local/safe-read-and-intake-authorization` in
/workspace/mcis-safe-read-main, based on main3aba2bf03e393909c611489ae573a887087637ac.
Changes are staged/uncommitted for review. Original /workspace/mcis stays clean.
Second isolated worktree /workspace/mcis-safe-read-combined contains the prior local
main+#61/#64/#69 resolution plus this proposal; no upstream branch was modified.

## Deliverables

- minimal-product.patch: exactly3 product files,63 additions/14 deletions against main.
- review-tests-and-contracts.patch: upstream safety documentation/tests with explicit
  main-compatible fixture adaptations, new delivery/authorization regression and contract.
- patches.sha256: exact patch hashes.
- INDEPENDENT.md and test_independent_safe_read.py: independent checks/limitations.
- application.json, source-equivalence.json, *-focused.txt, *-final-regression.txt,
  *-directory-probe.txt and authorization-*-observed.txt: actual execution evidence.

Both patch files passed git apply --check on clean main. Product patch also passes
apply-check on the previous main+#61/#64/#69 isolated tree. Nothing was merged.
The main EvidencePage resolution and progress-document conflicts from the prior report
remain separate; these patches do not resolve or overwrite those shared documents.

## Minimal dependency analysis

| Product file | Ported behavior | Existing dependency |
|---|---|---|
| common/safe_files.py | absolute descriptor-relative O_DIRECTORY/O_NOFOLLOW traversal; regular-file check; caller byte budget; fd cleanup; typed unsupported/budget errors | Python stdlib only |
| evidence_intake/router.py | 8MiB read wrapper; unsupported capability503 without fallback; reserve SQLite writer BEFORE final commit authorization | existing reports.access.begin, existing metadata/hash/receipt and DB code |
| working_records_archive/service.py | shared safe read with per-caller budget;409 missing/integrity,413 budget,503 unsupported | existing archive validation/problem code |

Read changes originate in c3d6126f55069efcda0525dd1e79ab5f6bbe98d7 and its direct child
9212493fde452f90912c0d28d7c25c7082e0f242. Final shared helper is byte-identical to9212493
(SHA25658e4d26d5cf93431cc7adf2065393c17d14b49902cfa50661e78383c0b8cb9c7), including
its existing trailing blank line (upstream patch hygiene warning, no semantic change).
No third-party library, migration, package version or new endpoint is required.

The two final-authorization lines are independently usable from aac3c5029c32ed854845186fc20ec0c35ae67739:
`from ..reports.access import begin; begin(s)` inside WRITE_LOCK/new session before
final authorize. Its source-incarnation allocation is NOT ported. No source/case
incarnation, timeline, identity-trial or unrelated PR56 features are imported.
Main already has the reservation helper. Its guarantee here is SQLite-specific.

Two upstream tests imported registered timeline preview fixtures. Those are test-only
couplings, not product dependencies. Adapted unsupported-platform test now calls main's
existing receipt/download APIs. New restore test uses existing working-record archive
fixtures and asserts inactive receipt409. Other reader tests are retained. The old
upstream documents are included as provenance; current counts below are newly executed.

## Reproduced issues and precise claims

### Parent directory replacement

The prior main helper probe replaced an already-checked parent directory with a symlink
to a second temporary directory. Main's leaf-only open returned a synthetic external
marker. Both patched worktrees return409 instead. Other tests replace a directory after
its fd is opened and verify the original directory stays pinned. These are synthetic
helper/filesystem probes, NOT evidence of a remotely exploitable endpoint leak.

A real historical endpoint regression also performs a deterministic parent swap and
checks409, no returned marker and no new successful Access event. Existing content-hash
checks remain important; the old helper result alone never established endpoint leakage.

### Final authorization versus a second SQLite writer

Separate actual local API race observed on the unpatched main+three-delta tree:

| Case | Second connection after final authorization | Response | Persistent result |
|---|---|---|---|
| fresh intake | revocation committed |200|evidence/custody/audit0/0/0 ->1/1/1;1 blob|
| same-operation replay | revocation committed |200|existing1/1/1 and1 blob retained|

After the two-line reservation change, that same interleaving reports `locked` on the
other connection. The authorized intake/replay completes; revocation may commit after
the transaction ends. When revocation commits before the final reserved transaction,
current authorization returns403 with no new writes/blob. A waiting writer also proceeds
after commit OR rollback; synthetic post-write fault leaves no new records/blob.
This is real SQLite/API ordering with controlled hooks, not a production identity test
or claim that an unauthenticated remote actor can write the SQLite file.

## Final executed results

| Test set | main + minimal proposal | main +61/64/69 + proposal |
|---|---|---|
| Safety/transaction focused tests |42 passed,0 skipped;5.87s|42 passed,0 skipped;5.89s|
| Independent additional safe-reader probes |9 passed|9 passed|
| Independent authorization-before-final-read checks |2 passed|2 passed|
| Existing affected regression +6 new transaction cases |196 passed,1 failed,2 skipped;71.43s|306 passed,1 failed,2 skipped;96.00s|
| Explicit three-slice report-ZIP flow after final change |not applicable|2 passed (final-combined-flow.txt)|

Counts overlap between focused and regression sets; do not sum them as unique coverage.
Independent authorization tests verify fresh and replay paths already hold a driver
transaction BEFORE final authorize reads policy, and a real second connection UPDATE
cannot commit there. Independent report contains the separately executed commands.

All final regression failures are the previously reproduced existing
`test_report_versions_full_review_gisis_and_hfacs_coexist` / HFACS_CORE_UNAVAILABLE.
Two skips require absent .NET SDK. No failed assertions removed, no fake core installed,
no policy relaxation to make tests pass. Existing OpenAPI contract tests are included
and pass on this main-derived proposal. Baseline failure evidence remains in the prior
/workspace/mcis-integration-results/clean-main-baseline.txt.

Reader cases include parent/leaf symlinks, before/after-open substitution, FIFO/directory/
missing path, fstat/read failure, fd closure, short reads, invalid budget/path, zero and
exact/+1 sizes up to32MiB, and unsupported O_DIRECTORY/O_NOFOLLOW/dir_fd with no fallback.
Real restore/content delivery preserves original bytes, full permission gate, hash
checks, normal audit semantics and inactive historical receipts. No model/intranet call.

Final regression commands from respective service directories are the earlier affected
suite plus tests/test_intake_authorization_transaction.py; combined acceptance suites
use `python -m pytest --import-mode=importlib` to avoid their duplicate module basenames.
Full outputs and reproducible new probe/test scripts accompany this report.

## Remaining boundary: integration still not automatically cleared

- Legacy evidence GET in evidence/router.py still reads via Path.read_bytes. PR64's
  container permission gate does not make that file open descriptor-safe. The package
  assembler's package/mcase.py build_files also retains read_bytes. This minimal upstream
  port does NOT cover those paths; they require separate explicit review before a claim
  that every attachment delivery/export is safe. No endpoint-leak claim is inferred here.
- Pinning directory fds does not freeze an open inode, prevent hard-link/mount changes,
  fix filesystem writer races, or provide crash-atomic filesystem+SQLite persistence.
  Existing hashes/bindings and write/custody checks remain necessary. Local filesystem
  mutation capability is an explicit precondition of these probes, not an assumed remote
  upload capability. All test data/files were temporary and synthetic.
- BEGIN IMMEDIATE serializes SQLite writers. It is not a promise that revocation always
  wins: ordering determines which authorized transaction commits first. Existing local
  role headers remain unverified identity; no production authentication is introduced.
- Browser sandbox startup remains unresolved from the prior actual Chromium attempt;
  this backend-only patch did not rerun or bypass it. No browser/visual/disk-save, .NET,
  full-system/CI, Windows/platform fallback or deployment acceptance is claimed.
- Prior EvidencePage/progress-document integration choices remain to be reviewed. The
  complete PR56 baseline still has its previously documented TS/OpenAPI issues; this
  minimal main port neither imports nor fixes unrelated PR56 functionality.

Recommended review unit: inspect minimal-product.patch first, then the supported read
budgets/status codes and final authorization ordering, then reproduce focused and
combined regressions. Keep attachment integration pending coordinator/security review
of this proposal and the uncovered paths. This report is not release authorization.
