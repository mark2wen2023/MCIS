# Public report replay: a source-specific acceptance checkpoint

Source baseline: commit 952c47a614d0bc0b6b1bdbda4b657438781f5344.
Public report: Yangze 22 / Vega Dream, 2024-12-30. User permits use of
published reports. Inputs are pinned in public_report_pin.json:
reports/yangze22/report.txt and tracks_from_report.csv.

## What was actually read and executed
Two rows for **the same vessel Yangze22** at 22:01:54 Beijing /14:01:54 UTC:
- ReportFigure-AIS, body page15/PDF17, figure6: extracted HDG47°.
- ReportFigure-VDR, body page39/PDF41, figure27: extracted HDG48°.

Their existing extraction values were retained verbatim. Both figure captions
were found in the fixed report text, and explicit timezone equivalence checked.
The figure images themselves were NOT re-read in this run. The csv is a previous
human/automation extraction, NOT raw AIS or VDR. Caption match proves location,
not numeric reading accuracy. The two excerpts are from one published report
and must not be treated as independent original evidence.

The test emits CSV (never fake NMEA), maps only hdgDeg to Heading, disables
calibration, and invokes the real W2 engine. It returns two tracks and zero
conflicts: the extracted 1° difference is below its default 2° threshold.
That is an engine replay result, **not** a finding of evidence consistency,
measurement accuracy or calibrated clocks. One timestamp cannot establish
trajectory coverage, device timing, manoeuvre history or collision causation.

## What deliberately did not happen
- No use of the AIS COG54° as Heading47°.
- No comparison of different vessels as conflicting measurements.
- No interpolation or invented points/timestamps.
- No changing earlier 1–2 second screenshot/narrative time differences.
- No upload of private evidence, model call, production case write or UI.
- No claim that SK-T01 accepts reports: its NMEA-only preview correctly rejects
  report-derived-csv. The real CSV execution is an isolated existing-core test,
  not a newly installed report adapter.

## Integration requirements exposed by this case
Before enabling report-derived sources in a case:
1. Bind vessel/object identity as well as case/source revision.
2. Bind physical quantity (HDG versus COG) and extraction provenance.
3. Preserve displayed device time, narrative time, explicit timezone and
   uncertainty separately; investigator review decides clock adjustment.
4. Attach original page/figure and excerpt plus extraction/reviewer version.
5. Label excerpts, original telemetry and derived observations distinctly.
6. Connect the trusted case repository and bounded service transport, not the
   test Repository/RealTestCore classes.

No production interface or existing W2 frozen source changed. This work
adds acceptance evidence and a concrete integration gap, not a completed module.
Reproduction uses the earlier build_real_w2.py and environment variables.
