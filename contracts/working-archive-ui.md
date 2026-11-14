# Working-history supplement local file trial

Separate isolated module `workingArchive`, profile `mcis-working-history-archive-trial-v1`. No route mounting, production login, credentials, fetch, arbitrary path access or remote delivery. Trusted fixed-scope callback owns current authorization.

Explicit export prepares a supplementary JSON package, not a full case backup. Download click re-exports via the host to recheck current authorization/source; SHA and actual bytes must match the prepared version before local Blob/download callback delivery. Changed package requires new preparation/confirmation; failures clear download/history caches. Temporary Blob URL is revoked after click and on context cleanup. Tests use a local download callback and do not establish that a real browser wrote a file to disk.

File selection reads only an explicitly chosen File in memory. Filename is React text only, never a path or RPC field. UTF-8 JSON <=8MiB; parse depth<=32 and <=1,000,000 nodes; canonical Base64 for bounded RPC <=12MiB. Selection alone never uploads. File-read epoch and scope epoch prevent late files after context switch or competing actions. Import requires explicit button, and the host performs authoritative full format/hash/permission validation. UI structural checks are not provenance authentication.

Unknown import retains identical package and requestId for retry and hides history. Busy/unknown blocks selecting another package. Explicit stop-retry/list is not rollback/cancellation and does not assert whether the original import saved. Authorization failures clear visible remote history and downloadable bytes. Context changes clear all state.

Imported content is always untrusted historical claims. It does not activate live proposals, evidence, permissions, author identities or facts. UI shows historical proposal summaries/claims, exact historical quote/span, source declaration and every working-review version, with old author identifiers explicitly unauthenticated. Package model/provider statements are claims, not verified inference. Missing original evidence remains explicit.

Real test chain uses HappyDOM File selection and download callback -> TS -> Node stdio -> Python archive -> temporary SQLite, export/import/list/read/component remount. No external network/model, real browser/native IPC, production deployment or cross-process archive retention is claimed.
