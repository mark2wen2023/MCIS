# Four-axis extraction scoring — developer-visible control only

Pure research candidate based on 194ee6be7a4b31c0e23b5615b5d60cd9b0667ed0, whose four reused pure modules are pinned below. No model, blind material, product integration or authority claim. Only this new research directory is changed.

## Fixed-source overlap checked
- 194ee6be7a4b31c0e23b5615b5d60cd9b0667ed0: synthetic-report-draft/project.py and check_utf8_joined.py implement exact byte location and host-annotated conflict guards. The existing six joined tests were rerun unchanged, exit 0.
- 0cc0624a31a08f81684ac9b0ddc42971c25670da: registered-utf8-draft/check.py checks synthetic registration, one Access, and unsaved three-node projection. Source read only this turn.
- 71b47a47ec8d192048a095b082159cce075654ca: same path adds late projection rejection with committed Access retained, including all seven table snapshots. Source read only this turn.
- research/semantic_support/evaluate.py is a provisional fixed-item label comparison, not a four-axis free-extraction scorer; it requires all predefined prediction items. Its two existing test module names/assertion themes were also checked. No corpus/answers were loaded.

The source tree at 71b47a4 contains only that evaluator among research eval/score/metric Python paths. This is a scoped inventory, not a claim about every unpublished local artifact or future branch.

## Run
Existing standard-library Python suffices:

    python -I -B research/report_extraction_four_metrics/check.py --dependencies .

Run from a checkout of this candidate commit. The inherited files satisfy pins.json, which records four dependencies at 194ee6b and checks their Git blob SHA before import. Alternatively pass --dependencies /path/to/pinned-export with the same repository-relative paths. Missing or mismatched files fail before tests. No dependency installation or network occurs. The executed publication check used this unchanged script with a separate four-file pinned export: 15 tests, exit 0; result.json is its actual stdout. A full Git checkout run was not executed in this environment. Private-path execution metadata and runtime logs are deliberately excluded. No dependency copies are added.

## Scoring definitions
- Citation coverage: emitted atoms with a supplied citation / all emitted atoms.
- Locator accuracy: citations accepted by the unchanged pinned UTF-8 locator / supplied citations. Source raw SHA is separately checked; atom and citation identities must agree.
- Semantic support: independently supplied S labels / emitted atoms. S=supported, C=contradicted, U=insufficient, D=pending adjudication. This prototype does not infer any label; developer control annotations are explicitly not independent expert review.
- Mandatory recall: unique required IDs matched by supported atoms / predeclared required IDs. Optional outputs cannot inflate this numerator. Matching is supplied in review, never by keyword matching.
- Conflict retention: predeclared groups with every required side matched by separate atoms having a valid located citation / all applicable groups, including wholly omitted groups. Both attributed statements being supported does not resolve which underlying account is true.

The visible source is only the already published three-line synthetic fixture. Negative 1 pairs its exact 'execution unconfirmed' quotation with a claim that execution occurred: the hand-authored control assigns U, not C, since lack of confirmation does not prove nonexecution. Negative 2 removes one fog account. The original projector also rejects that one-sided group.

Expected arithmetic: full control 3/3 locator, 3/3 support, 3/3 recall, 1/1 conflict; unsupported claim 3/3, 2/3, 2/3, 1/1; one-sided output 2/2, 2/2, 2/3, 0/1. These are diagnostic control results, not official evaluation scores or model performance.

Malformed identity/binding/denominator inputs and failed runs produce no metrics. Valid empty output has undefined precision/support and 0/3 recall after completed review. Zero applicable denominators are null, not 100%. Incomplete review explicitly lists pending required IDs and withholds final support, recall and conflict metrics. Review binds output digest and source SHA, but is not signed/authenticated. This is a narrow trusted-input research function, not an untrusted-input API or production validator.

## Observed and unverified
15 local unittest methods pass, including six malformed subcases, no-output/no-applicable/pending controls and different citation/atom denominators. Six existing joined tests pass separately; counts must not be added as model successes.

Future independent reviewers must predeclare required propositions/conflict groups, adjudicate S/C/U/D and atom matches without feeding answers to extraction, and resolve missing review before final metrics. No actual model, independent human evaluation, PDF/OCR, authenticated source or production save/read integration is tested here. Calibration remains HOLD; W20 and all frozen packages remain untouched.

## Duplicate-count guards
Same-atom citation identity is the verified original SHA-256 plus half-open byte range returned by the unchanged locator. Citation IDs cannot distinguish the same location: repetition rejects the entire scoring input with malformed / metrics=null.

Exact atom identity is the literal claim plus sorted citation identities, excluding atom/citation IDs and review labels. Located citations use normalized raw-byte identity; invalid citations retain their canonical span fingerprint. Renaming IDs, reordering citations, duplicate uncited claims, or duplicate claims with identical invalid citations cannot inflate a metric: the entire input is rejected. No fuzzy/paraphrase equivalence is claimed. Overlapping but unequal ranges are not collapsed. Distinct claims may legitimately cite the same span; this is not independent evidence and semantic review is still needed to detect paraphrase padding.

One atom cannot match more than one side of any conflict group. Composite statements must be split into separately attributed atoms. Each side counted for conflict retention must have a matching supported atom with at least one successfully located citation; unlocatable or uncited sides cannot complete the group. This checks traceable attribution structure, not the truth of the claim or whether a human match is correct. It does not require different source documents: two contradictory attributed statements can occur in one document. Reviewers remain responsible for matching the right claim to its cited side.

Five added test methods cover renamed repeated citations, duplicate atoms with renamed IDs (including reordered citations/uncited/invalid-location variants), multi-side matching by one atom, missing/invalid side locators, and legitimate distinct claims sharing one span. Original three control outputs remain identical. No source modules, fixture bytes, blind material or product code changed.
