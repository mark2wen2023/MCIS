# Nonproduction issue-workspace component

`web/src/issueWorkspace/IssueWorkspace.tsx` is a standalone React component, not
mounted in the existing workbench or legacy API. The old role-header identity is
not trusted. No fetch, URL, token, localStorage or sessionStorage is implemented.

Default `<IssueWorkspace/>` is disconnected and disables submission. Explicit
`<IssueWorkspace rehearsal/>` provides a functional fictional-memory rehearsal:
initial judgment -> verification -> changed judgment -> new verification ->
discussion, retaining the prior records. Refreshing/unmounting loses this memory;
it never claims a server/database write. Rehearsal accepts only the fixed fictional
case, and cannot be substituted for backend/LLM acceptance.

A future trusted host may supply a `JournalPort` and an opaque `contextKey`, plus
caseId and optionally issueId. The port has only business save/read callbacks,
not a credential or arbitrary-URL field. Port presence means only 'trial interface
provided', never successful authentication. Host must change contextKey on session
or authority-context change and use the server's actual auth; this component does
not authenticate, provision sessions, or establish a safe browser-host bridge.
No such bridge is delivered here. Optional existing issueId must be read before
editing; read failure does not authorize replacing/recreating a record.

Commands contain case/issue/operation UUID, expected revision and entry snapshot.
The UI freezes the exact command on uncertain saves and retries the same operation.
It does not fabricate a new operation on error. New judgment resets discussion
eligibility until that newest judgment receives verification. All verification
outcomes and discussions are submitted working opinions, not confirmed facts,
approval, collective consent or assignment of responsibility.

Responses must match scope, event sequence, unreviewed status and workflow. Save
response must include the actual submitted entry and preserve known prefix.
Refresh may not reduce revision or replace known history. After a failed refresh,
history is hidden and editing blocked, while a private in-memory baseline permits
integrity comparison on retry. Context switch, disconnect and unmount invalidate
late responses. They cannot undo a write already committed by a future host.
No exception message, credential or actor supplied by a response is shown.

Scope limits: one card per component, no case/card discovery menu, source upload,
evidence linking, archive controls, production identity, real LLM or persistent
browser recovery. Existing source IDs display as historical references, not current
source verification. These omissions must remain visible in delivery reports.

## Acceptance

Product-only strict TypeScript with ES2022, bundler module resolution, React JSX.
HappyDOM + actual React exercises forms and controlled async ports. This is simulated
DOM, not real Chromium clicks/layout/accessibility/CSP or a backend transport test.
The known cloud sandbox browser limitation was not bypassed.

Use installed trusted esbuild/TypeScript/React/HappyDOM. Bundle test `.tsx` in
`web/tests` for Node ESM with automatic JSX and a createRequire banner, then run.
`MCIS_HAPPY_DOM_PATH` optionally selects an installed HappyDOM entry file. Generated
bundles and node_modules are local test artifacts, not repository deliverables.
