# Independent main-based semantic worksheet extraction acceptance

2026-11-14. Separate native reviewer. No implementation/frozen-file changes, branch switches, commits or remote writes by reviewer.

**8 new independent tests passed; combined130/130 passed, zero skips. All40 source-manifest files match their stated Git source bytes and hashes. Candidate freeze42/42 matches. No blocking extraction defect found.**

```sh
PYTHONPATH=research/semantic_support service/.venv/bin/pytest --import-mode=importlib -q research/semantic_support tests_acceptance/SEMANTIC_BROWSER_EXPORT tests_acceptance/SEMANTIC_MAIN_CANDIDATE
```

## Evidence

- Git merge-base of HEAD and main3aba is3aba; PR56 head254167e is not an ancestor. The assertion remains valid after an ordinary local candidate commit and does not require HEAD to equal main. No97 preview ancestor chain is incorporated.
- Every manifest path is compared with `git show <sourceCommit>:<path>`, not only against the locally recorded hash. Selected files are unchanged source copies; all seven runtime files occur in the manifest.
- AST import inspection confirms each Python runtime module imports only standard-library modules or another selected module.
- A temporary directory receives exactly the seven runtime files, with two historical input snapshots in a separate inputs directory. Runtime invocation uses Python `-I -S -B`, removing site packages and ambient PYTHONPATH and suppressing bytecode writes. Socket creation and create_connection raise immediately. No production module is copied.
- In that isolation, the real restore generator creates the page; actual generated export/import scripts run through the existing Node adapters; downloaded JSON then enters the actual strict CLI HTML exporter. Both digests, literal notes and the unverified/no-auth/no-case-write/no-model statuses survive.
- Altering either worksheet digest fails exit2 without an output file. The generator creates0600 output, refuses a repeated output path and symlink target, and preserves existing bytes.
- Isolated evaluation of retained historical predictions still reports sourceLocatorVerified/modelIdentityVerified/provenanceVerified/semanticSupportVerified/factActivated false and zero verified reviewers.

The isolated script checks supplement, rather than replace, the combined source tests for CSP hashes/escaping, hostile import JSON, duplicate fields, Unicode, cancellation, late reads, repeated actions and unchanged state after failures.

## Limits

The7-file closure requires co-location and documented script-path invocation; this is not a packaged service or production page. Input corpus/prediction byte snapshots are explicit data dependencies. Test tooling needs pytest/Node; the Python runtime does not. Historical Jiangxin9 files describe a prior unverified run, not a model call in this acceptance.

No browser engine was launched or sandbox bypass attempted. Native file chooser/download, actual browser CSP enforcement, layout and platform filename behavior remain unverified. Node adapters do not prove disk-save success. Source hashes/HTML can be edited by a local operator and are not signatures or authenticated source provenance. This slice does not add identity, source PDF retrieval, model transport, Pi, database or production HTTP routes.

No blocker remains within the extraction scope; browser/production/model acceptance is not claimed. Initial reviewer harness assumptions about optional manifest tier metadata and Python bytecode output were corrected without touching candidate sources or weakening provenance/closure checks.
