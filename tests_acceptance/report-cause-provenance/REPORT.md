# Report registered cause-label snapshot

Branch feat/report-recommendation-cause-provenance, direct parent latest fetched
main4585016172094193b93ed200f1406c630e9fb8ab (PR88 policy test integration).
Remote archive candidates remain7aa9b9f (research/archive-main-73fc800) and
aeb8cf1 (feature/report-timeline-web-v1); neither is incorporated here. Their
combined report+recommendation source closure remains unsupported. Prior blank
label input candidate0666515 is also not a dependency of this feature.

## Actual gap / bounded improvement
Current report recommendation sentences snapshot title, addressee, status and
deadline but omit causeNodeIds. Three new real HTTP checks fail on unchanged main
because no registered-label snapshot sentence exists (baseline.txt,3 failures).
New reports now include one distinct Draft sentence per recommendation, original
label array as JSON-quoted text with no trimming/deduplication, and bilingual
explicit evidence-link/causal-finding not-verified caveat. sourceStatus is
RegisteredLabelsUnresolved. Citation is solely the case's registered recommendation
and needsReview=true, never a guessed evidence/COLREG/HFACS object. Labels that
look like EV-001 remain labels. No model or source-resolution inference.

The sentence preserves generation-time values in the existing report document;
updates to the recommendation do not rewrite already saved reports. New generation
uses new values. The clickable citation still navigates to the current register;
it is not a revision-bound resolver, digest proof or historical lookup API. Missing
legacy arrays remainnull with missing=true; no fabricated label. Current role/
source permissions, report review controls and export behavior are unchanged.
Existing rows/schema/archives are not migrated. Report+recommendation archive
still409 and no state write in the covered scenario. Contract note records limits.

## Actual verification
Final focused real local HTTP tests:5 passed in2.18s (focused.txt), covering exact
ordered/spaced/duplicate and markup/control-containing labels, only register
citation, Draft/needsReview, old report stability after edit, new report values,
403 no leak, archive409 unchanged DB, DOCX actual ZIP/XML text preservation and
missing legacy labels. These use synthetic local records, not real case findings.

Expanded sources/access/font suite plus initial3 cases:95 passed,2 failed in17.73s
(after.txt). Both failing font tests receive403 at report creation before font
checks; clean detached main4585016 reproduces both (2 failed in0.74s,
main-control.txt). Existing font fixture fixe91e4cf is unmerged and not silently
included. Final focused5 overlaps the earlier3, not additive unique coverage.
Independent acceptance results are recorded separately.

No real-browser/visual-DOCX/PDF acceptance: XML text preservation is not layout.
No actual AIS, HFACS/.NET or model execution, no authenticated SSO, no full-suite
pass. Existing long locks, memory limits and unknown-commit constraints unchanged.
No software installation/download, merge or deployment. The original candidate
01241b6 was subsequently pushed to feat/report-recommendation-cause-provenance;
this historical test record describes its original4585016 parent, not current main. This is a
readable registration snapshot improvement, not safe combined archive support or
proof of cause/evidence authenticity. Unknown external output consumers may see
an additional generated sentence; existing stored report documents remain intact.
