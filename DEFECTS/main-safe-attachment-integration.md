# Main-based attachment / safe-delivery integration independent review

> **CURRENT VERDICT: BLOCKED — do not release this integration.** Independent expanded
> revocation tests reproduce legacy plain-file export bypass of evidence_meta/audit Deny
> on both the combined tree and pristine main3aba2bf. Earlier72 passing narrow tests remain
> valid evidence but do not cover this gap. The section below supersedes any inference of
> general revocation coverage or integration approval from the earlier review.

## Blocking follow-up: plain legacy export ignores current denied categories

New independent expected-denial regression:
`tests_acceptance/main-safe-attachment-integration/test_plain_policy_blocker.py`.
It creates a synthetic case with no history/report/intake receipts, registers ordinary
nonZIP bytes through old evidence registration, then performs real Lead policy PUT setting
Investigator evidence_meta or audit to Deny. Individual evidence content or audit GET
returns403 respectively. The same Investigator's old export returns200.

This is not merely an HTTP status probe: independently opened returned ZIP contains exact
registered synthetic bytes and audit/audit.jsonl with custody.register, policy.update and
package.export. The package's own access-policy.json still records that category as Deny.
Thus revoked data are actually delivered in this authorized-role synthetic API scenario.
No filesystem mutation or remote unauthenticated actor capability is assumed in this test.

Actual results (expected403 assertions deliberately retained, not marked xfail):

| Target | Result | Evidence |
|---|---|---|
| Combined tree |2 failed in1.57s|blocker-combined-final.txt / .jsonl|
| Pristine main3aba2bf|2 failed in1.50s|blocker-clean-main-final.txt / .jsonl|

All evidence files are under tests_acceptance/main-safe-attachment-integration/.
JSONL records actual imported mcis_service.__file__ to prove each run exercised its
respective tree. Baseline git HEAD was3aba2bf03e393909c611489ae573a887087637ac and
tracked git diff was empty. No baseline product file was modified.

Reproduction from combined service/ uses `.venv/bin/python -m pytest -q
--import-mode=importlib ../tests_acceptance/main-safe-attachment-integration/test_plain_policy_blocker.py`.
For baseline, run that same absolute test path from pristine-main service/;
MCIS_BLOCKER_OUTPUT selects the JSONL evidence file. No secrets or real records are used.

Code inspection is consistent: old export allows investigator roles and holds a writer
transaction, but report/interview/history-specific permission gates do not require plain
registered evidence and ordinary audit category access in this no-history case. The new
container gate only runs full permission checks for ZIP-like member bytes. It repairs the
container bypass, not the broader old-export authorization matrix.

**Disposition:** inherited main defect, still present in the combination, blocks current
integration acceptance. Stop scope expansion and keep local candidate pending explicit
legacy-export authorization/migration adjudication. Do not push, merge, deploy, weaken
tests, or claim all revocation paths covered. No product repair attempted by reviewer.

2026-11-14. Local tree /workspace/mcis-main-safe-integration, actual main base
3aba2bf03e393909c611489ae573a887087637ac. Reviewer did not alter product code, stage,
commit, push, merge or deploy. Combined staged files were inspected plus the implementer's
new unstaged legacy-package container gate. This is review of the resulting tree, not a
claim that every original frozen hash still matches after intentional conflict resolution.

## Executed combined tests

From service/:

```sh
.venv/bin/python -m pytest -q --import-mode=importlib \
 ../tests_acceptance/main-safe-attachment-integration/test_independent.py \
 tests/test_restored_attachment_filename.py tests/test_report_bundle_attachment_access.py \
 tests/test_recorded_digest_delivery.py tests/test_intake_authorization_transaction.py
```

**72 passed in25.61s**, no skipped cases. Includes10 newly independent combination probes
and62 existing feature/security regression cases. Output is results.txt under the acceptance
directory. First7 independent probes passed before addition of3 further cases (first-results.txt);
that first run ALREADY included the implementer's new legacy export gate and is not repair-before
reproduction evidence. Parent's gate-before.txt separately records its two failing reproductions.

New probes cover original and prefixed ZIP registered through old evidence API without report
rows or intake receipts; low role denied both individual GET and whole export, Lead obtains
exact bytes; same verified ZIP bytes still gated if disk changes after read; original inode
content tamper returns409 without success audit; historic filename/hash restored with limited
role refusal and inactive receipt; synthetic gate exception produces no Access; ordinary
legacy text remains exportable/readable; actual policy PUT revocation blocks both GET/export.
All data are synthetic and local; no remote attacker capability is demonstrated.

