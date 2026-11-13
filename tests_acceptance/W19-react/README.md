# W19 actual React DOM lifecycle checks

Acceptance target: PR54 d76db98a9925168d9ab9e233008376af52489e99. No implementation change.

React 19.3.1 mounts and unmounts the real SuggestionPreview using react-dom/client, Happy DOM 21.0.4 and controlled deferred fetch. This is not static rendering or a mocked component. The transport deliberately ignores cancellation so late success/error paths execute. 19 assertions cover pending/double click, source change cancellation, late success and failure, A-B-A acknowledgment reset, explicit apply, identity changes with parent render, and unmount.

This is NOT a real browser, real network/backend, full app, visual, production authentication or LLM acceptance. It does not replace the remaining browser gate. No provider or production code is altered.

Run from this directory with Node 24:
```
npm ci --ignore-scripts --no-audit --no-fund
npm test
```

Use a writable npm cache if required. No server is started. Source inputs are synthetic. Install only test dependencies; do not alter web runtime dependencies.

Independent rerun: 19 original assertions plus 10 additional lifecycle probes passed. No implementation changes; source SHA256 94c6eb23e155810a84ff6d096b05f12129a1b82ab4a806f675f86af37f88fca5. Native development and independent acceptance subtasks, not a Codex application task.
