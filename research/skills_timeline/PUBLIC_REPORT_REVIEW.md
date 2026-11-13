# Independent public-report replay review

Reviewed `test_public_report_w2.py` and `public_report_pin.json` against the two
pinned report extraction files. Full discovery with real rebuilt W2: **80 passed,
zero skipped** (77 previous, 3 new; no duplicated imported TestCase classes).

No blocking issue found in the stated narrow scope. The selection keeps YANGZE22,
one UTC instant, and explicit HDG values 47/48 degrees. AIS COG 54 is not mapped
to heading; report-derived CSV is not fabricated NMEA. The captions match the
text extraction, and Beijing/UTC timestamps represent the same instant. The
current NMEA-only Skill still rejects report-derived CSV.

One independent ad-hoc diagnostic replay used a **test-only 0.5-degree threshold**
to observe the engine's actual imported values: C-01, a=47, b=48, delta=1,
trackKind=Heading, two used sentences, no import diagnostics. This is a test
sensitivity probe, not a proposed investigation threshold and not part of the 80
count. With the ordinary 2-degree default, zero conflicts is expected.

Limits: original PDF figure pixels, extraction accuracy, raw AIS/VDR, device
clock alignment, sensor accuracy and evidential independence have not been
verified. Both entries derive from one public investigation report, not newly
acquired independent original streams. Zero conflicts does not corroborate facts
or prove consistency. This is real-W2 replay of existing report excerpts, not a
completed operational Skill, UI, production authorization or LLM validation.
No implementation changed, no push/merge/deploy. Reviewer: independent native subtask.
