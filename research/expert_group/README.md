> 2026-11-14 更新：专家旧raw-key在线入口已默认拒绝；下文旧在线能力描述仅为历史。参见 research/expert_remote/RAW_KEY_HOLD.md，真实运行仍HOLD。

# Two model perspectives on a frozen public report excerpt

Research-only. Two independent Pi1.5.2 sessions examine the same fixed packet:
source/object attribution and uncertainty/precision boundaries. Neither sees the
other's opinions. Both return exact source quotations and explicit uncertainty;
the static page shows both without votes, consensus or case writes. These are
model roles, not independent human experts.

The packet contains three proposed claims about the oil-loss section of the public
YANGZE22 report (PDF28 / printed26), copied without suggested labels/rationales from
PR56's provisional corpus at254167e. Source text and its whitespace are unchanged;
original corpus SHA77cdbdf3f2656aa57b0772fadc909671bf5bbfbd7c480a3fcbb1cc79460ad19b.
Packet SHA1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e.
PDF URL/hash/page declarations remain visible. This slice has not independently
re-downloaded or authenticated that PDF. Proposed claims are questions to assess,
not assertions of ground truth.

## Offline use

Requires Python>=3.11, installed service requirements (httpx), and Node>=22.19.
Install pinned Pi dependencies with `npm ci --prefix research/expert_group`.

```sh
service/.venv/bin/python research/expert_group/cli.py --describe
service/.venv/bin/python research/expert_group/cli.py --fixture --output-dir /tmp/new-expert-review
service/.venv/bin/python research/expert_group/cli.py --verify-dir /tmp/new-expert-review
PYTHONPATH=.:research/expert_group service/.venv/bin/pytest -q research/expert_group
```

Fixture executes actual independent Pi loops with explicit scripted provider
responses; it never reads a key or calls DeepSeek. A fixture pass is engineering
validation, not model capability. Inspect comparison.html locally: all source/model
strings are escaped, no script, link, network or upload. Different proposed labels
are shown without a winner; equal labels explicitly do not mean consensus.

## Export completion and failures

Output directory must not exist; it is created0700, files0600. result.json always
states its artifact policy: incomplete without a valid completion.json. The last
manifest binds result.json, comparison.html and metadata receipt.jsonl. --verify-dir
checks all hashes, receipt chain/terminal and run binding. It proves local consistency
only, not authenticity, model identity or a human review. The result's run status is
separate from export completion: a fully exported failed/partial run is still failed.
A process/storage failure before the final manifest leaves incomplete artifacts;
never interpret a standalone result/page as a completed export. Existing runs are
never overwritten; no automatic retry occurs.

Two roles each have at most4 model attempts,8 tools,120seconds; group caps8/16/240.
Requests, pipe reads/writes and child cleanup are bounded. Stop on cancellation,
timeout, invalid quotes/schema/callId/completion or receipt failure. An uncertain
outbound outcome is retained as unknown; later work does not start. First-role data
can remain visible after second-role failure but the group is not completed.

## Real provider mode (not yet capability-accepted)

`--approved-remote --approved-disclosure <digest> --output-dir <new-path>` requires
the exact digest returned by --describe plus a bounded single JSON line with apiKey
on noninteractive stdin from an authorized secure credential channel. Do not put
credentials in chat, arguments, environment, artifacts or source control. No key
entry is requested by this project. The current implementation session found no
available secure environment credential and did NOT run real DeepSeek acceptance.

The digest binds public packet, both role prompts, tool/schema definitions, pinned
model/version and aggregate limits. It acknowledges scope, not authenticated human
approval. Destination is fixed official DeepSeek HTTPS with TLS, no redirects,
environment proxy, retry, model fallback or automatic switch to fixture. Python
alone holds the key; child Node receives only public prompts/tools and model results.
Node never receives a network provider adapter or secret. Any token/usage fields
inside the Pi adapter are placeholders, not measured billing/cost claims.

Before capability acceptance: independently review frozen implementation and the
exact public input; explicitly authorize outbound source and later model/tool history;
run both roles against real DeepSeek; retain actual request/response/terminal receipts;
review quote attribution, qualifiers and semantic errors without treating exact
quotes as semantic truth. Mock output fields cannot substitute for that evidence.
Native browser/CSP/download acceptance remains separate; sandbox must stay enabled.
No production authentication, evidence safety, timeline or hypothesis/archive code
is changed. No model output can activate a case fact or certify professional expertise.
