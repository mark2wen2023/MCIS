# Report + safety-recommendation archive: blocked draft, no enabled format

This design is NOT an implemented contract and does not allocate a released version. Current parsers continue to reject proposed future outer1.5.0; tests must not advertise it as supported. Existing1.0–1.4 semantics and all policies remain untouched.

## Why a direct extension is not ready

recommendation.schema requires at least one causeNodeIds string and describes ECFC/HFACS/COLREG causes, but the current service stores these as labels without a typed, case/revision-bound resolver. The web form accepts comma-separated labels (default COLREG-R19); a rule label cannot safely be guessed to mean a particular case analysis/finding. A locally absent cause row does not prove that the author lacked an external source; it means the archive cannot automatically prove complete local closure from these fields. Empty strings/duplicates also pass the current Python endpoint; C# filters blanks/duplicates and rejects all-blank lists. That discrepancy is observed, not fixed in this slice.

RecommendationRow is active business state. Draft/Issued/Responded/Implemented/NotAdopted/Closed, progress, response records and transition history influence UI/report generation and subsequent operations. Importing it using existing put_doc does not make it inert. RecommendationRow has no archive-only marker or separate historical authority. Full report source snapshots cite a recommendation as registered; current archive validation deliberately rejects such citations. Replacing this check with ID-exists would establish register membership, not cause/dependency completeness or historical authorization.

## Smallest proposed supported combination

A future first candidate should choose **report + draft recommendation** only: status Draft, explicit empty responses/history, zero progress and no verification claim. Preserve complete original doc, row timestamps, original audit and source package; never strip unsupported fields to meet the subset. Require default policy and the same full-content permission checks before content and under the existing reserved SQLite transaction. Deny unknown tables, consultation, timeline/track/COLREG active state, agent content and all issued/responded/closed workflow states unless separately versioned and accepted.

Two distinct contracts must be resolved before enabling success:

1. Typed cause binding: an explicit extension (not guessed from causeNodeIds strings) binds every original label to a case-scoped source kind, object ID, revision/digest and retained authoritative artifact or record. Define the supported single source kind and its validation/resolution first. Preserve the original labels verbatim and mark external/unresolved references; an unresolved/missing/ambiguous/cross-case source refuses the active-combination export. The present recommendation API does not supply this binding. Do not manufacture one from label prefixes, taxonomy names, report text or a fresh digest.
2. Restored behavior: either active Draft restoration after complete validated dependencies, with subsequent actions separately authorized/audited; or explicitly **read-only archival recommendations** in a distinct table/API/view. The latter must keep mutation endpoints refusing historical rows and resolve original report citations through a marked historical source path without pretending current registered actionable state. Existing routes/UI do not implement this mode. Mixing the two designs under one successful receipt is not acceptable.

Suggested future envelope: a new outer profile, mandatory recommendation extension with exact original rows plus causeBindings and explicit restorationMode; mirror agreement required. Unknown version/mode rejects. A typed binding cannot claim source truth or authenticate old operators. Default role headers remain untrusted and no production SSO claim is possible here.

## Required acceptance before enabling

- One actually supported source kind: positive report→recommendation→typed source closure, exact original rows and evidence bytes, three empty-store generations, original audit/source bytes retained; report GET and source links resolve as intended.
- Missing/ambiguous/cross-case causes, all-blank/duplicate labels, altered digest or bound revision, invalid graph and unknown modules reject before mutation.
- Workflow graph validation: legal status transitions, non-replayed original responses and history, required state-specific reasons/progress, no silent downgrade to Draft. The first candidate rejects all nondraft states rather than implementing partial semantics.
- Explicit active-vs-inert behavior after import, including mutation attempts and report-source lookup. No silent reactivation of historical execution authority or proof-of-approval claims.
- Existing full permissions, default-policy restrictions, restrictions on source contents and real second-connection revocation ordering retained. Supplied package policy never grants destination authority.
- Inject failures after new rows, audit writes and staged publication; verify existing database/objects untouched, no false successful receipt, retry semantics match proven transaction outcome. Do not promise DB/filesystem crash atomicity or auto-delete uncertain objects.
- New unknown-version rejection by old readers, old1.0–1.4 regression, truthful UI preview/receipt/export scope and sandboxed real-browser acceptance before a UI completion claim.

No allowlist/parser/source-citation relaxation, migration or new active table is implemented in this investigation. Approval of a label's intended meaning is not a substitute for the missing resolver/model. Until one of these explicit restoration contracts and source bindings is implemented/tested, keep report+recommendation export409.