## Per-file security inspection

| File under service/mcis_service unless stated | Finding |
|---|---|
| common/safe_files.py | Parent fds pinned, O_NOFOLLOW/O_DIRECTORY mandatory, regular-file check, <=1MiB read requests, caller budgets and fd cleanup retained. No inode immutability or aggregate memory guarantee. |
| evidence/safe_content.py | Missing-file compatibility retained; unsupported503 and unsafe409 fail closed. Legacy sys.maxsize is not a practical resource limit. |
| evidence/recorded_content.py | Trusted original digest, Register agreement and chained Change validated; hashes the same returned immutable bytes. Does not establish provenance. |
| evidence/router.py | Conflict resolution keeps WRITE_LOCK + BEGIN before source/policy reads, read_recorded and then protect_container on the same bytes before Access. Neither digest nor container gate lost. |
| evidence_intake/router.py | Safe read and unsupported503 retained; final commit authorization under writer reservation; intake download reserves transaction and applies container gate before Access. |
| package/mcase.py | build_files uses read_recorded. New legacy assemble gate visits actual member bytes before ZIP construction in existing transaction. Gate denial rolls back any earlier package.export audit. Working archive branch already requires full_content access. |
| redaction/write_access.py | Only initial recognized SQLite reservation contention plus successful rollback gets not_committed503. Later failure remains outcome-unknown. |
| redaction/router.py | Role/schema checks precede reservation; policy writes/audit follow it. No automatic retry introduced. |
| report_output/attachment_access.py | Conservative PK or is_zipfile recognition without member extraction; existing all-category full-content gate. Labels/extensions cannot downgrade ZIP/DOCX. Not general DLP. |
| working_records_archive/service.py | Shared descriptor reader retains historical path validation, budgets and typed errors. Full-content permission remains before working archive assembly. |
| working_records_archive/filename.py | Rebuilds original binding against bytes/case/evidence/key/digest; quotes filename rather than emitting raw header syntax. |
| working_records_archive/router.py | Permission and historic identity/content hash precede validated filename and Access; no active receipt recreation. |
| web/src/evidenceIntake/history.ts | Parses constrained UTF-8 attachment name, keeps bounded bytes, SHA and current identity checks before returning download data. |
| web/src/evidenceIntake/EvidenceIntakePanel.tsx | Uses verified parsed filename; wording says download initiated, does not claim actual disk persistence. |

Reviewed existing main audit/service.py and reports/access.py reservation-proof relationship:
main already bypasses Python audit lock only for valid same-thread/same-transaction live SQLite
writer proof. Combination preserves this substrate; no audit lock inversion fix was silently
removed. This review's72 run covers intake revocation; separate original lock-contention suites
remain the appropriate detailed proof and are not relabeled as newly independent tests here.

## Newly discovered integration gap and repair assessment

As reported/reproduced by implementer, old registration of ZIP content in a case with no
report/intake history could receive403 on individual GET but200 as a member of old .mcase
export. Existing report-row/package gates did not classify such copied container bytes.

Inspected minimal repair: in old assemble(), after build_files, apply protect_container to
all member byte values before manifest/ZIP assembly, inside the already reserved transaction.
No extra file read, type-label inference or altered digest is introduced. Archived working
path has its full-content gate already. Independent normal/prefixedZIP and plain-text tests
confirm intended narrow behavior and rollback. No remaining blocker found for that gap in
this inspected tree; do not describe the original unpatched combination as safe.

## Limits / no unconditional release approval

This is a local combined review, not production integration approval. Existing baseline
HFACS failure/.NET absence, full-suite outcomes and browser limitations must remain in the
coordinator's report; reviewer did not independently execute browser, .NET or whole-system
CI. No true-browser file save or UI identity transition acceptance is claimed by source review.

Trusted SQLite/process and cryptographic digest assumptions remain. The filesystem itself
is mutable; hashing prevents delivery of mismatching memory snapshots but does not stop
writes or establish source provenance. Missing/malformed digest migration behavior and
legacy package omission of absent files persist. Hash metadata from imports/declared-only
registration is not authenticated original acquisition. Memory accumulation, large-file
writer-lock duration, other reader/writer endpoints and production identity remain outside
this bounded combination. #69 multimodal changes and low-lock research are not in this tree.

Conservative container gating includes DOCX/anyZIP and can refuse previously allowed copied
containers; it is intentional permission tightening, not silent transparent compatibility.
NonZIP report copies are not classified by this gate. No authenticated remote exploitation
claim follows from synthetic local mutation tests. Main/remote remained unchanged by reviewer.
