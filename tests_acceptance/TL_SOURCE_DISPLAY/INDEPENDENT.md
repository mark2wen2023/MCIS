# Timeline source tooltip: independent review

## Verdict
PASS for the pure helper and static integration review, with browser/full-app validation still pending. No blocking defect found within this slice. No implementation edits, remote writes, API/model requests, or production data use were made.

## Frozen files checked
- `web/src/timeline/tooltip.ts`: SHA256 `c85fa356d151cba3a832f3595b873fab69ae09f6d80c8c6db6b9d971d0846ec3`
- `web/src/pages/EvidencePage.tsx`: SHA256 `476cbfa860f03378e23e55c2b0c3021b1a0bf06d750f5e50b5cc68209910dd3c`

Hashes match `logs/tl-source-display-frozen.txt`.

## Findings
- All server-controlled values inserted by the new helper (display time, title, source label, evidence IDs) are HTML-text escaped. All attribute/style values are static. No links, remote requests, new lookup, or privileged operations are introduced.
- Both boolean workflow flags are tested independently and only strict true/false receive those labels. Missing/null values do not imply confirmation or factual status.
- Source/evidence absence is explicit. The helper does not infer new references, deduplicate, resolve evidence contents, or claim evidence verification. Duplicate references and original order are preserved.
- The input event is not mutated. 1001 reference entries are retained, with bounded scrollable markup rather than truncation.
- Static EvidencePage integration passes existing raw timeline data to the helper, keeps the distance tooltip branch, and sets `confine` and `enterable`. This is source inspection, not an executed ECharts/browser interaction test.

## Executed checks
- Existing `timeline-tooltip.test.ts`: **14/14 passed**.
- New `timeline-tooltip-independent.test.ts`: **6/6 passed**; one case checks all 9 flag combinations.
- Scoped TypeScript helper/types check passed:
```
node_modules/.bin/tsc --ignoreConfig --noEmit --skipLibCheck --target es2022 --module esnext --moduleResolution bundler src/timeline/tooltip.ts src/types.ts
```
- Tests bundled using esbuild then run under Node. Initial scoped tsc command omitted `--ignoreConfig` and was rejected by TS5112; corrected command above passed.

## Remaining validation
Full application build, CI and browser rendering/hover/scrolling, touch usability, narrow-container layout, and actual ECharts interaction remain unverified. Source-level HTML escaping checks are not a browser XSS penetration test. This slice assumes the typed timeline payload supplied by the existing app; it is not arbitrary malformed-server-JSON validation. No genuine case or LLM behavior is exercised by this display-only change.
