# W7: registered agreed deadline persists after reopening SQLite

Fixed source: `94d5e38c926fda232bb987b60fa9145e4bcf01a7`. The test adds no service
change and does not require the separate proposed front-end change. It supplies
the same request shape as the latter after confirmation, for the hand-made
case `SYN-W7-AGREED-001`. It supplements existing default-30-day and closure
lifecycle tests; only this new positive business test is intended here.

Use an existing dependency environment with FastAPI, Pydantic 2, SQLAlchemy,
jsonschema, and referencing as installed for MCIS. Materialize only the 32
paths listed in the manifest, not any case or seed data. From the checked-out
candidate containing these test files, with the fixed source commit available
in the same Git repository:

```sh
set -eu
base=94d5e38c926fda232bb987b60fa9145e4bcf01a7
testdir="$PWD/tests_acceptance/W7"
src=$(mktemp -d)
trap 'rm -rf -- "$src"' EXIT
root="$PWD"
awk '{print $2}' "$testdir/agreed_deadline_sources.sha1" |
  xargs git -C "$root" --literal-pathspecs archive --output="$src/closure.tar" "$base" --
mkdir "$src/source"
tar -xf "$src/closure.tar" -C "$src/source"
"$root/service/.venv/bin/python" -I -B "$testdir/check_agreed_deadline_reopen.py" --source-root "$src/source"
```

The script checks exact fixed Git blob bytes before loading the narrow service
modules. It uses the registered POST and GET handlers and real request context
parser, production default-policy checks, JSON-schema contracts, and the
production SQLite ORM session, round storage and audit implementation. The
fixture creates only the four relevant tables and one synthetic case using
real model definitions; it does **not** run app startup, global schema
initialization, or any seed code. There is no HTTP/ASGI invocation. Both time
sources are fixed during the write, and the same fresh SQLite file is reopened
with a second engine and fresh request context. Expected: opened
`2026-02-01T08:00:00Z`, 45 days / agreed flag true, deadline
`2026-03-18T08:00:00Z`, 43 remaining two synthetic days later, one persisted
round and one matching audit event with a valid chain.

The audit distinguishes an agreed-deadline declaration from the default
branch, but neither the audit wording nor this test proves mutual agreement,
dispatch or delivery to a party. No report is created/finalized/archived; no
roles or policy are changed. This does not verify browser interaction,
transport/security behavior, production authentication, or crash recovery.
