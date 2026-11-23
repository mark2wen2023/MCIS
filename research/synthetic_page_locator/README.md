# Synthetic two-page coordinate regression

Research-only fixed coordinates, NOT a PDF/OCR implementation. Parent: 4bab226c3d05464d86337e5e0ff4bff9f6b9123f. No old data/scorer, contract, W20, service or 3D code changes.

## Prior overlap and guidance
AGENTS.md and docs/HANDOFF-STAGE1.md were consulted. No .agents/skills paths exist in the fixed parent tree or examined local checkout. The existing tests_acceptance/synthetic-utf8-locator/check.py deliberately rejects page fields and maps UTF-8 logical paragraphs only; its README explicitly disclaims PDF/OCR coordinates. The synthetic-report-draft page mode has handwritten page/paragraph references, not page rotation mapping. Neither is repurposed as a PDF transform. No real report, PDF or media file was opened.

## Run
From repository root, standard-library Python only:

    python -I -B research/synthetic_page_locator/check.py

Nine unittest methods pass, exit 0. result.json is actual stdout. No dependencies, installation, network, model, server or browser. SHA256SUMS covers the package except itself.

## Visible controls
source.json is the original synthetic layout JSON byte stream, not a PDF. Its SHA-256 is 5e81572e5cd74c9a73c0cb96b216f6d54a32d3f03c7e333a24b04174f2e8a0c6. Two handwritten logical pages both contain 08:30: page 1 is a rehearsal schedule; page 2 is a panel alarm display with unknown calibration. They are different records, not one event or a time alignment.

Page 2's table region is represented as a clockwise-90-degree candidate view, not rendered or extracted. Original page size is 600 by 800 synthetic units. Its candidate size is 800 by 600. Inverse map is x_original=y_candidate, y_original=800-x_candidate. Candidate rectangle [560,100,600,300] maps all four corners back to original [100,200,300,240]. Coordinates are top-left-origin synthetic page units, not PDF points, pixels, crop-box or media-box coordinates.

host.json is an explicitly trusted TEST fixture, binding original byte SHA, record ID, page, record index and reviewed transform. Its reviewed flag is handwritten, not actual reviewer approval. Proposal cannot set that flag or source SHA. Exact mapping requires the pinned source version, correct record/page/text, a host-reviewed same-source/same-page transform, canonical inverse matrix and dimensions, finite in-bounds coordinates, and equality with the independent handwritten original rectangle. The narrow supported transforms are identity and whole-page clockwise 90 degrees only.

Wrong page or original SHA rejects. Missing/unreviewed/wrong-source/wrong-page/invalid-matrix/unsupported-rotation/wrong-size transform falls back to page with originalBox=null; wrong/out-of-bounds/nonfinite candidate box likewise cannot claim exact coordinates. No fallback searches for the repeated time string on another page. Exact success is named exact_fixture_box and authorityVerified remains false.

## Limits
Only fixed coordinate math and attribution guards were run. No actual PDF generation/rendering/parsing, rotated table extraction, OCR text, page-label inference, crop/scale/skew transformation, authenticated host or review authority was exercised. A real integration must obtain and verify page geometry and the complete preprocessing transform chain against the same original bytes; until then it cannot claim exact page coordinates. Locating 08:30 does not prove its semantics, clock accuracy, event identity, ordering or causality. This package does not change or connect the four-axis scoring tool.
