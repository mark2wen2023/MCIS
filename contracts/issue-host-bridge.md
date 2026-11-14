# Issue host bridge trial

## Implemented path

React IssueWorkspace -> createIssueHostPort -> host-owned business-message callback
-> Python IssueHostClient -> fixed in-process ASGITransport -> protected issue API
-> SQLite journal. The callback is a **host transport contract**, not browser login,
public HTTP proxy, or a delivered browser extension/native-message integration.

IssueHostClient construction requires trusted host DB/settings/current session and
case selection. It pins case incarnation and epoch, checks actual authority before
and after requests, uses no arbitrary URL or environment proxy, and never sends
its session token in RPC responses. Every issue API still performs its normal
membership/content/IssueGrant checks. Close invalidates later response release;
already committed writes cannot be undone by closing the client.

RPC request version is `mcis-issue-host-trial-v1`. Context UUID is correlation, not
an authentication secret or permission grant. Request UUID, action, case, issue,
operation/revision and Entry are strictly validated. Fixed callbacks expose only
save/read. Unknown top-level/entry keys and non-scalar entry values are rejected by
the TS adapter before transport; Python independently rejects invalid schema.
Scope and input snapshots are copied before awaiting; response correlation, scope,
unreviewed status and actual submitted event must match. Returned projection strips
unneeded identity/source metadata. Errors are fixed generic strings, not exception
messages containing credentials or arbitrary backend details.

A save with an uncertain response must retain the same operation and content;
IssueWorkspace already does so. This bridge does not create replacement operations.

## Runnable fictional stdio fixture

`python -m mcis_service.investigation.fixture_host` accepts no arguments. It creates
its own temporary SQLite, fictional case and sources, locally issued session and
explicit issue grant, then prints a noncredential ready scope. It ignores real-case
configuration by supplying explicit fresh settings. It opens no listener and never
mounts the legacy app. stdin lines carry bounded RPC JSON; stdout contains protocol
only; stderr uses fixed errors.

Limits:64KiB input line,100 messages,30-second idle/read deadline,300-second run
budget,8MiB response. Duplicate keys, nonfinite JSON and overlong lines terminate
without interpreting them. EOF closes transport/database and removes only its own
temporary directory. Forced process kill/power loss cleanup is not guaranteed.
This fixed fixture is not a real-account provisioning tool and cannot take a user's
DB path, credential, arbitrary core command or external URL.

## Verification boundaries

The integration test drives actual React forms in HappyDOM and sends their commands
through the actual TS adapter and a Python stdio child. It creates, appends and
re-reads five records through the real protected API and real temporary SQLite.
This is stronger than a mocked UI response, but **not a real browser render, network
server, browser-to-native IPC security test, durable user database or production
login**. The fixture's records are deleted on normal process exit. No LLM runs.

Trusted dependencies: service Python environment, React, HappyDOM and esbuild.
Tests use `MCIS_HOST_PYTHON`, `MCIS_HOST_SERVICE` and optionally
`MCIS_HAPPY_DOM_PATH` to locate installed code. These are test-runner paths, never
browser form fields. Generated bundles and node_modules are not committed.

Remaining work: choose and authenticate a real browser-host transport, add secure
session lifecycle/login, mount actual workbench navigation and validate in a real
browser. No cloud tunnel, disabled Chromium sandbox, deployment or merge is added.
