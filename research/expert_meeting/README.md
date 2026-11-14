# Main-based offline meeting protocol

Base: main 73fc8002868d9c6894b5fce6d03f7db690291bf6 (PR78 receipt merged).
Source: 1d5262c9f8a491fd7b1d8037c4dff8988865770c. machine.py and demo.py
preserve source behavior; imports now reference packet.py, not the old engine.
packet.py extracts only stdlib packet/review validation functions and fixed role
identifiers; it has no execution path. No historical commits are imported.

The software chair 海青君 reserves at most two rounds/four turns, 16 model and
32 tool allowances, 600 seconds elapsed. These are protocol reservations, NOT
executed calls. Each role sees only the entire preceding completed round, never
its current-round sibling. Same labels are not consensus; disagreements remain.
Cancellation, timeout, failed and unknown outcomes stay distinct; partial opinions
are retained, late submissions rejected, exact replay does not spend another slot.
Exports replay the versioned event chain; hashes prove local consistency only.

`provider_mode='remote'` is a declared protocol mode without any transport. It
never authenticates a provider or executes Pi/DeepSeek, even when an input claims
to be a provider response. modelExecuted/piExecuted/identityAuthenticated remain
false. There is no browser endpoint, service registration, case writer, secret
reader, subprocess runner or network request path. Trusted binding is unavailable;
real execution remains HOLD. Do not connect a remote runner based on these tests.

## Public input and display contract

public-packet.json is byte-for-byte the prior frozen public excerpt packet (SHA256
1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e).
All three items use the SAME report, PDF page28 / printed page26. `claim` means
**人工编写测试主张（含反例）**, not a report quotation or verified conclusion.
`sourceText` and `citation` are the frozen report excerpt/quotation declaration;
review `quote` is the reviewer's selected substring, not an independent source.
These must be separately labeled by later display integration. Source URLs are
metadata only; this code never downloads or establishes publicness from a URL.
No per-item answer labels are present in the packet. No new model prompt or call
is added. The prior source provenance is retained, not reverified online here.

## Reproduce

`PYTHONPATH=. service/.venv/bin/python -m pytest -q research/expert_meeting tests_acceptance/EXPERTRECEIPT`

Use explicit `python -m research.expert_meeting.demo --simulate` for synthetic
output, optionally `--stop-after-turn 1`. `--verify-stdin` checks snapshot replay,
not model execution. This CLI prints local JSON only and does not create files.

The integration test writes a snapshot digest into the already merged metadata
Receipt and checks replay separately. It deliberately does not invent a group
completion.json envelope or claim verify_export validates meeting schemas.
Receipt filesystem limitations remain those in expert_group/RECEIPT_SCOPE.md.
The workbench, bridge, transport and authenticated browser execution are future
layers, not included or claimed complete. No real-model or browser acceptance.
