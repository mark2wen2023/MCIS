# W18.3 Independent acceptance

## Result
- **24 independent CLI/API tests passed**, with actual standalone C# CLI for calculation, thresholds, source-race and policy-race cases. Missing-core test intentionally selects an absent executable and verifies 503, not a fallback calculation.
- **Real CLI + FastAPI + Vite + browser passed**: blank manual form, source selection, short-window/Unknown warnings, technical-only disclaimer, wrong input hash rejected, editing invalidates results, delayed replies after edit/case/identity changes cannot restore stale output. Chinese and emoji source titles exercised cross-language canonical hashing.
- Recorded implementation hashes rechecked after final tests. Original `mcis-core.dll` and `RestHours.cs` matched the prior accepted baseline and remained unchanged under concurrent standalone CLI calls. No original core rebuild or W11 work was performed.

## Independent defect / correction record
- A genuine core/API response with only `inputSha256` replaced by a syntactically valid unrelated hash was displayed by the original UI. Original browser assertion waiting for an error failed; its original assertion is retained. Owner added actual canonical SHA-256 verification and source snapshot binding; same test now passes.
- Fragmented-rest fixture initially asserted only `findings`. The unchanged core assigns the record-edge-truncated case to `insufficientData`. The fixture was corrected to examine both lists without treating insufficient evidence as a violation; no case was removed. It now confirms `RestSplit.actualHours=8`, `limitHours=10` and exact API/CLI agreement. The adapter's separately reported limit validation defect was fixed by owner before this independent API comparison ran.
- Raw original failure/environment logs remain local, not published.

## Calculation / boundary coverage
10-hour boundary and one second below; 77-hour seven-day boundary versus 70 hours; no work-limit findings in rest-only mode; 12-hour record with 4 Rest and 8 Unknown; complete-window coverage flags; fragmented rests; no `isCompliant` field. Invalid overlap/outside/kind/duplicate source/client hash, >14 days, >256 intervals, non-Z UTC and duplicate JSON keys rejected. Limits are engineering safeguards, not professional thresholds.

Source metadata is case-scoped, bound into canonical input SHA, and rechecked after real computation. Concurrent source change returns 409, permission revocation returns 403; denied identities receive no case-existence clues. Successful calculation and rejected inputs do not add DB rows. Original files are not read to authenticate the manual transcription.

## Professional boundary review
Read the linked official documents and existing `RestHours.cs` directly:
- [STCW Manila amendments, A-VIII/1](https://wwwcdn.imo.org/localresources/en/OurWork/HumanElement/Documents/34.pdf): ordinary rest baseline and split/interval provisions support a limited technical check, not unconditional compliance certification.
- [MLC 2006 consolidated through 2022 amendments, A2.3](https://www.ilo.org/sites/default/files/2024-10/NORMES_MLC%20Amendments-EN_2022_Web_1.pdf): maximum-work and minimum-rest are alternative systems; short breaks are excluded from rest. Exceptions and national application require separate review.
The wrapper uses direct schedule creation, never a complement that fills Unknown as Rest, and disables work-hour limits. Existing aligned/full-rest-segment splitting is explicitly a project assumption. This review does not validate its legal equivalence, fatigue diagnosis, HFACS, flag-state applicability, emergencies/exceptions, or source authenticity.

## Reproduce / publication scope
```
cd service
MCIS_DOTNET=<existing-sdk-dotnet> PYTHONPATH=. .venv/bin/pytest -q ../tests_acceptance/W183/test_rest.py
cd ..
MCIS_DOTNET=<existing-sdk-dotnet> MCIS_BROWSER_BIN=<existing-headless-shell> python tests_acceptance/W183/browser_real.py
```
Publish only REPORT.md, test_rest.py, server.py, browser_real.py and verified-impl-sha256.txt. Exclude local-* raw logs and caches. No deployment or publication performed by reviewer.
