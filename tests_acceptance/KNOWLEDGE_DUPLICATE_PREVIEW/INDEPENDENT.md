# Independent review — knowledge duplicate preview

Reviewed the API-only bounded exact-match inspection against its development-only contract. No implementation modified, no model called, no repository write/push or deployment.

Initial independent tests: **10 passed / 1 failed**. Failing regression `test_card_identifier_format_fail_closed` changes stored row/card document IDs together to `../../not-a-card`; endpoint returns 200 with this malformed ID instead of rejecting malformed stored metadata. Implementer notified; red assertion retained unchanged. This is corruption validation, not evidence of arbitrary path access (the endpoint does not dereference IDs as paths).

Passing coverage: unauthorized roles rejected before database access; no outbound socket connection for public source URLs; response excludes approval/actor/body/source payloads; whitespace not normalized; incomplete scan without matches clearly flagged; malformed nonmatching source blocks all output; invalid request creates no candidate. All inputs synthetic; no model competence, production authentication, browser/UI, semantic deduplication, full-corpus search or CI claim.

Declared-role headers remain the pre-existing development identity boundary, not production authentication. No automatic merge/delete/publish occurs; exact source excerpt equality does not establish factual identity or rights.

Final disposition pending fix and rerun.

## Final rerun

Implementer added strict `KC-[0-9a-f]{32}` validation. Original red assertion unchanged and now passes. Final independent + primary run: **31/31 passed**, exit 0, 10.28 seconds (11 independent + 20 primary). No blocker found within this read-only development slice. This is local ASGI/TestClient with temporary real SQLite, not production auth, actual browser or CI.
