# W19 source preview session reset

Based on PR54 de72970. Source values (including kind) and current identity define the React child instance. A changed committed input unmounts the old session, aborts its request and sets its existing active guard false; its late success/error cannot update the new instance. Result, error, pending flag and acknowledgment are reset, including A→B→A edits. Mere property insertion order changes do not remount. No new API, authentication or persistence behavior.

14 key/wrapper checks, existing 16 source-review and 9 independent source-binding checks plus W19.2 regression, isolated TypeScript and browser-target bundle pass. These checks are not browser interactions or a full app build. React commit/effect and network race behavior still requires browser end-to-end validation; no claim of production identity or real LLM validation. template-stub-v1 remains.

Native development subtask plus independent acceptance, not an independent Codex application task. No merge or deployment.

Independent review reran the listed checks and added 10 boundary probes (field changes, whitespace, Unicode/NUL, identity separation and clone stability); passed. No actual React mount/unmount or late-network response test was executed. Identity changes still depend on parent re-render, while request/apply identity guards remain. The session behavior is supported by code review and key tests, not claimed browser race acceptance.
