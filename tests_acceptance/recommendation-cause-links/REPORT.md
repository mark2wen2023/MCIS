# Recommendation cause-label data quality, archive boundary retained

Branch fix/recommendation-empty-cause-links, direct latest fetched main25b9df6.
No dependency on outstanding timeline/report-test branches.

## Actual model and unresolved archive closure
RecommendationRow and ConsultationRoundRow are active JSON business records.
Recommendations include causeNodeIds, state, responses and transition history;
restoring them as current rows can restore active workflow semantics. Report
snapshots preserve registered sources, not independent verification of underlying
causes. causeNodeIds are untyped labels, without case/revision/digest-bound source
resolution. Current web splits comma/whitespace-separated labels and removes
empty tokens. Working-record archives reject unsupported recommendations and
consultation tables; no safe versioned report+recommendation round trip exists.
This work does not remove that gate or interpret labels as genuine evidence.

## Reproduction and smallest fix
New HTTP regression on unchanged main:8 failed,4 passed in3.93s. All eight failed
because create/patch accepted four blank-only label forms (empty, ASCII whitespace,
ideographic whitespace, NEL/NBSP) instead of422; this is real service behavior,
not a mocked model. An array length of1 previously satisfied the contract despite
containing no actual label. C# source also requires at least one nonblank cause,
but its filtering/deduplication behavior is not copied and C# was not executed.

Now create and explicitly supplied patch labels require at least one nonblank
string using existing _core_blank definition, after permissions and existing
lifecycle/domain priority. Explicit PATCH null also rejects with422. No writes
precede the new check. Mixed/duplicate/nonblank labels retain exact input strings,
order and spacing, and existing blank-only rows survive unrelated updates without
rewriting. Unknown labels remain accepted as unresolved declarations. This does
not solve typed links, source authenticity, causality or migration closure.

New-write compatibility tightening is explicit in contracts/recommendation-cause-input.md:
unknown external clients relying on blank-only labels must handle422. No changes
to historical stored schema or archive parser, and no production role grants.

## Tests
Initial12 regressions plus existing recommendations lifecycle and content-access
suites:89 passed in21.14s (after.txt). Three additional tests cover explicit null,
non-Draft priority, historical-row compatibility and actual report+recommendation
export refusal. Final complete focused module:15 passed in4.78s (focused.txt).
These15 overlap the89; do not add totals as unique coverage. Independent review
is separate. Synthetic local HTTP/SQLite, genuine API handlers; no model or SDK.

Coverage: invalid new writes preserve all ORM-table snapshots; valid exact labels
read back and audit chain verifies; restricted roles403 precede domain validation;
Issued patch409 remains; combined report/recommendation export409 and unchanged
DB rows. This proves sequential database behavior for tested paths, not filesystem
crash atomicity, concurrency/SSO, general reference closure or complete archive
compatibility. Existing no-network tests do not constitute real model validation.

No software installed/downloaded. No remote push, merge or deployment. Browser,
real AIS, real HFACS and production identity remain unverified; long locks and
memory constraints unchanged. Future combined archive needs a separately reviewed
versioned binding and active-versus-historical restoration contract.
