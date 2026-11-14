# Explicit public UI broker (test only)

`tools/pi-transcript/public-ui-host.py` is an explicitly started stdio test broker,
not an HTTP service or production session. `--approved-public-ui` reads one key
JSON line through stdin; `--fixture` never reads a key and replaces provider
transport with deterministic public-excerpt responses. No silent fallback.
Ready reports mode/transportMocked/provider selection, inferencePerformed=false,
fixed report/source hash and generated fixed review/archive scopes. It never
contains a session token, API key or complete disclosure prompt.

Protocol:
1. Original bounded Pi envelopes only. UI channels are unavailable beforehand.
2. Successful server-owned reference completion is saved once through the same
   Pi working host. Final response adds workingReady with proposal ID/counts,
   saved=true, factActivated=false and reviewOrigin=scripted_test.
3. Explicit `{channel:'review'|'archive',request:...}` messages use existing
   fixed-scope RPCs. Review generation is disabled; reviewOrigin is fixed in the
   trusted host constructor and not an accepted RPC argument. Archive import is
   limited to the exact package most recently exported by this same broker.
4. `{channel:'close'}` closes hosts/database and removes normal temporary storage;
   cleanup confirmation is emitted only afterward. EOF/exception is not successful
   shutdown. Forced termination may leave temporary files; no automatic retry.

Limits:96 commands,32 Pi-phase commands,12MiB per line/output,64MiB total input,
300-second process interaction deadline/30-second idle reads, existing4 model,
8 tool and120-second Pi budget. Existing source/session/authorization checks
remain authoritative. Models receive only the three original read/validation
tools; they never receive review/archive RPC tools.

Initial local verification:3/3 tests (two trusted-origin/RPC checks and actual
fixture subprocess → Pi protocol → SQLite save → scripted review → v2 export,
import/read inert history → clean close). Mocked transport is not real inference.
No real provider invocation, production UI, deployment, merge or publication
was performed by the broker implementer. Independent review and Node/React
integration are coordinated separately.
