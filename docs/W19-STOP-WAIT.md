# W19 preview stop-wait

Adds explicit stop waiting to the actual product preview. Aborts local transport and invalidates the request generation; late success/error/finally cannot overwrite a newer result or unlock a newer pending request. Does not claim server cancellation. No save/publication or API changes; template provider remains.

19 lifecycle + 10 prior independent + 16 stop-wait tests pass; independent acceptance added 10 probes, passed with implementation hashes unchanged. Browser-target bundle passed. Happy DOM and controlled fetch only, not real browser/network/backend, complete application or LLM acceptance. Native development and independent review subtasks; not Codex app tasks. No merge/deployment.

Run from the repository root with Node 24:

```sh
cd tests_acceptance/W19-react
npm ci --ignore-scripts --no-audit --no-fund
npm test
```

`npm test` runs the lifecycle and cancellation suites. For cancellation alone, use `npm run test:cancel` from that same directory. The cancellation source files remain in the sibling `../w19-react-lifecycle` directory; the runner writes bundled modules into `W19-react` so external dependencies resolve from its locked local installation. No global dependencies or web runtime install are required. The previous instruction to run from the sibling directory was incorrect.

This runner repair does not change production code or establish real browser/backend acceptance.

Runner repair validation (2026-11-13): development and independent review each used a fresh directory and writable isolated npm cache with Node v24.22.1. `npm ci --ignore-scripts --no-audit --no-fund` followed by default `npm test` passed all four suites: 19 lifecycle, 10 lifecycle probes, 16 cancellation and 10 cancellation probes. Production sources were unchanged. This is scoped reproducibility evidence, not CI or full project acceptance.
