# Persistent extraction working-review UI chain

An independent default-disconnected React component and strict trusted-callback port now support saved proposal list/open, immutable source quotations, per-item human opinion history, and appending new working revisions. The trusted Python adapter exposes only fixed-scope generate/list/read/review methods, never credentials, provider configuration, arbitrary paths or old role headers. Fixture mode is explicitly pinned for the actual synthetic integration.

Verified locally on final frozen products:
- **462 Python related regression tests passed**, zero skipped, 341.59 seconds; one existing Starlette/httpx warning.
- Independent backend review + primary RPC rerun: **41/41 passed** (24 independent and 17 primary). One additional independent post-commit failure test was added after the larger collection began, so this rerun is reported separately.
- **24 primary UI checks**, **9 independently authored port checks**, and strict TypeScript passed.
- Actual React/HappyDOM -> TS -> Node stdio -> Python -> same-database authority -> temporary SQLite passed: two fictional proposals generated/saved, individually reviewed, UI remounted, directory listed and original reopened, revision two appended with revision one and original quotations retained.

Unknown writes preserve the exact operation for retry. Explicit stop-retry/read is not cancellation or evidence of failure. Tests cover response failure after an actual committed write, await cancellation whose worker still commits, and original-operation recovery without duplicate stored effects. Dirty decisions/notes prevent accidental navigation; explicit discard is available. Late old-context responses, rewritten history, revision rollback, altered citations and fixture-to-local spoofing are rejected.

This is a tested isolated component/host chain, not a mounted production workbench, browser/native IPC, real-model acceptance, CI result or deployment. Fictional fixture database is deleted on normal process exit: UI remount while host remains running is demonstrated, not fixture restart retention. Underlying persistent-host database reopening was tested in the prior slice. Saved review is only a human working record, not facts, official interview approval, liability conclusions or training-data approval. Original binding changes continue to deny old-content access; case/archive integration remains outstanding.
