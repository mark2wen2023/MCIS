# Registered preview real-network transport acceptance

This is **not browser or visual acceptance**. It uses the actual frontend `registeredBody`, `intakeRequest`, and `registeredResult` code in Node. The only fetch adapter resolves relative URLs against a dynamic `http://127.0.0.1:<port>` supplied by the runner; native fetch supplies every response. No response fixtures or core doubles are used.

The Python runner creates a disposable seeded SQLite/data directory, starts real uvicorn on a dynamic loopback port and the existing Vite dev proxy on a dynamic free loopback port in the same process tree. It requires installed service dependencies, existing web dependencies (Vite/esbuild), Node with native fetch, and an actually compiled compatible W2 wrapper. It fails rather than falling back to a fake core. The runner passes `MCIS_ACCEPTANCE_WEB_URL` to Node, which requires HTTP on 127.0.0.1 with an explicit port. Vite strictPort fails if another process claims the selected port. No external service or production data is used; the runner terminates its services and removes generated bundle/data.

Run from repository root:

```bash
PYTHONPATH=service \
MCIS_ACCEPTANCE_CORE=/absolute/path/to/actual/core-wrapper.sh \
MCIS_DOTNET=/absolute/path/to/dotnet \
/path/to/service/venv/bin/python web/tests/run-registered-network.py
```

Verified in the cloud environment:
- Four real requests preview/commit two fictional CSV originals (heading 45/50, shared timestamp).
- One real registered preview request traverses Vite/FastAPI/actual W2; frontend parser accepts the 5-degree conflict and `persisted:false`, `observationApproval:not_assessed`.
- One real request using the existing AgentService header identity receives 403.
- All dispatched requests supply fetch `cache:no-store`. This observes request configuration, **not browser cache behavior or a server Cache-Control guarantee**.
- A pre-aborted request rejects with AbortError and dispatches no fetch. This does **not** verify cancellation of already-running core computation.

Final run exited 0 with six real requests. An initial test attempted nonexistent role Viewer and received expected service BAD_ROLE/400; the final test uses the real AgentService role to exercise authorization denial. Header identity remains a development mechanism, not production authentication. No browser, rendering, clicking, cross-tab behavior, real evidence, LLM, or persistent source certification is validated here.
