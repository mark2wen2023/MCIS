# ET0 synthetic host-to-scoped-comparator trial

Research candidate only; no product caller/API, registry, account, model, database,
W20 change, real calibration signature, or authorization proof. The host is a
hand-authored in-process test fixture, not an authenticated authority. Every
result says authorityVerified=false, pending_human_review and saved=false.

## Overlap checked and new scope

PR46 already implements scoped Decimal interval comparison and its refusal rules.
The previous SK-T01 synthetic check already distinguished corrected display time
from reviewed calibration. The SK-T01 source-bound preview adapter delegates
uncalibrated NMEA to W2 and does not supply this scoped calibration seam.
This trial adds only the host-side binding from exact synthetic bytes/record
locator and a selected reviewed calibration version to the existing PR46 types.
It does not implement another comparator or migrate these mechanisms to production.

## Replay

Use existing standard-library Python (3.10+), no installation; no -O. At this
candidate's repository root, with the fixed parent Git objects present:

```
python -I -B research/evidence-timeline-et0/host_trial/check.py --repo .
```

The loader uses only local `git --no-replace-objects show`, with
GIT_NO_LAZY_FETCH=1 and GIT_TERMINAL_PROMPT=0. It never fetches. Missing objects fail.
Alternatively pass a local directory containing the two original fixed files:

```
python -I -B research/evidence-timeline-et0/host_trial/check.py --dependencies /absolute/path/to/fixed-export
```

Both modes require exact Git blobs from 31c2a896d1717a7876a416f7d8ca295fa41378b8:
- timeline.py: 1c2f3457eb05833b02b1a2f79820c54c90e1118d
- scoped.py: fceca88fcbee782eca870b7c16824dd31b721d23

No copies of those modules are committed in this package. The dependency-export
mode was actually run: 13 tests passed, exit 0 (tests.log/results.json). Local
available checkouts lacked the fixed commit, so --repo was not positively run in
this session; do not count that mode as independently verified. The original ten
scoped tests were separately run in the preceding source review, not counted as
13 new tests here. sha256sum -c SHA256SUMS checks this package.

## Exact boundary

Proposal fields are only case, left and right references. Each reference has
sourceId, revision and a narrow /rows/key locator. Model-supplied confirmation,
clock, offset or reviewer fields fail. The host resolves original bytes against
its pinned SHA256, document case/identity/version and exact record; it selects
calibration by source+locator, not by a model calibration ID. Calibration binds
source revision/bytes/locator, clock, version, raw scope, target basis, independent
basis bytes/locator, offset, uncertainty and synthetic review state. Re-pinning
changed original bytes does not make an old calibration applicable.

The host constructs PR46 Source/Event/Correction/Scope/ScopedCorrection and calls
validate_events/scoped_interval/scoped_compare unchanged. No numeric timestamp
creates no Event and yields undetermined. Unknown/absent/disputed review remains
unaligned. Bad identities/bytes/bindings and partly out-of-scope ranges fail.
Review status is synthetic input; reviewed means only that the test selected a
synthetic-reviewer record. Python object ownership is not a security boundary.

## Visible invented control and outcomes

Fixture is entirely in check.py; no blind data or report answers. Source bytes are
canonical JSON constructed by the fixture and pinned before the call. Numeric
seconds are manually normalized to UTC epoch 2030-06-03T16:00:00Z; timezone parsing
is not implemented/tested. Panel local display 2030-06-04 00:01:10 UTC+08 is 70;
its synthetic reviewed offset -97 gives -27. Already aligned VDR alarm is -27,
with a separate explicit reviewed zero correction; applying -97 again is rejected,
even if a synthetic host anchor repeats that offset. A panel -194 change is also
rejected against its -97 reviewed basis. This is bounded policy, not automatic
semantic detection of arbitrary double-calibration histories.

Alarm comparison yields overlap-not-identity, not proof of one alarm. VDR sound
at -20 permits before only under the supplied zero-uncertainty synthetic review
assumptions, never causation. Error bounds of zero are fixture assumptions, not
estimates of real devices. Cargo loss has no numeric time and remains undetermined.
Unknown/disputed review, missing review and different target bases stay undetermined.

13 tests cover unchanged positive inputs, temporal-only output, wrong case,
source version/bytes/locator, model authority injection, unreviewed/disputed/absent
review, double offset on aligned rows, changed panel offset, partial scope,
unknown loss time, missing/misbound review, differing target basis, and changed
bytes with stale calibration. Some tests contain multiple negative subcases.

## Remaining blockers

No authenticated source repository, reviewer identity/authorization, calibration
revision store, signature verification, atomic revocation/snapshot handling,
report/VDR extraction adapter, timezone validation, drift handling or durable
history exists in this trial. Host can fabricate or replace all its inputs; this
code cannot prove them true. Only the narrow fixture format is supported; this is
not a hardened untrusted serialization parser. Real implementation must independently
supply these authorities. The registered trajectory read path is not called here;
its Access/audit or original-source authorization must not be inferred from these
pure tests. No contracts, production APIs, frozen samples or W20 files changed.
