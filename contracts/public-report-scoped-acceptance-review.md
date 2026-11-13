# Independent review: public-report scoped preview acceptance

## Material verification

Recomputed from the local PDF during this review:
- bytes: 4,524,411
- SHA-256: `99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f`
- Git blob: `cf7819378cd68eb9e7ef9c37d8d76c417a779cee`

These match the pinned visual-review record. Fresh Poppler renders of PDF pages 17 and 41 were inspected, alongside the existing enlarged crops. This run did not fetch a fresh remote copy.

- PDF 17 / printed page 15 / figure 6: YANGZE 22, IMO 9958212. Ship heading is 47.0; the separate course field is 54°. The displayed clock is 30-12-2024 22:01:54. The heading field does not explicitly identify true versus magnetic reference; keep **unknown**. No clock-zone label is visible.
- PDF 41 / printed page 39 / figure 27: YANGZE 22, IMO 9958212; explicitly **Heading True 48.0**. UTC displays 2024/12/30 14:01:54; LMT also displays that same time. Use the explicit UTC field, not an inference from LMT.

This is assistant transcription review, not investigator approval. Both observations belong to one published-report family. No original AIS/VDR telemetry, independent evidentiary provenance, sensor accuracy, or clock calibration has been verified.

## Accepted test plan, not an execution claim

1. Register two separately identified **report-extract CSV derivatives**, never sensor exports or original telemetry. Include report/PDF hash, page/figure locator, and transcription provenance. Their CSV byte hashes certify only those derivatives.
2. Keep figure 6 Heading reference unknown; keep figure 27 explicitly true. An ISO timestamp assigned to figure 6 must disclose the report-based Beijing-time interpretation, not claim the display labels a timezone. The scope failure must not be hidden by fabricating certainty.
3. Scoped joint request must return 422 before core execution because of unknown heading reference. It must not fall back to an unscoped request, remap course 54° into Heading, or relabel unknown as true.
4. Figure 27 alone can validly exercise scoped routing and actual W2 with an explicit UTC timestamp. A successful single-source response is only a single-source preview, **not evidence agreement, a cross-source comparison, or proof of accident findings**.
5. Preserve user_declared_not_verified, observationApproval:not_assessed, persisted:false and calibration warnings. Record investigator approval as pending, original telemetry/independence/clock verification as false.

This review verifies the material and the acceptance plan only. The new service/network execution and its statuses must be reported separately after the actual run. Synthetic report_extract fixtures in other tests are not this public report.
