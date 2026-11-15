# Workbench registry-receipt observation text editor

Opt-in panel beside each conflict, separate from existing note/status editing.
The initial control calls existing GET conflict/revisions: only after successful
case/conflict-shaped response does it render observation inputs. This uses existing
full-history/source policy and can be MORE restrictive than the receipt route for
some historical references; it does not assert equivalence to timeline permission.
Denied users keep existing note/status controls. Server rechecks all actual writes.
Self-reported role headers remain unchanged, not production authentication.

Scope: a/b valueText only, evidence IDs not editable. Displays current observation
and proposed text/source ID. Draft lives in page memory; selection/list reload does
not replace it. Page navigation/reload loses it. Explicit refresh/adopt reads current
editable version while retaining proposed text and using latest nontext fields;
changed source IDs refuse rather than silently switching source. No automatic retry.
User must compare again, request server receipt, inspect displayed full SHA/custody
sequence/expiry, then explicitly submit. Editing text clears receipt. Response
case/conflict/version/metadata boundaries are checked; no client digest creates receipt.

Submit sends existing document+proposed a/b+expectedVersion+sourceReceiptId. Late,
expired, mismatch,409/412/428 errors clear receipt and preserve text.403 additionally
closes source editor without changing original handling controls. Unknown500/network
result is NOT declared failed: prompt read current state before deciding next action,
never automatically repeat. Local expiry prevents send; server time is authoritative.
Identity-declaration changes hide editor/discard receipt, retain draft in memory and
ignore late responses; cannot infer outcome of an already submitted request.
Success reloads list but keeps draft, requires explicit current-record refresh before
further editing; no original verification or fact approval claim.

This is no PDF viewer/source-file read receipt and not human-reading evidence. Source
metadata only, no wider permissions. New-source assignment and unknown-source review
remain unsupported by this UI. Backend legacy-client rules unchanged.
