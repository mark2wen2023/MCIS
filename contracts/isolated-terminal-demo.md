# Runnable isolated terminal demo (fictional only)

Entry: python -m mcis_service.identity.demo --core-command <trusted-W2-command>
Interactive options:1(single45°),2(single50°),both(compare),q(exit).
Automated reproducible run adds --choice both --json. JSON requires explicit choice,
so scripts cannot accidentally wait on interactive input. No session argument,
login, browser, listener, network URL, real-case path, deployment or installation.

A fresh TemporaryDirectory contains explicit SQLite and blob paths; ambient
MCIS_DB_URL/MCIS_DATA_DIR do not select user storage. DB schema then fixed fictional
case/two CSVs are created through existing case/intake functions as trusted host
calls, not legacy HTTP app/role headers. No create_app or uvicorn server. Host creates
five-minute local session and grants only this fictional case. Token stays in memory;
client does authorized catalog -> mapping selection -> pinned save -> read via
ASGI HTTPX. No returned object/CLI output contains token or caller identity.

The supplied core command is a trusted host executable configuration, not downloaded
software or untrusted form input. Actual core needed for compute. q requires no core
execution. No mock result fallback on missing/failing core; CLI exits2 with sanitized
message. EOF/interrupt returns failure rather than claims completion. Unexpected
internal paths/stdout/stderr are not printed by the demo.

Output explicitly fictional/unreviewed/not_assessed; source relationship not verified,
core implementation not attested. Both fictional headings produce delta5 degrees
with current W2; clocks remain uncalibrated. Not real case, semantic validity,
independent corroboration, LLM or accident conclusion. Single source zero conflicts
is not proof of consistency. Stored result exists only in the temporary run, then is
removed: this is not a durable investigation archive. Optional stdout summary can
be redirected by host but is neither an approval nor import credential.

Engine disposed and temporary directory removed on ordinary success, cancel and
exceptions; cleanup flag appears only after successful context cleanup. Abrupt kill,
power loss and OS cleanup failure are not crash-cleanup guarantees. Debuggers or
host logging can inspect secrets; memory-only is not protection from trusted host.

Actual subprocess/interactive and in-process socket.bind refusal tests validate local
terminal behavior. No browser, IdP, real network deployment, protected intake API or
production account administration is introduced. Existing app and default closed
protected entry unchanged. No merge or deployment.
