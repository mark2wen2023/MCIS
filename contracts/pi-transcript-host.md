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
