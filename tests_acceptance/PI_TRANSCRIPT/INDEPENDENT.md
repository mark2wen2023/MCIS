# Pi transcript slice: independent review (2026-11-14)

Scope: real official Pi 1.5.2 runtime with explicitly simulated model, read-only Python trusted-host tools, fixed fictional temporary SQLite integration. No real LLM/API call was made by this reviewer; no production browser, persistent audit or fact approval is claimed.

## Finding and correction

Initial external AbortSignal only called agent.abort(), leaving an uncooperative provider/host pending until the deadline. Independent reproduction: abort at 10 ms, return MCIS_TIMEOUT at 152 ms for a 150 ms deadline (default deadline could be 120 seconds). Implementer changed external abort to reject the shared cancellation promise immediately. Independent hung-provider and hung-host cases now reject promptly. This prevents waiting/result delivery; it does not establish that an arbitrary uncooperative injected implementation has physically stopped executing.

## Final reruns

- Node primary 8 + independent 10: **18/18**, zero skips, 0.38 s. Real Pi agent loop; simulated provider only. Covers immediate cancellation, pre-aborted no actions, candidate modification after validation, failed validation, maximum host tool executions, unknown tools, oversized output, closed remote modes, invalid deadlines, model budget and source revocation.
- Python primary 29 + independent 10: **39/39**, zero skips, 24.02 s. Covers exact source/citation checks, no writes, strict protocol and numeric types, budgets/state closure, source mutation during tools, and revocation after candidate validation before final return. One pre-existing FastAPI/Starlette httpx deprecation warning.
- Independent actual Node Pi -> stdio -> Python -> temporary SQLite rerun: 3 model turns, 2 executed tools, one PendingReview proposal, saved=false. Observed tool_execution_start/end for passage search and validation. Fictional source and provider, not real inference or business accuracy evidence.
- Final publication path is tools/pi-transcript/ (no extra runtime level); ../../service in integration resolves repository service. Isolated local review uses explicit MCIS_TEST_SERVICE/MCIS_TEST_PYTHON overrides; fixture child environment excludes credentials.

## Dependency boundary

Reviewed installed lockfile SHA256 8828a8cbb8fe7fbd2632daca3052e6035821539070036a0c05909b4222659a61: 88 packages, all registry.npmjs.org with integrity fields; declared licenses MIT39, Apache-2.0 36, BSD-3-Clause11, Unlicense1, 0BSD1. No absent license field. Keep installation scripts disabled (genai/protobufjs include lifecycle scripts). Pi telemetry defaults to NOOP and no exporter is configured. Dynamic imports and Agent/createModels construction under fetch/net/tls/http/https/dns/dgram blockers recorded zero network attempts during the short observation. This is not a whole-OS or all-provider-path network audit, vulnerability database audit, or signature verification.

Ten packages lack top-level license files, including four Pi packages. Distribution must preserve official license/notice texts; SPDX metadata alone is not a completed distribution notice bundle. Do not enable model catalog refresh, OAuth or other providers implicitly. Current runtime accepts fixture mode only; real DeepSeek loop remains unconnected.

## Reviewed implementation hashes

- runner.mjs: bb18e37792d96b5b5fa9ada18d8aa4c7804c3f8e978dd4bc473383438f6e2c5f
- independent.test.mjs: 0ca74b5a0661e3bac1f91dbf365e05bb202f0925b31d9f48a990bca2b5e449fb
- pi_transcript_host.py: 9253d7403272dd9c7ad24ce3683e2e75d95a30d60cfbadf11c54c5270fc526c6
- test_pi_transcript_independent.py: daff08158c42383c1cbc1d5855d592276ab785aff69e5c442501319967d08f56

No remaining blocking defect identified within this isolated fixture scope. Not approval for deployment, real-data external transmission, complete workbench integration or merge.
