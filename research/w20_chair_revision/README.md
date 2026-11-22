# FourChair selected-source attribution — synthetic internal seam

Parent 90d05818aabb09913ca59138d210755236195ef3; same independent candidate branch.
Uses existing FourChair issue/submit_simulated/receipt, not another chair.
Reference: 431d9d5ff06d051b9017ae350a5dabaf2ad61e8b single cited-excerpt principle.
Synthetic originals: fixed 6996fa05 ECFC package. No W19 blind materials.

## What changed
A trusted in-process synthetic host may call the INTERNAL
_select_review_sources_simulated(registry, selection) before issue, after binding
the draft. The registry must match that version's sourceSetDigest. Selection maps
each existing review item to exactly one source ID; unknown IDs are rejected.
Host selection is explicit in the issued context and covered by contextDigest.
submit_simulated keeps its existing signature and review shape. It accepts no
source registry/citation payload from the submitting seat. The existing _validate
checks each item against ONE host-selected excerpt. Neither other registered
excerpts, excerpts selected for other items, nor concatenations are searched.

Accepted opinions retain role, attempt ID, draft version/digest/generation and
locatedReviewSources (source ID, raw-byte SHA-256, one-based line, locator, excerpt).
The existing review carries its exact quote separately. Opposite statements and
opinions remain separate; even unanimous labels keep factVerified=false.

locatedCitationPlaceCount means ONLY 可定位引用处数, deduplicated by original raw
SHA-256 + exact line across accepted source-bound opinions. Aliases and seats
are not counting keys. It does NOT count independent witnesses or establish
evidence weight; sourceCountIsWeight=false, sourceIndependence=NOT_ASSESSED.
Unbound/default receipt and ticket shapes do not gain these fields.
The count excludes outstanding/rejected opinions and is not a causal conclusion.

## Trust boundary and gaps
This is a private research-host seam, not a product API, source-access grant,
identity check, original-file integration or persistent consultation interface.
The host must first run the existing locator against the fixed bytes and verify
the same case before constructing the registry. FourChair checks the registry
digest and correspondence; it does NOT itself authenticate a source or run I/O.
A sourceSetDigest supplied by an arbitrary caller is not a credential.

The test does actual locate() on the frozen files, then passes the resulting
registry through this seam. No load_packet/default pin change is made. Tests mock
the constructor's storage and packet loader to use pure synthetic items only.
Thus no real initialized ledger meeting/default evidence integration is claimed.
An actual product host and professional/human adjudication remain unimplemented.

Selection can change only in ready state. An issued ticket freezes a deep copy.
Changing draft binding clears the future selection and makes the existing ticket
stale through the previous generation checks. No cross-draft migration/restart
is added. Once opinions exist, draft rebinding remains prohibited.

## Reproduce (existing Python, no install/network)
From this candidate checkout:
```sh
python -I -B research/w20_chair_revision/check.py \
  --ecfc-package /path/to/verified-6996fa05/research/ecfc_pending_handoff \
  --locator /path/to/verified-431d9d5/research/w19_case_ranking/source_traceability/check.py
sha256sum -c logs/W20_CHAIR_SOURCES-impl-hashes-frozen.txt
```
Explicit dependency paths can be verified fixed Git exports. The ECFC manifest
SHA, each manifest-listed byte, locator blob and packet.py blob are checked.
No dependency/original copies are committed. The script prints checks, never
saves consultation opinions or reports. Existing previous freezes are historical.

## Executed coverage
2026-11-22 full check exited 0; no assertion skips.
- Original revision/generation/default-path tests retained, including A->B->A.
- Wrong source-set digest and unknown source selection rejected before issue.
- Four same-label seat opinions referencing OBS-1/its alias retain four opinions
  but only one citation place; no fact verification.
- Unselected registry quote rejected with no settlement or opinion change.
- With two explicitly selected excerpts, borrowing the other item's text and
  joining the boundary between both excerpts are also rejected.
- Correct single/multi-item quotes accepted through actual _validate.
- Opposed synthetic inspection statements retained separately with exact sources;
  conflicting labels stay disputed, three byte positions are not causal proof.
- Active selection replacement rejected; returned ticket/receipt copies cannot
  change the host-frozen source association.
- Draft change rejects a source-selected old ticket before settlement.
- Default no-selection ticket/opinion/receipt adds no source fields.

Actual classes/functions: FourChair methods, packet._validate, source locator.
Mocked: Ledger, constructor file open/close, packet-loading pair only.
NOT RUN: real DB/identity, external runner/model, service/browser, professional
correctness, human sign-off, independent source authenticity or causation.
Pending independent review. No merge/deployment.
