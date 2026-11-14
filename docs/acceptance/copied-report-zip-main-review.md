# PR64 current-main independent security review

Main4585016172094193b93ed200f1406c630e9fb8ab. PR64 head5d10b67db47e55b6352b559ec1d00ae61ede99c7 targets research/sk-t01-preview-20261113 (254167e), not main. Do not merge original branch wholesale: it carries a different ancestry. Main and this branch diverge at3aba2bf.

Applied exact three production-file PR64 hunks to isolated current-main service export, preserving main router changes (intake hunk offset -2 only). Tests copied from candidate; source dependencies came from pinned main. Global fixtures/production policy not relaxed. Original PR64 untouched.

Baseline main two report-copy regression checks genuinely failed: both download routes returned200 where403 required. Restored candidate and reran:15 candidate regression +30 independently authored access/transaction checks =45 passed in8.09s. Prior candidate run45 passed in8.34s. Covers generated DOCX report ZIP explicit registration, both live routes, every12 permission category, field rules, policy revocation, no decompression, existing non-ZIP behavior, separate SQLite connection lock refusal, error rollback/no Access and whole ZIP archive restore.

Related larger local suite:238 passed,1.NET SDK skip,4 PDF renderer failures. Export lacked pinned main NotoSansSC font. Existing local font Git blob is different and was not substituted. An accidental unchanged retry was interrupted; do not count it. Thus PDF/whole report rendering remains unverified here, not attributed to candidate code. No SDK installed.

This guard intentionally restricts all detected ZIP containers including DOCX. Not general DLP; text/PDF/transformed unrecognized copies remain outside it. Role headers are synthetic, not real SSO. No real browser/LLM, CI/full-service acceptance, deployment or merge. A minimal current-main integration is recommended for further independent review, not original-branch wholesale integration.
