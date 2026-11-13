# Strict historical result declaration v1

Historical schema only. No result index, save operation, live receipt, approval,
UI or endpoint is introduced. Valid imported declarations remain untrusted history.
The machine contract is schemas/unreviewed-result-history.schema.json, combined
with semantic linkage checks in timeline/unreviewed_history.py.

The exact reserved prefix is local-unreviewed-result:v1:. Recognized namespace,
action, category or entity with a missing/malformed marker fails closed. Unknown
versions and duplicate run IDs are rejected; unrelated old audit events are not
reinterpreted as results. Source/parent/run/case UUIDs and exact source ordering,
request mapping, digests, timestamps, parent relations, case epoch and core result
references must agree. All declarations remain unreviewed; user-supplied public
reports/relations and claimed core executions are NOT authenticated by a valid
schema or imported hash chain.

Canonical declaration budget2MiB UTF8, maximum32 nested containers, finite JSON
and duplicate-key rejection. The enclosing audit metadata must match the run and
creation timestamp. Existing whole-archive/member limits and audit-chain rules
continue. Current source bytes/permissions are not authority for imported historical
claims; no local incarnation/index is reconstructed from a historical result.

Both import paths validate before SQL/blob writes: modern parser after audit-chain
validation; legacy import after existing chain validation and before case identity
allocation. Existing working-record packages still require the modern endpoint.
Export validates reserved declarations after content authorization, so it will not
knowingly produce an unsupported result history. Malformed reserved historical
claims cause explicit rejection, not truncation, implicit migration or approval.

This stricter namespace has never been emitted by a product save feature. Earlier
synthetic malformed-marker access tests remain useful for read isolation, but their
export expectations now become rejection; roundtrip tests use a valid deliberately
self-reported historical fixture. Non-result archives retain existing behavior.
