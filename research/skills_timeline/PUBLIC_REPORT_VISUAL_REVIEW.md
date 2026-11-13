# Original report figure review

## Verified source and method
Official publication: https://www.sh.msa.gov.cn/sgdc/104170.jhtml
PDF: https://www.sh.msa.gov.cn/u/cms/www/202505/191445221747637122775.pdf

Downloaded 2026-11-13, 4,524,411 bytes. SHA256:
99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f.
Git blob cf7819378cd68eb9e7ef9c37d8d76c417a779cee matches the repository PDF.
No report bytes changed or newly uploaded.

Two native agents independently viewed rendered PDF pages17/41 and enlarged
crops, and independently checked the file hashes. Figure6 shows YANGZE22,
IMO9958212, heading47.0 and course54; figure27 identifies the same vessel
and shows True Heading48.0. The 47/48 transcription is now visually checked,
superseding the earlier unreviewed-image limitation.

## Time and reference caveats
Figure6 playback clock: 30-12-2024 22:01:54, no explicit zone label on the crop.
The previously extracted UTC conversion relies on the report's Beijing-time
context, not a calibrated device clock.
Figure27's UTC AND LMT fields both show 2024/12/30 14:01:54. Use the explicit
UTC field; do not infer another +8-hour shift from the LMT label.
AIS crop's heading reference is not explicitly labelled; only VDR says True.
Keep that uncertainty rather than silently certifying reference compatibility.

## Integration consequences
The structured review JSON binds these readings to PDF hash/page/figure/crop,
vessel identity, quantity labels and time interpretation. It remains an
assistant visual transcription, not investigator approval or production data.
Its tests establish record/source consistency, NOT that Python re-read images.

Before enabling report-derived sources in the production Skill, the trusted
repository needs a reviewed observation record with these fields. Different
vessels, COG versus HDG, unreviewed extraction or uncertain time-reference joins
must not become automatic evidence-conflict conclusions. Preserve both the
original reading and the interpretation; never overwrite one with the other.
No production adapter or new case route was added here.

## Acceptance limits
83 local tests passed with real-engine paths enabled: previous80 plus3
source-binding/identity/time-policy tests. Existing actual-W2 replay still uses
report excerpts, not original telemetry. Original records, device clock offset,
sensor accuracy, independent evidence-chain and human signoff remain unverified.
No LLM, UI/API, CI, production integration, merge or deployment claim.
