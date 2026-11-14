# Registered preview source replacement resets declarations

Changing one evidence selection resets that row's CSV mapping, measured kind to
Heading, vessel/source/citation/time/reference declarations, optional parent PDF
reference, and acknowledgement/result via the existing generation guard. Other
rows are retained. A visible notice explains that another file requires renewed
mapping and declaration. This prevents accidental carry-over of one extract's
claimed parent/ship/citation to a different extract. It does not certify those
claims or alter originals, database records, permissions or persistent relations.

Acceptance: primary HappyDOM/control-fetch test reproduced the retained parent
control before the change, then passed53 checks after the change (previous45+
8 reset checks). TypeScript/Vite build passes, existing large-bundle warning.
No new real-network/backend/browser/LLM/CI validation claimed. Test-only synthetic
change events are not evidence of actual browser click acceptance.

Independent native reviewer:15 newly authored multi-row/lifecycle checks pass,
primary53 and previous parent48 rerun pass. Counts overlap; do not sum as unique.
New independent test: web/tests/source-reset-review.tsx (esbuild with same
HappyDOM run setup as parent-report-review.tsx). Targeted oxlint exits0 with two
existing set-state-in-effect warnings. Frozen component SHA256:
7a8f8f081f4c1466b09ddde2e074cc756e1c82844683b14cd950e7f967ea4eec.
