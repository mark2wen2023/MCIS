# Media candidate: three direct seed imports deferred

Base/old counterexample: d9662368aa88236afa92df8ed010f79c30ee5dfc on candidate/media-demo-lazy-factory. Known equivalent source: fix/instance-source-read-policy at 6d5069b9d320dcaddab28b95f8ed265bfc567b67. No policy branch merge.

Only product change: move main.py's three direct seed imports into the existing `if settings.seed_demo:` before its existing session. Import order remains haili5 → lily_mary → yangze22; call order remains lily_mary → haili5 → yangze22, with unchanged session and blob_dir arguments. Default seed_demo, settings construction, DB initialization, all routes, launcher and prepare remain unchanged. False suppresses only these direct imports; normal truthiness condition is unchanged. Import failures are not caught or replaced with missing data. Incidental module-level seed aliases are now local to create_app, matching the known protection; no claim of compatibility for external patching of those aliases.

Development command:

`python tests_acceptance/media-demo-seed-imports/check.py`

Passed full-source AST equivalence to the old AST with exactly those three import nodes relocated, plus equality of the seed conditional to the fixed known-policy implementation. Entire main AST is parsed, never executed. The only executed extraction is a synthetic function containing the three selected imports plus seed conditional, with a closed handmade importer, settings object, callbacks and context manager. Disabled: old 3 fake import events, new 0. Enabled: identical import/create-session/callback order, object arguments and context exit. No actual Settings, create_app, ORM, DB, real dependencies or seed bodies read/imported. Fixed local Git objects required; no automatic fetch. No existing paused tests run.

Initial worktree preparation used an unsupported `sparse-checkout add --no-cone` option, leaving main absent; that attempt stopped with FileNotFound before checks. Re-running the ordinary add with the worktree's existing non-cone mode exposed only the explicit main source path; the above check then passed. No permission refusal or workaround occurred.

This eliminates three top-level dependency edges, not all transitive imports or request-time source reads. Default seed_demo is still True. Existing routes may still import/access materials by other paths. The factory's explicit real invocation still creates application/database/directories; it remains paused. No real startup, isolation, permission, HTTP, Save, archival/recovery, browser, model or media acceptance. This limited development result awaits independent review; do not merge or deploy.
