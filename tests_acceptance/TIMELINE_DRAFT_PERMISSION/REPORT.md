# Timeline-draft target write permission

Baseline commit:28c14d5f7764df71489ae31a4c0a8e298150ed1a.
Native implementation and separate native independent reviewer.

## Reproduction and scope
On a temporary real SQLite case, Investigator had agent_drafts ReadWrite and
timeline ReadOnly. Confirming a timelineEvent draft returned200 and created
TE-13 before the patch. The separate reviewer independently restored the old
_apply behavior in memory (not source files) and reproduced the write.
This requires access to the local service and the described role-policy
combination. It is not evidence of an unauthenticated remote attack.

## Fix and verification
The timelineEvent Confirmed/Modified branch now checks existing timeline
write permission inside the existing review transaction, before event creation.
No new permission, role or trust in caller assertions is introduced.
Rejected creates no event and remains allowed by existing draft-review policy.
Unauthorized confirmation rolls back draft status, event and review audit.

15 new regression cases passed:2 roles x3 insufficient permission levels x2
apply decisions,1 rejection-without-target-write case,2 authorized success cases.
The independent reviewer reran all15 and added1 historical in-memory repro.
The historical test intentionally removes the guard only inside that test's
monkeypatch; it does NOT mean the patched application permits the operation.

## Wider regressions are NOT all green
Existing test_agents_colreg_sim.py and test_agents_w20.py produced8 passed,
1 failed and31 setup errors. The failures concern existing full-interview
content access returning403, before reaching this timeline branch.
Restoring the pre-patch _apply in memory and rerunning those same old tests
gave exactly8 passed/1 failed/31 errors. No existing tests were removed or
relaxed. This establishes the observed failures predate this change; it does
not certify the entire agent subsystem. The issue remains separately open.

No model call, browser/CI/full-system acceptance, production authentication,
evidence-version binding, merge or deployment claim. Source IDs/versions need
a server-owned snapshot design plus old/imported-draft invalidation, not a
caller payload flag or needsReview=false treated as human approval.

Final targeted combined rerun:17 passed, zero skipped (15 new +1 historical repro +1 existing authorized workflow),5.79s.
