# W8.5 Basic package intake v1

Profile `MCIS-BASIC-INTAKE-1`. Local single-process investigation-group workflow only.
POST `/api/v1/packages/intakes:preview` JSON `{contentBase64}` validates a complete
MCIS-MCASE 1.0.0 ZIP and returns profile, caseId, title, sourceSha256, byteLength,
counts and warnings. No writes. POST `/api/v1/packages/intakes:commit` requires
identical bytes, sourceSha256 and literal `confirmed:true`; revalidates, imports only
into a NEW case and returns a receipt including importedUtc and replayed.
GET `/api/v1/packages/intakes/{sha256}` is the sole recovery operation after an
unknown write outcome. 404 means no committed receipt, not permission to auto-resend.

Only Investigator/LeadInvestigator. Existing header identity is NOT authentication.
Only case/case.ext, vessels, tracks, environment, registered evidence, custody/audit
and default access policy are supported. Other business content must be empty;
unknown files and fields are rejected, never silently dropped. Original ZIP retained
with SHA-256 receipt. Imported original chains preserved; one local import event added.
No imported policy may expand access. No existing case or blob directory overwritten.
32MiB compressed / 64MiB expanded / 16MiB member / 2048 members; bounded JSON body.
Single-process lock serializes imports; ordinary failure including final DB commit
rolls back SQL and removes only this operation's files. No crash-atomic filesystem/SQL
or multi-worker guarantee. No deployment, LLM analysis, general package compatibility,
or completed professional analysis is implied.

Audit/custody chains support LF line endings only. CRLF and literal Unicode/ASCII
line-separator characters are rejected at preview, rather than changing original lines.
Evidence with replaced-original version history is rejected pending a dedicated design.
JSON and JSONL must be UTF-8 without BOM to keep preview and import semantics identical.
