# Independent public expert-group research acceptance — 2026-11-14

Separate native review; implementation files were not changed by this reviewer.
Reviewed frozen main-based candidate at `/workspace/mcis-expert-group-20261114`.
No real credential access, real provider request, browser workaround, remote write,
commit, merge, deployment or case-data write was performed by this reviewer.

**R1:36 independent tests passed, zero skips. All12 revised frozen hashes match.**
The original20-test acceptance remains historical;16 additional descriptor-lifetime
checks cover EG-D05. The original freeze is superseded, not deleted.
The tests run actual pinned Pi child loops against explicit scripted responses.
A separate test replaces the provider function in memory to inspect canonical
histories; its `fixture=False` result fields are not claimed as real inference.
Python IP socket connections are prohibited during independent testing.

Reproduce:

```sh
PYTHONPATH=research/expert_group service/.venv/bin/pytest --import-mode=importlib -q \
  tests_acceptance/EXPERT_GROUP/test_independent.py
sha256sum -c logs/expert-group-r1-impl-hashes-frozen.txt
```

## Defects identified before freeze and closed

- EG-D01: an exception while emitting `group_completed` initially left
  status=completed_unverified with outcome=failed. This was reproduced without any
  network. Implementation now demotes the group to not_accepted; independent
  actual Pi fixture test injects the final receipt failure and confirms rejection.
- EG-D02: the initial synchronous HTTP implementation restarted its timeout after
  receiving headers; that could exceed the role/group total deadline. It now uses
  an outer asyncio deadline across connect/request/header/body with task cleanup.
  Independent delayed-header test verifies bounded exit and client closure.
- EG-D03: blocking child stdin writes could ignore cancellation/time budget if the
  child stopped reading. Implementation now uses nonblocking writes with repeated
  deadline checks and a bounded response size. The implementation regression uses
  an actual nonreading child; this reviewer inspected the corrected loop and does
  not relabel that implementation test as a new independent case.
- EG-D04: completed run JSON alone could be mistaken for a complete export when
  final receipt/marker writing failed. Result now requires a valid completion
  manifest. Independent injections after result/HTML writes leave no verifiable
  complete export; verifier rejects absent marker, mismatched files and symlinks.

## Independent coverage

- Main ancestry and frozen input/runtime bytes: no PR56 ancestor is inherited.
- Actual two-child Pi fixture: six model protocol rounds, four tools, three reviews
  per role, distinct run IDs, zero provider requests, realModel=false, and no fact or
  consensus activation. All exported files0600 and output directory0700.
- Metadata receipts are readable before the mocked provider function is entered;
  receipt failure prevents provider entry and does not increment real attempts.
- Separate canonical histories never contain the sibling role's unique rationale;
  each begins with its own system prompt and two initial messages.
- Group-wide model budget does not reset at role boundaries. Unknown cancellation
  during an in-flight mocked provider call stops sibling execution and is not retried.
- Modified packet bytes, source text or locator are rejected before a child process
  starts. Returned text remains unverified and does not gain factual status.
- Stale disclosure acknowledgment is rejected before reading a credential or
  creating output. Final receipt and completion-marker failures cannot pass export
  verification. Tampering with each of four artifacts and a symlinked result reject.
- Actual generated comparison HTML escapes hostile model markup and contains no
  script, link, image, iframe or form elements. Same/different labels are shown as
  unverified opinions rather than consensus; fixture mode is explicitly visible.

## Limits and interpretation

No real DeepSeek acceptance was possible/attempted here. Literal configured-model
names and result flags are not independent evidence of provider/model identity.
No expert accuracy, source-PDF authenticity, human reviewer identity or production
security is established. Public source declarations are pinned inherited material;
this review did not download the PDF again. No browser engine was used: file chooser,
download and rendering in real browsers remain unverified.

The completion verifier checks local file/hash-chain consistency only. It is not a
signature and cannot authenticate a coordinated rewrite of all files/hashes. A
complete export may truthfully contain a not_accepted partial run; export completeness
and model-run acceptance must remain separate. Production identity, evidence-file,
time-line and hypothesis/archive modules are outside this research candidate.

## R1 follow-up — EG-D05 descriptor ownership failures

The coordinating review reported one leaked descriptor per attempt when a directory
occupied completion.json: os.fdopen raised before a context manager owned the raw
fd. The owner moved regular-file validation before wrapping, retained raw ownership
until fdopen succeeds, and closes untransferred descriptors in finally. write_new
uses the same ownership-transfer rule. No implementation change was made by this
independent reviewer.

Additional16 independent tests use actual Linux /proc/self/fd counts after every
rejection. Each of the four artifact leaves is replaced by a directory and a FIFO
and rejected eight times without descriptor growth. Each of the four read stages
has fdopen failure injected repeatedly; write wrapping and fstat failures are also
repeated. Finally, successful wrapping followed by read/write exceptions confirms
that context-owned streams close correctly. Failed writes may leave an empty partial
file, but no complete export is asserted. All36 independent tests pass; R1 freeze
12/12 matches. No remaining scoped blocker, real-model run or network access.
