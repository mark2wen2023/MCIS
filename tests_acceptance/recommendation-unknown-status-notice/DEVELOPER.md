# Unknown notice across status snapshots — developer evidence

Base717c683f7bc38a3514735c4724d542ad61a5c44d. Independent branch
fix/recommendation-unknown-status-notice; no other product change.

Synthetic ordinary failed progress save followed by same-ID Implemented snapshot
hid progressNotice inside Responded-only controls. Initial loose assertion matched
sourceChanged wording and passed falsely. Tightened assertion to startsWith 保存结果未知
then failed on unchanged product. This explicitly distinguishes source-change advice
from actual unknown submission notice; source advice is not a conflict blocker.

Move progressNotice outside status-specific controls. No lock, request or permission
logic changed. Test requires visible unknown notice after status change, no progress
button for Implemented, then same-ID Responded restores a disabled button; direct
callback still dispatches no further PATCH. Existing draft assertions remain.

Reviewed exact commands from web (existing dependencies):
- node tests/recommendation-progress-flight.test.cjs: 7 synthetic scenarios passed;
  the ordinary failure scenario now includes status transition assertions (not a
  separately counted extra test).
- node tests/recommendation-progress-snapshot.test.cjs: 4 continuous synthetic cases passed.
- npm run build: TypeScript/Vite passed, 768 modules, JS1865.95kB/gzip603.02kB;
  existing large-chunk warning remains.

No browser/visual, real HTTP/backend, real data/seeds, models, HFACS, paused or
write-refusal/security tests. In-memory notice survives same-ID snapshot only, not
navigation/unmount. No multi-user or server-version guarantee. Independent review
pending; no merge/deploy.
