# W19 preview stop-wait

Adds explicit stop waiting to the actual product preview. Aborts local transport and invalidates the request generation; late success/error/finally cannot overwrite a newer result or unlock a newer pending request. Does not claim server cancellation. No save/publication or API changes; template provider remains.

19 lifecycle + 10 prior independent + 16 stop-wait tests pass; independent acceptance added 10 probes, passed with implementation hashes unchanged. Browser-target bundle passed. Happy DOM and controlled fetch only, not real browser/network/backend, complete application or LLM acceptance. Native development and independent review subtasks; not Codex app tasks. No merge/deployment.

Run from tests_acceptance/w19-react-lifecycle using existing dependencies: `npx esbuild cancel.tsx --bundle --packages=external --platform=node --format=esm --jsx=automatic --outfile=.cancel.mjs && node .cancel.mjs`; repeat for independent-cancel.tsx. Existing lifecycle and probe tests also pass.
