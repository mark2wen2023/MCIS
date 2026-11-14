# Proposed internal unreviewed result storage, v1

STATUS: DESIGN ONLY. Storage/index/schema-parser/import support are not implemented.
This increment implements only audit/package read protection and a tested capacity
precheck helper. It does NOT yet save generated results.

Design scope: actual internal server generation/save/export/restore foundation.
No public route, UI, approval, timeline mutation or transfer of local authority.
`save_unreviewed` accepts only RegisteredPreview, never caller output, run IDs,
incarnations, authorization flags or a returned computation envelope. Every call
computes a new result and creates a new random run UUID; no automatic replay or
recovery of uncertain delivery. Delivery failure after commit can leave a saved
run, so an eventual API must expose explicit reconciliation before retry.

A shared private verified-computation context owns initial capture, real core
execution outside DB transaction, and final BEGIN IMMEDIATE access/version/byte
recheck. Save writes directly inside that final transaction; returning the plain
preflight envelope and later accepting it is prohibited.

## Complete historical representation
Existing audit snapshot_ref, without truncation, contains prefix
`local-unreviewed-result:v1:` and canonical finite JSON:
- version:1; runId: server UUID; caseId; createdUtc; status:"unreviewed";
- request: exact strict RegisteredPreview (input declarations remain unverified);
- generationSnapshot: case incarnation+epoch and all source/parent identity and
  registration snapshots as captured at computation;
- serverPreview: schema-validated existing core response, previewOnly:true,
  persisted:false refers to that original computational preview, not saved run.
The outer status and local index identify the archived saved run. None of these
fields grants investigator approval or verifies semantic observation accuracy.

Whole canonical declaration <=2MiB UTF-8. Existing archive total/member budgets
remain enforced; save also prechecks resulting complete audit member <=16MiB.
Current source bytes can later change: historical saved data must remain exportable
if full declaration/index/audit match. No current approval state is inferred.

Local index contains only caseId, runId, case incarnation and exact audit sequence.
Export validates complete audit hash chain, index/marker/schema/case association
before permitting the table. All meaningful index fields are represented by the
saved full declaration and enclosing audit line. Import validates recognized
historical declarations structurally but NEVER reconstructs the local index or
current authority. Old declarations remain self-reported historical data, not
proof of a locally executed core or identity. No new archive version/section.

Unrecognized/malformed current v1 declarations fail closed for import/export.
Absence of an index after restore is intentional: historical audit can be read
under its existing permissions. A specialized history UI/query remains future work.
Future external read/list/save APIs need separate permission/uncertain-delivery
contracts; no endpoint is exposed in this foundation.

## Independent design review and prerequisite implementation
The initial design omitted an audit-read leak: audit permission does not grant
source content permission. The new guard recognizes both projected and raw-line
markers/action/entity/category, including malformed namespace and historical
records without a local index. It conservatively requires the existing full-case
content gate (all12 categories and applicable field rules), on audit queries and
package export. It grants no role and returns no partially redacted full record.

Capacity helper measures actual escaped UTF-8 audit lines plus newline, reserving
64KiB within existing16MiB member limit. It is not wired to any save operation yet,
and headroom is finite, not unlimited future export growth. Complete v1 parser,
unknown/duplicate marker strategy, both import paths, rollback/uncertain delivery
and archive roundtrip tests remain required BEFORE persistence is implemented.

Independent review found a second bypass: access-workbench exposes policy audit
lines directly. The same guard now protects that route, even if a historical result
marker is disguised as policy.update/Access/accessPolicy. Recommendation history
already requires the same conservative full-case content policy before returning
its audit rows; audit:verify returns only integrity summaries, not event contents.

The existing modern package parser accepts only default access policy. Tests
therefore verify history roundtrip under default policy, then revocation denial;
after non-default policy editing, authorized modern re-export still returns the
existing ARCHIVE_RESTORE_UNSUPPORTED409. This restriction also reproduces without
any result marker; it is not silently widened by this prerequisite. Legacy import
of working-record extensions remains explicitly rejected by its existing contract.
