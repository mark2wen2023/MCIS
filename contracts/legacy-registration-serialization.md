# Serialized legacy registration (existing API)

Acquire existing process WRITE_LOCK and reserve SQLite writer before any case/policy read,
next_id allocation or file write. Hold through existing DB transaction completion. A prior
committed revoke must be seen; an earlier reservation prevents concurrent policy commit.
Successful concurrent registrations must have distinct identities and matching immutable
metadata/custody/file content; no upsert collision from simultaneous next_id.
Keep strict Base64/expected SHA, content-only/SHA-only, valid empty bytes and existing
permissions. Do not claim an admission quota: parsed request bodies can wait in memory.
No shortened locks. Busy/error/unknown commit behavior is unchanged, no automatic retry.
Filesystem and database are not crash-atomic; later DB/I/O failure may still leave a file.
This patch does not introduce rollback cleanup that could delete another writer's content.
