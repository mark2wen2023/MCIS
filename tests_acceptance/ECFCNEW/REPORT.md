# Independent ECFC new-slice acceptance

## Final disposition

**NOT fully accepted / NOT ready to merge. Keep the change in draft, unmerged state until supported independent real-browser verification completes. No deployment.**

| Verification layer | Final result |
| --- | --- |
| Revised-protocol backend / SQLite / real C# core | **30 passed in 11.48s**; all 13 implementation SHA256 entries matched before and after |
| Actual loopback TCP HTTP / real C# core / temporary SQLite | **10 checks passed**; the same 13 implementation hashes remained unchanged |
| Independent real Chromium browser | **BLOCKED; 0 UI assertions completed** |

The final backend freeze is `logs/ECFCNEW-backend-v2-hashes-frozen.txt`. The final protocol requires exact `acknowledgeArchiveLimitation: true` on save. Backend acceptance covers only the bounded synthetic scope below, not integrated UI acceptance, whole-W11 completion or ECFC backup support.

## Scope and provenance

This is a new implementation based on `3aba2bf03e393909c611489ae573a887087637ac`. No lost W11 code, old test outcomes or reported 933-count acceptance are reused. The reviewer changed only this acceptance directory and `DEFECTS/ECFCNEW.md`, not implementation. All runtime data is synthetic with `seed_demo=False`; tests do not ingest reports or contact external services.

The five original C# source blobs independently match the baseline tree. CLI, HTTP, SQLite and UI are distinct verification layers. A drawing diagnostic is not evidence, causation, legal compliance or expert approval.

## Final backend coverage

- Original red tests reproduced five malformed/future saved-document disclosure variants and a valid Unicode graph falsely rejected by a hidden core-output limit. The implementation owner repaired both; original assertions remain.
- Current, receipt and audit foreign-case/future/status/digest pollution and coherent current digest without matching audit are rejected.
- Real C# presumption and edge-style derivation; professional prerequisite diagnostics do not block structurally valid draft persistence.
- Real second-connection source/case/policy mutation during core computation refuses the write. Concurrent distinct request IDs with the same CAS expectation produce one success and one HTTP 409.
- Actual committed save followed by deliberately failed reply produces an unknown response; retrying the same request does not duplicate graph/audit/receipt.
- Role and operator binding, protected historical source access, append-only audit/receipt and audit/receipt/commit SQL-fault rollback.
- New table state blocks the whole affected case export, including orphaned history, without blocking another case. This is refusal, **not ECFC backup support**.
- Unknown/partial/malformed policy is denied.
- Missing, false, integer, string and null archive acknowledgements reject without any new graph, audit or receipt.

The separate actual TCP run checked context/archive declaration, real CLI zero-write preview, acknowledgement enforcement, save/reopen/idempotent receipt, CAS conflict, whole-case export refusal, default-role denial and audit binding. Final database counts were 1 current graph, 1 audit and 1 receipt. HTTP success is not a substitute for browser flow acceptance.

## Browser blocker

The first launcher used the service virtual environment, which lacked Playwright. Using the already-installed Python Playwright package reached Chromium while the service continued to use its project virtual environment. Default sandbox execution failed before page creation. The same execution tool's normal approval path was then requested for this new synthetic test and execution was admitted, but Chromium still failed:

```text
process_singleton_posix: socket() failed: Operation not permitted
```

No UI assertion executed. Owned loopback child services were terminated by the runner's cleanup. No alternate tool, channel or launch-flag workaround was attempted; browser attempts stopped. This is a runtime capability failure, not another approval rejection and not evidence of a product UI defect. Raw runtime logs are retained locally and are not included in this delivery; the material result and failure text are recorded here without requiring access to them.

`browser_real.py` and `server.py` prepare independently owned synthetic services with temporary SQLite and loopback sockets. The browser script is an uncompleted acceptance procedure, not evidence that its assertions passed.

## Reproduction

Run from the repository root with the project service virtual environment prepared. Configure `MCIS_DOTNET` to the installed dotnet executable and `DOTNET_CLI_HOME` / `NUGET_PACKAGES` to the intended writable runtime/cache directories. The commands use those existing environment variables; no reviewer-specific paths are required.

```bash
: "${MCIS_DOTNET:?Set the dotnet executable}"
: "${DOTNET_CLI_HOME:?Set the writable dotnet home}"
: "${NUGET_PACKAGES:?Set the NuGet cache directory}"
export MCIS_DOTNET DOTNET_CLI_HOME NUGET_PACKAGES
sha256sum -c logs/ECFCNEW-backend-v2-hashes-frozen.txt
PYTHONPATH=service:tests_acceptance/ECFCNEW \
  service/.venv/bin/pytest -q tests_acceptance/ECFCNEW -p no:cacheprovider
python tests_acceptance/ECFCNEW/http_real.py
sha256sum -c logs/ECFCNEW-backend-v2-hashes-frozen.txt
```

The HTTP runner owns and cleans up its temporary service and database. Browser reproduction additionally needs the project's frontend dependencies and a supported Chromium/Playwright execution environment; its execution did not complete in this review environment.

## Historical result, superseded

The earlier freeze (`logs/ECFCNEW-backend-hashes-frozen.txt`) produced **25 passed in 12.80s**, with its 13 hashes checked before/after. That run preceded mandatory archive acknowledgement and is retained only as historical evidence. It is not the final revised-protocol result and is not substituted for the 30-test rerun above.

## Limits

Not full-repository CI, Unity, professional agreement, production authentication, unrestricted archive/migration, non-SQLite concurrency or crash/power-loss proof. Audit checks within the returned window are not full-history authenticity. Deliberate in-database corruption fixtures are boundary tests, not evidence of a real user incident. The linked Sklet methodology was read through repository thesis/core documentation, not independently certified against its publisher.
