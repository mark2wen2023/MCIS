# Pi transcript host trial (unmounted, no network or persistence)
Trusted Python constructs `TranscriptHost(db, settings, token, case_id, record_id,
expected_binding_digest)`. Caller credentials never occur in tool arguments.
All reads and model boundary calls reauthorize and compare the initial snapshot.
`begin_model()` / `end_model()` surround every model invocation. Only one model
may be pending. `close()` and a failed source/authority check permanently close
this run. Upper bounds: 4 model calls, 8 tool calls, 120 monotonic seconds.
Tool dispatch: `call(name, args)` returns an isolated JSON-compatible value.
- `read_transcript_excerpt`: `{round: positive integer, field: "Question"|"Answer", start: nonnegative integer, length: 1..4000}`. Offset is Python Unicode code points in the redacted field, NOT original/UTF16 citation coordinates.
- `find_transcript_passages`: `{query: nonempty string <=200 chars}`. Literal search, at most 20 matches, redacted text only, fixed current transcript. Returned locations are redacted Unicode code points.
- `validate_extraction_proposal`: `{content: JSON string <=65536 UTF8 bytes}`. Uses original schema and exact-quote validation. Success is only PendingReview, not fact verification, saved=false. Generic invalid result permits correction, no exception content or hidden source disclosure.
Unknown names/fields/types fail closed; no filesystem/URL/case/session inputs.
`finish(content)` repeats validation and final authority checks, closes the run,
and returns only a pending-review result. No write or formal-fact tools exist.
This callable alone is not a Pi runtime, transport, remote consent UI or persistent audit.

## Official Pi runtime checkpoint
`tools/pi-transcript/runner.mjs` imports pinned official Pi Agent1.5.2 and exposes
only an explicitly selected simulated-provider trial. `dispatch` accepts exact
`{op:model_start}`, `{op:model_end}`, `{op:tool,name,args}`, `{op:final,payload}`
envelopes from trusted runtime. No user or model-provided identity/URL settings.
The Node runtime requires final text to equal a validated candidate; the host
revalidates independently. Real Pi tool execution with fictional model responses
is distinct from actual DeepSeek tool calling, which is not implemented here.

## Opt-in remote extension (separate files; original single-shot API unchanged)
`describe_remote` returns full redacted transcript, fixed system/task prompt,
fixed three tool schemas, official DeepSeek destination/model and a scope digest.
It explicitly discloses that model outputs and real tool results are sent back in
later rounds. A digest is only binding, not proof of user consent: trusted caller
supplies it after explicit user authorization. Unknown/absent approval means no
network. Approval binds session, case/source/policy, prompt and model.
`RemoteTranscriptHost` owns canonical messages. `model_request` accepts only
`{op:'model_request'}`, once between each model_start/end. No caller-supplied
messages, URL, model or credentials. Remote tool envelope adds `callId`, and must
match the next outstanding actual model call name/args/id exactly. Real tool
results are appended by the host. Missing tool results prevent another model
turn. Final payload must equal actual final model content; at least one successful
proposal validation tool and a source read/search must have occurred, and final
content must be the content successfully validated. Failed/unknown network calls
close the run rather than silently retrying.
The transport independently validates message roles, call identifiers, exact
three tool schemas/arguments, size/type/number bounds, finish reason and duplicate
JSON keys. Fixed official HTTPS, TLS verification and managed proxy/CA; no retry,
redirect, arbitrary destination or implicit environment selection.

DeepSeek response compatibility: a tool-call may additionally carry `index`.
When present it must be an integer (not boolean) equal to that call's array
position in0..7. It is stripped before canonical storage/execution; unique `id`
remains the identity. All other unknown tool-call fields remain rejected.
