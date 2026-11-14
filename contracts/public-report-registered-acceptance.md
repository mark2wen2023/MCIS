# YANGZE 22 report excerpts through registered preview

This acceptance uses the existing public investigation report, not synthetic
accident values. The original bytes were already in the repository; no new PDF
upload or source replacement is performed. Publication:
https://www.sh.msa.gov.cn/sgdc/104170.jhtml
PDF: https://www.sh.msa.gov.cn/u/cms/www/202505/191445221747637122775.pdf

Pinned SHA-256:
`99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f`.
The automated test verifies this hash and the existing assistant visual-review
record. It does not automatically read image pixels or replace investigator
review. See `public-report-scoped-acceptance-review.md` for independent visual
review of the source.

## Actual controlled flow

The test starts a disposable seeded database and real uvicorn loopback server,
then performs the normal file-preview/confirmed-registration API calls for two
small CSV derivatives reconstructed from the existing reviewed observations:

| Derivative | Locator | Recorded quantity | Interpretation retained |
|---|---|---|---|
| Figure 6 | PDF17 / printed15 | Ship heading47°, separate course54° | Heading true/magnetic reference unknown; 22:01:54 clock has no explicit zone label; UTC conversion relies on report Beijing-time context |
| Figure 27 | PDF41 / printed39 | Heading True48° | Explicit UTC14:01:54; identical LMT display is not used for another timezone conversion |

Both are YANGZE22 / IMO9958212, **one published-report family**. They are
registered as Document derivatives, with `sourceNature:report_extract`, report
name, page/figure and PDF hash in plain-text citation. The intake timestamp is
the CSV reconstruction time, not a fabricated original-device extraction time.
The registration hash proves only the derived CSV bytes.

The joint scoped request returns **422**, preserving the figure6 unknown heading
reference. It is not retried unscoped, relabelled true, or substituted with COG.
The figure27-only request returns **200** through actual W2, one imported source,
no conflicts, uncalibrated and `observationApproval:not_assessed`. One-source
zero conflicts is not corroboration or evidence consistency. Both preview calls
leave all database rows unchanged after registration.

## Run

```sh
MCIS_ACCEPTANCE_CORE=/absolute/path/to/actual/core-wrapper.sh \
/path/to/service/venv/bin/python -m pytest \
service/tests/test_public_report_registered.py -q
```

The repository PDF and visual-review JSON must be present. Without actual-core
configuration the test is explicitly skipped, not counted as a pass.

## Unresolved production boundary

The citation's PDF hash/page/figure is a caller declaration, not a server-owned
validated link from this CSV to a stored PDF version. The test's pinned hash is
an acceptance safeguard, not a production authorization token. No original
AIS/VDR telemetry, independent source chain, device clock calibration or human
approval is established. No investigation findings are changed. There is no
OCR, live LLM, browser UI E2E, CI-wide pass, merge or deployment claim.
