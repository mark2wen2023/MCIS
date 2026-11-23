# Explicit read-only single-seat preview boundary

Isolated MCIS research candidate based on 6d4b00032abdba1f3b1cce46ecd3dff488f1aa81, no default mounting, endpoint, queue, persistence or authorization. Imports unchanged fixed 6d4b00032abdba1f3b1cce46ecd3dff488f1aa81 seat_note.py and 420284ab5fd44c94b737f8c1cf51bc0ef09aea29 packet.py after Git blob verification. pins.json gives exact repository paths; export those two files with their basename to a source directory. Existing repository guidance applies; old source modules are not duplicated in this package.

    python -I -B research/single_seat_preview/check.py --sources /path/to/two-fixed-module-export

Five tests, exit 0. result.json is actual output and preview.txt its plain-text presentation. Tests use a clearly handwritten synthetic frame and pins; they do not read registered originals or perform authorization. A's reference is host-bound within this control, NOT evidence of an actual authorized read. It retains evidenceId and gap locator only; requestDigest/sourceSha256 are not exposed by the presentation. B reference remains null, never borrowed from A or a neighboring point. The gaps describe unavailable observation, not proof of no maneuver.

The only import boundary is preview(args, frame=..., trusted_pins=..., source=...). It first calls actual fixed seat.handoff with the actual fixed host validator. Only then does it produce synthetic_single_seat_readonly_preview/v1. It is not an AgentDraft and supplies no targetEntityType or queue identifier. The renderer outputs plain text; no clickable reference route, original access, confirmation or write button exists. actions is empty. EvidenceState and sufficiency remain separate from humanAction pending/confirmed=false/saved=false; factActivated=false.

Negative controls: conflicted is structurally allowed by the generic host but rejected by this exact single-seat import; wrong case/vessel/evidence identity, fake B locator, and added Confirmed field reject. T100 input also rejects rather than silently reusing T124.250 semantics. Initial regression failed because fresh imported exception classes were compared by identity; boundary now normalizes the two known fixed rejection classes to ValueError, then all tests passed. Original modules were not altered.

T100 reference 3eabe40551b871e509442e707e514f4ad0e26d85 t100_seat_crosscheck.py returns only pending flags, not the item/reference object this preview needs. Its separate SQLite/grant path was not executed or adapted here. Supporting T100 must preserve its actual missing-heading versus position-record distinction and supply an explicit safe boundary; do not construct missing references from this preview. No general conflict/unresolved classifier or reviewed state has been invented.

Separate future acceptance note, NOT a cross-schema bridge: parent independently reproduced 6eb9a25 pending-qualifier control with a known broken citation. Both good and bad pending controls withhold final semantic/recall/conflict metrics; locator accuracy differs 2/2 versus 1/2 and locator_mismatch remains nested while top violations is empty. A future presentation for THAT schema must display pending decision alongside known source failure, not turn pending into clean/passed. This candidate neither reruns nor imports that scorer, and never feeds its output into the seat.

Remaining boundaries: no actual human review, production source authority, UI/browser rendering, queue integration, model, real data or report save. This local preview is scope-limited acceptance material, not a new production workflow.

## Portable source preparation
No private directory is a runtime dependency. From a candidate checkout with both fixed Git objects already available, create a fresh source directory and export:

```sh
mkdir seat-fixed-sources
GIT_NO_LAZY_FETCH=1 git --no-replace-objects show 6d4b00032abdba1f3b1cce46ecd3dff488f1aa81:research/haiqing_single_seat/seat_note.py > seat-fixed-sources/seat_note.py
GIT_NO_LAZY_FETCH=1 git --no-replace-objects show 420284ab5fd44c94b737f8c1cf51bc0ef09aea29:research/expert_group/packet.py > seat-fixed-sources/packet.py
python -I -B research/single_seat_preview/check.py --sources seat-fixed-sources
```

If objects are absent, obtain only these two exact files through an authorized read mechanism before going offline:
- https://github.com/mark2wen2023/MCIS/blob/6d4b00032abdba1f3b1cce46ecd3dff488f1aa81/research/haiqing_single_seat/seat_note.py
- https://github.com/mark2wen2023/MCIS/blob/420284ab5fd44c94b737f8c1cf51bc0ef09aea29/research/expert_group/packet.py

Save raw file bytes under the basenames in pins.json, not HTML pages. Missing or altered bytes fail; no download fallback exists in the checker. No fixed source copies are included in this new directory.

Publication verification used a fresh temporary copy of this candidate plus a separate source export. Five tests exited 0 and stdout matched result.json byte-for-byte. Two additional input controls altered a fixed source byte and removed a source file; both exited nonzero. The published check.py and preview.py are unchanged from the independently reviewed local candidate. Git-export commands are documented but were not executed against a complete local object database this round; the tested mode is the exact source export. This distinction does not claim a production checkout, UI or original-access integration.
