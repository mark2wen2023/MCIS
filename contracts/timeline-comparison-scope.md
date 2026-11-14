# Timeline preview: caller-declared comparison scope

This optional request extension is a transient investigator declaration, **not**
verified vessel identity, source authenticity, independent evidence, review
approval, report extraction or durable provenance. No evidence/approval/archive
record changes. The existing byte-registration checks remain separate.

Each source may contain `comparisonContext`:
- `vesselLabel`: 1–128 characters, trimmed, case-sensitive exact comparison.
- `sourceNature`: `report_extract`, `sensor_export`, `other`, `unknown`.
- `sourceTitle`: report/source name, 1–200 characters.
- `citation`: page/table/figure/record locator, 1–500 characters.
- `timeBasis`: explanation, 1–300 characters; never adjusts timestamps or clocks.
- `headingReference`: `true`, `magnetic`, `unknown`, or null.

All text is nonblank single-line. Unknown fields are rejected. Citations are
plain text only: no link fetch, file lookup or hidden instruction execution.

Every source supplies context or none does. A scoped request requires one mapped
quantity per source, identical kinds and identical normalized vessel labels.
Heading requires an explicit declaration of true heading; magnetic or unknown
reference is rejected without conversion. Other quantities require null heading
reference. This does not prove the declaration correct or measurements comparable.
Units remain degrees (Heading/COG) and knots (SOG); no unit conversion is added.

Old requests without context remain compatible (including multiple mappings),
but response `comparisonScope.status` is `unscoped` with empty `sources`.
Scoped responses echo each normalized `{evidenceId, context}` and status
`user_declared_not_verified`. The new workbench requires context, checks its echo,
and refuses old-service responses rather than silently downgrading.

Changing any declaration clears prior results and invalidates late responses.
The UI displays declarations separately from SHA checks and states that report
extracts/derived values are not original sensor data. The mandatory review
checkbox checks mapping intent only; no API turns this into fact approval.

## Deliberate gaps

No automatic OCR/report extraction, verified document-to-CSV linkage, page-image
comparison, vessel registry matching, temporal uncertainty model, source
independence detection, magnetic variation correction or persisted review record.
Two sources with matching labels may still describe different vessels or events.
Different labels for the same vessel require human resolution. Existing core
uncalibrated-clock warnings remain and zero conflicts never imply correctness.
Real browser visual/E2E acceptance remains pending.
