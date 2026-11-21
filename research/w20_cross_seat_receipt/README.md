# Cross-seat source identity — synthetic receiver acceptance
Status: self-tested research fixture, not FourChair meeting acceptance.

## Existing implementation / gap
Inspected fixed 26451febf955f4b6d7654e9a4b32ca70c2ec4c13:
- research/expert_budget/four_chair.py blob 9417ad2a5e8cbef8e44dba15dd5307f0beba134c.
- research/expert_budget/test_four_chair.py blob e76849770eedeb157b3456119796b971891a4d8a.
FourChair binds attempts/context and returns role-labelled opinions; receipt indexes per-round labels with factVerified=false. Its packet entry is fixed. It does not expose a versioned ECFC draft/source registry, cross-seat original count, or observation-versus-causation source projection. Existing unanimous-label test is not cross-seat source identity coverage. No existing entrance or contract is altered here.

This fixture reuses actual packet._validate (blob ff2018dad2d58e9fe158f503ecd71a004c20e226) and actual d1c1d37 locate (44fc5d82279db5fa3a3c748161f3122708e85668), with exact 6996fa05 ECFC sample bytes. The synthetic packet passed to the standalone validator is test input, not an injected FourChair meeting. No FourChair instance, DB, budget, provider or lifecycle is run.

## Reproduce
In an MCIS checkout containing the fixed sources (these paths are present at parent 6996fa05), use existing Python:
```bash
python -I -B research/w20_cross_seat_receipt/check.py \
  --ecfc-package research/ecfc_pending_handoff \
  --packet research/expert_group/packet.py \
  --locator research/w19_case_ranking/source_traceability/check.py
```
Explicit paths may point to verified exports of those public fixed files. No installation/network/fetch is performed by check.py. It verifies the published frozen sample manifest, all listed sample bytes and both executed dependency blobs. No prior task/private directories are referenced.

## New coverage
Same frozen synthetic-draft-v1 digest 213b8bd46acf49a489bfc46523449d83a75751f5c714b925b10810d3e2765959 across both evidence sets.
- Four attributed role opinions retained, all referring to one observation: 4 opinions, 1 located original, 0 causal-statement originals.
- Alias of that same original: still 4 opinions / 1 original.
- Two opposite inspection statements added: 4 opinions, 3 originals (1 observation + 2 inspection statements); source text and asserted stance retained separately, conflict pending.
- All four supported labels cannot vote away opposed source statements.
- Five negative cases: draft content changed; opinion version changed; opinion digest changed; unknown source alias; quote absent from supplied source text.

Identity key is raw original file SHA-256 plus exact one-based line, after existing locate verified file hash/line/record/excerpt. Seat, alias, free quote and statement text are not counting keys. Distinct source byte locations do NOT establish independent witnesses or evidence weight; independenceBeyondByteLocation=NOT_ASSESSED and sourceCountIsWeight=false.

The phase change adds evidence, not a new draft revision. All outcomes keep causalConclusion/jumpAnchor=null, humanConfirmation=PENDING, factVerified=false. Supports/refutes are frozen synthetic source assertions, not blind answers or adjudications. All opinions are hand-written synthetic test inputs, not actual professional opinions. No semantic correctness score.

## Formal work still missing
A trusted existing host would need to bind the actual draft revision and located provenance to submitted opinions, then expose this separation to the real chair/human-review path. This fixture defines no production interface, grant or cross-repository contract and verifies no human sign-off. No blind-review data, real case, service, browser, model, report save, deployment or main/3D modification.
