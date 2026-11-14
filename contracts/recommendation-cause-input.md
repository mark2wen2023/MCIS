# Recommendation cause-label input validation

Applies to new POST /cases/{caseId}/recommendations and explicitly supplied
causeNodeIds in PATCH /cases/{caseId}/recommendations/{recId}. Existing input
shape validation still applies (including empty-list structural rejection).
After existing full-content/write permission and lifecycle checks, a list must
contain at least one string that is not empty/.NET-style whitespace-only, using
the service's existing _core_blank character definition. A supplied null on PATCH
is also invalid. Semantic failure is422 safetyrec_invalid_argument with no row or
audit write. Permission-denied well-shaped requests remain403; non-Draft patch
state errors retain409 priority. No silent trimming, filtering or deduplication.

This tightens previously accepted blank-only inputs; unknown external clients
may need adjustment. Existing web tokenization already excludes empty tokens.
Lists with any nonblank label retain their exact strings/order/duplicates, including
mixed blank labels, for compatibility. Existing stored records are not rewritten;
patches that do not supply causeNodeIds do not revalidate old labels. The stored
recommendation schema and legacy archive compatibility remain unchanged.

Labels are declarations only: no existence, source authenticity, causality,
case-bound graph, revision or digest validation is implied. A nonblank unknown
label may still be unresolved. Report+recommendation working archives remain
unsupported until a versioned dependency and restoration contract is implemented;
this rule does not establish safe round-trip closure or confer restored authority.
No model invocation or authentication upgrade is involved.
