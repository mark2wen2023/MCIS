# Actual public-report model → isolated review/archive UI acceptance

Run5d3b415b-9e8b-4c5e-aa98-9c978834fd85 completed successfully using actual Pi1.5.2
and official DeepSeek, configured deepseek-v4-pro, with **3 provider requests,
3 model rounds,2 tool calls,6 proposals and6 citations**. No mocked transport or
fallback in this run. Input was the fixed authorized Shanghai MSA YANGZE22 public
report damage excerpt (printedpage1/PDFpage3), not a complete case or testimony.
Source https://www.sh.msa.gov.cn/sgdc/104170.jhtml ; excerpt SHA256
c158ad790b5605dc4eea9303f9dc3748bb9f5ce07b969fd10f30cee9d6c45748.

Verified through existing components and protected host/RPC/storage:
1. Pi's reference completion selected the same server-owned validated candidate.
2. Saved that candidate into temporary working SQLite; no formal facts activated.
3. Actual React/HappyDOM component listed/opened all6 proposals, preserved their
   original quotes, and submitted per-item needs_verification reviews.
4. Review origin was fixed server-side scripted_test, explicitly NOT human
   judgment. Remount/reopen retained original candidates and review revision1.
5. Existing archive component exported v2 through the reauthorized download
   callback to memory, selected that package as a File, imported it, listed and
   read untrusted historical contents. Full proposals/citations matched the
   accepted originals; provider identity labels and script origin were preserved.
6. Restored history stayed activated=false/historicalClaimsVerified=false.
7. Components unmounted; temporary hosts/database/directory cleanup was confirmed
   before receipt terminal success; broker normal process exit0 was verified.

The terminal receipt includes model_result_verified, ui_review_verified,
archive_roundtrip_verified, cleanup_verified and accepted_pending_review. It
contains only fixed state/counts, not source/model text or credentials.
API credentials entered non-echoing stdin and stayed in memory, never argv,
environment, repository or receipt. No automatic repeat of a failed/unknown run.

## What this does not establish
HappyDOM is not a browser engine. This does not prove rendered-browser behavior,
actual browser disk download, production login, persistent user data deployment,
whole-case completeness/accuracy, expert review or CI. Six vs earlier seven
proposals are separate nondeterministic model runs, not a completeness score.
The temporary case was deleted after the test; no user production case was saved.
Earlier successful and failed/unknown tests remain separate evidence.

## Offline safety gate before the real run
Broker primary3/3; independent12/12 (14.20s); launcher independent3/3 child-process
checks including explicit mock full-chain and invalid-input no-secret output.
Related default host/RPC/working regression50/50 (40.16s), zero skips. Node runtime
baseline87/87 and launcher strict TypeScript passed. These are local, overlapping
checks, not full-repository or CI counts. Independent review found and fixed
prebuffered-input bypass of the total broker deadline before real invocation.

Implementation files: tools/pi-transcript/public-ui-host.py and
web/tests/pi-public-ui-live.tsx. Explicit --fixture is mock-only; explicit
--approved-public-ui requires prior user permission for the fixed report/provider.
The trusted host review_origin constructor defaults unchanged to unverified user
submission and is not a client RPC field. No deploy, merge or permission bypass.
