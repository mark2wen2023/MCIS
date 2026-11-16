# Second-round view — developer synthetic evidence

Parent26451febf955f4b6d7654e9a4b32ca70c2ec4c13. New isolated revision6 ledger,
first-round reducer delegated unchanged to revision5. Single explicit action
bind_round_two_view takes no client opinions/digests. Requires all four first-round
seats sealed, intact candidate/context/seal associations, no pending tools/requests.
References and full-view digest commit with state/operation/audit in the shared DB.
Full original candidate bodies stay in their original per-ticket transcripts; no
truncation, summary substitution, backfill or client re-upload. Read-only replay
and expansion return all four originals and fixed public packet, never dispatch.

Actions remain <=4096 ASCII-serialized characters, operations<=128, each seat<=2,
global<=16 (first round only<=8). Full material view <=262144 ASCII bytes including
newline; oversized view rejects instead of segmentation. No second-round requests
or adapters enabled. Bound state permits no further new operations; cannot claim
round-two execution or expert completion. Old revisions are not continued/migrated;
missing old/new view remains unknown. Pinned packet file still required; missing
or invalid material blocks. Digest consistency is not independent authenticity.

Developer result4 passed in0.44s, zero skips. COMMAND.txt has exact four nodes.
All new nodes reviewed before execution; rejection checks pure reducer only,
no write-refusal probes. Synthetic reviews, existing public textual packet and
temporary SQLite. No paused/security/process/Pi/model/browser/full-suite tests.
Not independent acceptance, actual crash/uncertain commit/concurrency or production
identity verification. No complete second-round protocol, no resume, HOLD remains.
