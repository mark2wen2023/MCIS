# Independent offline blind-run safety review

Scope: isolated research runner only. No real provider request, production deployment, commit, or expert certification was performed by this reviewer.

## Result

No blocking safety issue found in the frozen files below. The implementation satisfies the safety prerequisites for **one explicitly authorized real run** on the fixed public-report corpus. This is not an assertion that the provider/model is reachable or that its judgments are correct. A failed/unknown run must not be automatically repeated.

## Verified boundaries

- Model input uses opaque sequential case IDs; original semantically suggestive IDs, suggested labels, corpus rationales, reviewer records, and fixture-predictions are absent from captured provider histories. Original IDs are mapped back only by the host after completion. Task-necessary evidence, claims and citations remain visible.
- Host owns canonical message history, call IDs, tools and fixed official DeepSeek endpoint/model. Call arguments, order and IDs are checked; callers cannot supply prompts, URLs or arbitrary tools. Validation feedback is schema/coverage-only, not an answer oracle.
- Manifest, projected cases and mapping are pinned and rechecked, including after provider return. Failed validation clears a previous accepted candidate. Completion requires exact marker and the host's latest valid prediction set, read performed, no pending tools and canonical terminal state.
- Real mode requires explicit `--approved-blind`; fixture is a separate explicit mode. Secret arrives via non-TTY stdin into Python memory; Node argv/environment/ready/messages/receipt receive no key. Node environment is PATH-only. Raw provider errors and reasoning are not printed or persisted. Python error output is fixed metadata only.
- Before transport invocation, Python returns a request-attempt event and requires matching acknowledgement. Node writes an exclusive 0600 metadata-only receipt and fsyncs before acknowledgement; persistence failure stops before provider dispatch. In-flight failure closes host, clears credential and is unknown; no retry loop exists.
- 4 model calls, 8 tool calls, 180-second host deadline, bounded JSON/line/total bytes and 96 bridge commands. Redirects disabled. Model content/tool inputs bounded and strict parsed; duplicate JSON keys and nonfinite values rejected in trusted host.
- Successful output follows close acknowledgement, matching Node totals and child exit 0 within deadline. Receipt protocol completion is not a claim of source accuracy or expert agreement. Hard kill/container loss can leave a partial receipt, not proof of no request.

## Offline tests

`test_blind_independent.py`: **19 passed**. Includes complete captured provider history leakage checks using injected offline transport; sentinel corpus metadata projection; canonical call tampering; success-then-invalid candidate invalidation; post-provider case/mapping/manifest mutation; duplicate/deep/nonfinite JSON; prediction coverage/size/authority fields; expired buffered input; tool budget; official Pi fixture subprocess with receipt permissions, cleanup sequence and exclusive path; invalid credential generic output.

Independent + primary Python suite: **32 passed, zero skipped**, 1.12 seconds.

Node primary scripts rerun: **2 files passed**, comprising 6 runner scenarios plus CLI coordinator receipt ordering/cleanup check. These cover persistence failure preventing ACK, unsupported tool/final marker, model budget, hung bridge deadline and actual official Pi fixture flow.

All tests use fixture/injected transports, **zero real API requests**. The real Pi fixture reaches 3 model cycles, 2 tool calls and 11 prediction records; this demonstrates protocol execution, not real model ability. No browser UI or CI is claimed.

## Frozen hashes

- blind_host.py: e70a7761a77e755eb0fdf0127999ad234836a0495de5ab39f4ef58986fa8e20a
- blind-cli.mjs: 37198e4a9664bc8b2446c14f19183b58469528c6b46dffe66a50c820ae5fa6b4
- blind-runner.mjs: bc632a728389a7ac7b64761a15b7d3db6247cde269d700d9f61f707ab896f412
