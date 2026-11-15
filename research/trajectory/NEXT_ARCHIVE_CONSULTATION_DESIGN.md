# Next bounded archive slice: consultation (design only, NOT enabled)

Base4099d235d29ab9480d2652bdad9d46450e89c610. Remote main checked94d5e38.
Independent research branch; only synthetic tests and documentation. No runtime,
permission, parser, table whitelist or archive schema changes. This is not a claim
that complete case archive or consultation restore is implemented.

## Inventory from actual code

| State | Existing persisted facts | Closure / history prerequisites |
|---|---|---|
| Safety recommendations | RecommendationRow doc and row timestamps; causeNodeIds, status/history/responses, notes; safetyrec.* audit | Cause IDs are references without generation-time cause snapshots. Draft content updates replace fields; audit uses400-character summaries, so not a complete revision store. Reports can cite recommendations; working archive validation rejects registered citations to this unsupported module. Need same-case cause-source semantics and full original/current record/history association; don't invent missing history. |
| Consultation rounds | ConsultationRoundRow: roundNo, draftVersion, optional draftSha256, dates, parties, full replies/waivers/comments and single decisions; consultation.* audit | Fewest external dependencies, but draftVersion is a free label; no reportId/immutable report artifact binding. Supplied SHA is optional and is not looked up against stored content. Full comments/feedback are in doc; audit summary alone is insufficient. Keep party/comment references, all earlier rounds, row timestamps and audit exactly. |
| Agent drafts | AgentDraftRow: target/kind/payload/citations/model/promptDigest and review status; agent.* audit | Payload is open-ended. Review may modify payload and apply to interview statements or timeline. Original pre-modification payload is not a separate full revision. Need exact target/citation closure and applied effect association, plus inactive imported review semantics. Unrecognized targets/kinds refuse. No model call or ECFC inspection performed. |

Sources: recommendations/models.py and router.py; audit/service.py (_summ400);
agents/models.py, router.py (_apply/review); schemas/recommendation,
consultation-round, agent-draft; working_records_archive/validation.py sources().
Full original recommendation/consultation access is guarded by
recommendations/access.require_content and reports/access full-content policy.
Package default-policy restriction, same-case checks and audit protection must remain.
Self-reported role headers are not production authenticated identities.

## Chosen smallest next design

Choose consultation rounds, initially **closed rounds only**, on top of working-v1
with optional bounded timeline. Do not combine track-history, recommendations,
conflicts, agent drafts or other unsupported state in the first increment. This is a
proposal, not permission to remove/refuse some rows from an otherwise accepted case:
if ANY round or linked source cannot be included, refuse the ENTIRE package.

A future explicitly versioned profile (tentatively1.5, not reserved/implemented)
would carry `consultation/records.v1.json` with exact caseId, format/version and
{key,createdUtc,updatedUtc,doc} rows. Validate round key/number uniqueness and ordering;
unique party IDs; reply/waiver exclusivity; comments belong to a reply in the same
round/party; decisions/actors/times/closure retained exactly. Persist stored docs,
not dynamic daysRemaining/partyStatus/allReplied views. No fake new signatures.
Keep original audit JSONL and verify applicable events against the represented IDs;
retain summaries as summaries, not pretend they were full revision snapshots.

Required additional source association: a **server-created**, immutable round-to-
report binding, specifying case, exact reportId/version and canonical document digest,
and separately the archived rendered original file digest if that was actually sent.
A JSON document digest is not interchangeable with PDF/DOCX byte SHA. Preserve the
bound report snapshot/artifact with the round. Existing draftVersion/draftSha256 are
preserved as declarations, never upgraded into verified binding. New archive fields
must not be supplied by untrusted metadata and called server verification.

Export -> restore -> export must preserve original docs, timestamps, bindings, files,
receipts, audits and lineage. Imported closed status is a historical claim, not a new
review; no open-round timers, automatic notification or replay authorization activated.
Old1.0–1.4 semantics remain unchanged; older readers reject the new profile. Old
unbound rounds must stay explicitly unsupported by this first verified-binding
profile, without rewriting them or guessing from a version label; preserve originals.
An eventual unresolved-source preservation mode requires a separate explicit contract,
not silent acceptance into the verified mode.

## Concrete blockers and ordinary test evidence

`service/tests/test_consultation_archive_readiness.py` uses only synthetic temporary
apps/SQLite and normal HTTP, with existing LeadInvestigator test headers:
1. A round opens201 with free draftVersion, blank digest and ZERO stored reports;
   stored round has no reportId. Cannot prove which immutable report was circulated.
2. A supplied64hex SHA also opens201 with ZERO stored reports; digest is a declaration,
   not server-verified reference to bytes. No attempt to forge a historical record.
3. Full long feedback remains in round doc. Audit after is truncated400 chars, but
   a second decision is409 with unchanged store. This corrects an early read inference:
   consultation decisions are NOT freely overwritten, and feedback was NOT lost.
4. Timeline+consultation export409 with no ZIP/no mutation, retaining bounded guard.

Additional discovered gap in case1: **consultation-only** export returns200 with1.0,
then restricted intake returns422 PACKAGE_INTAKE_INVALID with target unchanged.
The ordinary test now characterizes this actual behavior, not endorses it. Initial
run expecting409 had1 failure/2 passes; after explicit characterization and adding
mixed-state refusal,4 tests pass. The legacy selection omits consultation from
has_history; current runtime is unchanged, so this gap is NOT repaired by this branch.
Main code inspection suggests inheritance, but exact-main runtime was not rerun here.
Do not describe all complex cases or every export as affected.

## Implementation gate / next verification

Do NOT enable a new archive version now. First address the consultation-only export
preflight gap in a separately reviewed fail-closed patch without granting restore;
then establish the server-side immutable sent-document binding and migration policy.
The existing code is insufficient to assert this binding without adding a new source
capture contract. Preserve old data unmodified and old packages rather than infer it.

Once those prerequisites are independently reviewed, test closed-round multi-party
reply/waiver/decision closure, same-case report/artifact association, long fulltext,
three-store byte/row/audit preservation, missing/unsupported sources -> whole refusal,
old-version rejection and unchanged target on ordinary injected failure. Test source
mutation/concurrency only within separately authorized scope; no restricted operations
are authorized by this design. Browser/LLM/HFACS/full-suite and independent acceptance
have NOT run. No production source files or data changed, no push/merge/deployment.
