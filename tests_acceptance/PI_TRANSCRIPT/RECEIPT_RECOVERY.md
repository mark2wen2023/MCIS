# Recovery receipt review · 2026-11-14

PR56 observed head ee1814fbd73eb34931698d4c566db404ac1bea4d, open/draft/unmerged.
Local directory is a snapshot, not a Git checkout. Changes below are not claimed
published. The fourth historical live run remains unknown and was not retried.

Added metadata-only local JSONL recovery receipts to the explicit public-report
launcher. Fixed restricted phases/error codes, bounded counters, mode0600 file
in unique mode0700 directory; fsync before each external model dispatch.
Terminal result is immutable through API. Source/model/key text and arbitrary
exceptions cannot be written. Started-only or request-start without terminal
must be interpreted as unknown. No automatic retry. Temporary disk receipts are
not power-loss/container-destruction backups, signatures or production audit.

Independent reviewer reproduced invalid-key launcher execution without Python
or network, abrupt child exit with unknown request state, forbidden payload and
error strings, terminal immutability and lifecycle sequences: primary1 plus
independent5 =6/6. Final npm test:60/60, zero skipped (34 prior remote/runtime,
20 final diagnostic,6 receipt). Python remote primary+independent:63/63, zero
skipped,19.02s. Existing Starlette warning only. Counts are local and overlap
older evidence; neither CI nor new real-model acceptance.

Strict final candidate equality and quote/source/auth validators are unchanged.
No new actual DeepSeek call, merge, deployment or business-data persistence.

Files: runtime/run-receipt.mjs, run-receipt.test.mjs,
run-receipt-independent.test.mjs; live-probe.mjs integration; package.json test
registration. Earlier final-diagnostic files were local and need comparison
against remote tree before publication.

## Subsequent separately authorized live observation
After offline review, a new explicit run (202d715c) completed3 real model rounds
and2 real tools. Candidate validation returned PendingReview; final raw model
text differed only in outside-string JSON whitespace and was rejected with
MCIS_FINAL_UNVALIDATED_FORMATTING. No new acceptance claimed. The phase receipt
has a terminal not_accepted record. This narrows the formerly unknown rejection
cause without weakening validators. No second provider retry was made.
