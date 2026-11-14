# Existing issue directory trial

Problem addressed: the prior component could create records and read a supplied issue UUID, but offered no authorized way to find an existing card after leaving a page. The trial adds an explicit case-scoped directory, then opening a card and reading full history before further append.

The host `list` command requires only profile/context/request/case fields and rejects issue, write and pin fields, including null. It invokes the existing protected trial issue-list API, checks authority and case incarnation/epoch before and after, then projects only canonical issue UUID, revision, opening-note preview (200 characters), latest kind and unreviewed status. At most100 unique summaries; no actor/token/source body metadata is exposed. A list is a point-in-time aid, not a write capability or review decision.

Opening an existing card never manufactures revision0 from its summary: full read must succeed before append. New cards remain separate and use new operation/issue identifiers. Busy or uncertain writes cannot be switched away; unsaved text must not be silently discarded by navigation. Context changes invalidate delayed results. API revision checks still prevent overwriting concurrent additions; source incarnation/SHA pins remain in force.

Still an isolated nonproduction component and host trial, not deployed/mounted production UI or login. Synthetic stdio fixture records disappear on normal host exit; opening existing cards is verified within that trusted temporary host, not promised durable user storage. No expert approval/consensus or real LLM introduced.
