# Report recommendation cause-label snapshot

Newly generated recommendation sections include a separate Draft sentence
recommendation-causes-{recommendationId}, sourceStatus RegisteredLabelsUnresolved.
It displays the original causeNodeIds array as JSON-quoted text, preserving order,
duplicates, spaces and escaped control characters without merging ambiguous labels.
Both languages explicitly state labels have not been verified as evidence links
or causal findings. Labels resembling evidence/rule IDs are not resolved or linked.
The sole citation points to the case's registered recommendation, needsReview=true;
registered refers to that record, not validation of its causes.

An absent/null/empty list is shown as absent (missing=true), not invented. Saved
report text remains a generation-time snapshot; editing the recommendation changes
subsequent reports only. The navigation citation opens the current recommendation;
it is not a revision-pinned or cryptographically authenticated source resolver.
Existing review controls may later change sentence status; generation never confirms
it. Existing reports and historical schema are not rewritten.

No permission grant, model call, external fetch or archive-profile change. Full
report permission applies to these sentences and exports. Report+recommendation
working archive still refuses until source closure/restoration semantics are
versioned and validated. This output improves visibility of registered labels,
not source authenticity, causal correctness or safe combined archive support.
