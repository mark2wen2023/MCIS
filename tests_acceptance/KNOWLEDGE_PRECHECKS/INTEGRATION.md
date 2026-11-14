# Local-only composition of host + actor checks

Base3aba2bf; host input is published dddd7dd96f598f8473325f4a4b4f3373c033df03 implementation,
actor input is current isolated unpushed fix. No remote ref moved/merged.

Both touch knowledge/router.py:create preamble. Required composed order:
internal(ctx) -> validate_actor(ctx.operator) -> validate_content(body) ->
validate_new_source_host(body['source']) -> existing WRITE_LOCK/session/BEGIN IMMEDIATE.
Host helper before output and actor helper before digest are independent additions. Review retains
role rejection -> actor validation -> review-body validation -> existing write transaction. No host
validation added to historic review/archive, preserving old recorded source bytes and URLs.

Potential line-level Git conflict: host commit changes original create line; actor changes the same
line. Resolve by preserving BOTH calls in above order, not choosing ours/theirs. Do not transplant the
whole isolated checkout over main. Existing actor validator remains text-only, no identity guarantee.

The combined extra order test confirms invalid actor stops before content/host validation; valid actor
with bad host calls both guards and refuses without candidate/audit/snapshot/epoch writes. Full selected
knowledge suite also covers historic bad-host archive save/export and Unicode actor preservation.
No deployment or production DB use; test clients are temporary local apps.
