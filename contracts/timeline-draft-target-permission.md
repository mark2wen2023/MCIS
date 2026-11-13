# Target permission on timeline-event draft review

Change proposal registered before implementation: existing agents draft review
currently checks agent_drafts permission but the timelineEvent application
branch must ALSO require existing timeline ReadWrite within the same write
transaction before creating the event. No new role, permission, schema or API.

Affected prerequisite: reviewer is Investigator or LeadInvestigator, has
agent_drafts write access, but has timeline ReadOnly/Redacted/Deny; a
timelineEvent draft is available. The old branch allowed confirmation to write
despite target permission. This is an authorization consistency defect in
the local role-policy system, not proof of unauthenticated remote exploitation.

Confirmed/Modified require timeline ReadWrite; otherwise existing403 error.
Failure rolls back draft status, event creation and review audit together.
Rejected remains allowed under existing draft-review permission, since that
branch does not create timeline events. Authorized review remains unchanged.

This does NOT bind evidence IDs, source versions, original bytes or reviewed
observations. The generic citation schema currently requires only quote;
needsReview=false is not an observation approval. A source-binding slice needs
a server-owned snapshot with legacy/imported-draft invalidation rules; no
caller-provided payload flag is adopted as an authorization credential here.
