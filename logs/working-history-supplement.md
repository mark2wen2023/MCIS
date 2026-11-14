# Working-review history supplemental archive

Implemented explicit trusted-host export/restore/read/list for immutable AI proposals, source citations/declarations and every human working-review revision. Export rechecks live source/record/policy bindings. Import and historical reading each require a separate, explicitly provisioned ArchiveGrant plus current same-database case/session/content/testimony permissions. Neither permission implies the other.

Same case ID may import historical material from an older case incarnation into the current target incarnation/epoch. The imported partition is inert and append-only: no live proposals, reviews, sources, interviews, users, sessions, grants, or facts are activated. Imported authors, source declarations and model labels are historical claims, not authenticated identities or present-source attestations. A recalculated checksum does not make a forged history authentic.

The supplemental package intentionally excludes complete interviews, original media/bytes and identities/permissions. It is NOT a complete case backup or source recovery mechanism, and has no production web/HTTP mount in this slice. Existing `.mcase` format is unchanged.

Independent review found a terminal authorization ordering defect: session expiry during the final epoch read could occur after the prior authorization check. Import/read/list now perform terminal policy/grant/session rechecks; export orders final metadata before authorization. Reproduction tests and export's analogous boundary now pass.

Final local verification:
- **508 related Python regression tests passed**, zero skipped, 310.43 seconds.
- **54 final archive tests passed**, zero skipped, 56.13 seconds: 15 implementer, 33 independent catalog/security, 6 independent transaction/concurrency checks. Additional tests were added after the larger collection began, so these runs are reported separately.
- Real concurrent same-package imports produce one new row and one replay; injected final failure rolls back; SQL UPDATE/DELETE are denied; reopened database reads retained history; empty target restore does not reconstruct live data/authority.
- Strict JSON/fields, duplicate keys, non-finite/deep/oversized input, citations/spans, ordered review revisions, source declarations, author claims, revoked permission and target epoch/incarnation boundaries covered.

One existing Starlette/httpx deprecation warning per run. Synthetic data only; no real LLM/API, CI, new browser acceptance, merge or deployment claimed. Implementation SHA256: `38ddad108639cf6724339c3c38ef436cd6056745b8ae0154d6f9ed84a4452f14`.
