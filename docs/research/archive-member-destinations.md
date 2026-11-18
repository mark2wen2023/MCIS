# Existing archive member destinations — read-only handoff

Developer static review, 2026-11-18. No restoration, tests, models, browser, real case files or fault probes executed. This document adds no runtime support and is not restoration acceptance.

## Frozen scope

Product implementation inspected: `b4df82306d9bab87b938b9e447e27a64b0464406` (PR104 reference); main read back as `94d5e38c926fda232bb987b60fa9145e4bcf01a7`. Research parent/remote `research/restore-normal-case-registration`: `1fa13fdd87e3685bf938d9782b40105ad52733d5`. Line references below are to the **product SHA**, not the research worktree. Use `git show <SHA>:<path>` to reproduce. No claim that these branches are integrated.

All abbreviated module paths below are under `service/mcis_service/`.

`package_intake/parser.py:148-166,350-352` admits outer 1.0.0, 1.1.0 (HFACS), 1.2.0 (working records v1), 1.3.0 (working records v2/track history). Extensions must match versions. This does not admit arbitrary combinations. Research 1.4, conflict v2, image/audio candidates are NOT added to this supported list. Existing protection remains required.

## Member mapping through strict intake

DB means decoded rows, not preservation of the JSON member as an independent file. All original ZIP bytes are additionally retained by the intake wrapper as described below.

| Member | Destination and scope | Exact code evidence |
|---|---|---|
| `manifest.json` | Validation/response metadata; no standalone product file or manifest table. Retained within original ZIP. | `package_intake/parser.py:148-185`; `package/mcase.py:403-405` |
| `case.json`, `case.ext.json` | Combined and normalized `CaseRow`; defaults/time normalization can change representation. Do not promise identical reserialized bytes/revision. | `package/mcase.py:410-425,454` |
| `vessels.json` | `VesselRow` per vessel | `package/mcase.py:457-458` |
| `environment/observations.json` | Optional validated `EnvironmentObservationRow` | `package/mcase.py:434-456` |
| `derived/tracks/{vesselId}.track.json` | `TrackPointRow`; not separately written as track JSON | `package_intake/parser.py:245-265`; `package/mcase.py:459-463` |
| `evidence/index.json` | `EvidenceRow`; fallback custody reconstruction exists in legacy importer, not evidence of strict-intake missing-index support | `package/mcase.py:464-476` |
| Registered evidence members under `raw/` or `evidence/` | Files at case-relative paths, excluding index and `.keep`; strict parser requires registered paths and matching digest. This is current archive-byte consistency, not historical authenticity. | `package_intake/parser.py:266-279`; `package/mcase.py:477-481` |
| `audit/custody.jsonl` | `CustodyEventRow`, preserving each nonempty line; chain validated | `package/mcase.py:446-452,501-513` |
| `audit/audit.jsonl` | Audit rows through `audit.append_raw_line`; an additional import event is appended | `package/mcase.py:514-517,525-528` |
| `audit/agent.jsonl` | Optional derived subset checked against main audit; not a separate imported table/file | `package_intake/parser.py:339-342`; export `package/mcase.py:174-176` |
| `access-policy.json` | `AccessPolicyRow`; strict intake accepts only default policy, not arbitrary archived authorization | `package_intake/parser.py:200-201`; `package/mcase.py:498-499` |
| `analysis/timeline.json`, `analysis/time-alignment.json`, `analysis/colreg.json`, `recommendations.json`, `consultation/rounds.json`, `agents/drafts.json` | Strict intake permits only specified empty values. Legacy importer has current-value DB writes, but these do NOT establish supported nonempty strict restoration or complete history. | `package_intake/parser.py:238-244`; legacy branches `package/mcase.py:482-497` |
| `testimony/{id}.json` | Not a supported standalone member in strict intake; working archive removes these and carries records in authoritative extension | `package_intake/parser.py:229-279`; `working_records_archive/service.py:112-114` |
| `hfacs/backup.v1.json` | Validated current worksheet, revision audit and archived request rows; requires extension validation, not executable requests | `hfacs_drafts/archive.py:17,137-143`; `package/mcase.py:518-520` |
| `working-records/backup.v1.json` | Interviews, reports, report snapshots with timestamps; archived manual receipts, import history, artifact metadata/lineage. Both working versions use this filename. Historical receipts are not current execution authorization. | `working_records_archive/validation.py:10-17`; `working_records_archive/service.py:157-172`; `package/mcase.py:521-524` |
| Declared `history/artifacts/{sha256}.bin` | Artifact metadata in DB plus exclusive file creation. Current retained source ZIP becomes one such artifact on re-export; existing artifact lineage retained. | `working_records_archive/service.py:115-130,167-171` |
| Required directory `*/.keep` | Structural ZIP placeholders; not individually restored as files by raw/evidence loop; directory existence is not promised for empty placeholders | `package/mcase.py:140-141,477-481`; `package_intake/parser.py:277-279` |
| Other members / nonempty unsupported states | Strict parser rejects, not an unknown member to silently drop. Legacy direct importer behavior is not equivalent to strict intake. | `package_intake/parser.py:238-244,277-279`; `package/mcase.py:392-402` |

