# Durable working review trial UI

Separate module `extractionWorking`, profile `mcis-extraction-review-persistent-trial-v1`. Does not change ephemeral extractionReview semantics. Isolated component and trusted callback port, not mounted in current web/native application. No fetch, credentials, local/session storage, old role headers or production login. Host chooses provider and owns authorization.

Explicit list -> open/read, or generate and store an unreviewed original. Source quotes/spans/claims are read-only. Each item shows every prior working decision/reason/revision/time and an anonymous investigator identifier (not a name). Appending sends full decisions, expectedRevision and operationId; originals and prior revisions are never overwritten. Saved means working journal only, not official interview adoption or fact activation.

RequestId and operationId are distinct explicit UUIDs. Unknown write outcomes hide sensitive state and retain exact immutable request for retry. Optional explicit user action stops retry and reads the known proposal (or lists after generation); this does not cancel the server action and does not claim it failed. Nothing automatically generates a replacement operation. Read failure clears visible data and allows another authorized read. Context/port replacement clears memory; late callbacks discarded.

Any note or changed decision blocks navigation/generation/directory refresh until submission or explicit discard. Unknown write prevents discard/navigation except explicit recovery read. Scope/context/reply request identity verified, payloads bounded in UTF-8 bytes, record scope checked. Parsed minimal projections only. Original fingerprint and history prefix retained by port to reject rollback/rewrite within that port lifetime; remount can list/read durable host state. A new host/port relies on authenticated backing service, not browser memory as integrity evidence.

A trusted host may bind expectedProvider to fixture/local via the optional third port argument. The actual fixture test binds fixture. This expectation is not proof of real model identity; local model identity remains unverified. No real model tested here.

Limit: no actual browser/native IPC wiring or production identity. Stdio fixture's SQLite is real for its process lifetime but deleted on exit, so UI remount recovery is tested, not multi-process production retention.