## Wrapper-created files and receipt

`package_intake/router.py:178-216`: parse first, hold process WRITE_LOCK, create staging directory, enter DB session and BEGIN IMMEDIATE, import into staging, write/fsync `_package_intake/source.mcase`, add existing `IntakeReceipt`, flush, rename case directory to final target, then exit DB session and return. The original ZIP therefore retains member bytes including metadata that is otherwise only decoded. This is conditional on this wrapper; do not claim the low-level `import_case` itself retains the ZIP.

`working_records_archive/service.py:145-152` rejects per-case files outside the constructed supported inventory. Do not expand its allowlist to accept image/audio job directories. Product exports select formats in `package/mcase.py:195-267`; legacy 1.0 serialization without full preparse is not proof every serialized state is restorable.

## Research observer coverage versus product writers

At research parent `1fa13fd`, `research/conflict_source_intent/publication_observer.py`, function `layout_files`, covers raw/evidence members plus retained source ZIP. It excludes working-record artifact files. `inspect_publication` also expects a research operation marker and returns `restore_ready=false` even when observed files match. Product intake does not write that research marker. These are different protocols, not interchangeable implementations.

Known writers relevant to this mapping:

- `package/mcase.py:477-481`: raw/evidence file creation.
- `working_records_archive/service.py:167-171`: historical artifact file creation plus DB metadata.
- `package_intake/router.py:185,197-216`: staging, retained ZIP, rename and cleanup.
- `package/mcase.py:454-524`: database reconstruction; wrapper adds receipt and import audit.

Not covered by a proof here: other evidence replacement/intake writers, track import writers, report-output/attachment writers, image/audio workers and their `worker.log`/home directories, other processes or local filesystem mutation. This review did not exhaustively enumerate these writers or inspect any runtime contents. Existence of WRITE_LOCK does not prove ownership across processes or a frozen filesystem snapshot.

## Remaining consistency conditions and next bounded step

1. A shared layout inventory must distinguish DB-only members, actual files, retained source ZIP and structural placeholders. Before reusing the research observer, add declared historical artifacts to its *explicit supported contract*, not a permissive prefix. Preserve existing rejection of unclassified files. This is a proposed task, not implemented or validated here.
2. SQLite row consistency and sequential file reads do not establish a common immutable snapshot. Need documented writer ownership/quiescence or an immutable-copy protocol before any ready promotion.
3. File rename occurs before DB-session commit completes. Cleanup exists on BaseException. No joint filesystem/DB transaction or durable reconciliation is proven by this ordering; this static observation is not a reproduced crash or proven data-loss incident. Unknown commit must not imply success, safe deletion or retry.
4. Research migration/normal-case identity is isolated; product list/read/export/receipt entries are not universally wired. Preserve ordinary legacy cases and do not enable experimental restoration from one gated entry alone.
5. Next ordinary verification, after contract review: tiny synthetic 1.2/1.3 package containing a declared historical artifact; compare expected inventory with importer destinations in a temporary directory, without publishing, fault injection, permissions probes or models. Test selection must be reviewed individually; no paused nodes or write-refusal probes. No such test ran in this task.

## Self-check and limits

Only this report changes. Source lines were read from frozen Git objects; branch heads were read back before commit/push. No tests were run, so no new pass count or restoration claim. No credentials, database, media, private material or generated runtime files are included. Production protections, permissions and unsupported-state refusals are unchanged. No merge/deployment, browser, HFACS execution, crash or uncertain-commit validation.
