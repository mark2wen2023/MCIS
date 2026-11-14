# Independent review: selected track point predecessor display

TrackView.tsx SHA256 `7e665ed881d76fda61107be5363bb09e56da612ff19e1e4ced00e1e6a0838130`.

## Independently executed

Added `independent.test.tsx`: mounts the actual full TrackView in HappyDOM with 205 synthetic points passed through the real parseSnapshot. Uses real provenance selector, next-page button, table point button and plotted circle events.

Passed: filtering to Measured, going to page two and selecting filtered point102 yields original returned point203, previous original point202 (Interpolated), correct5s difference and previous UTC/source rather than previous filtered point; source markup remains escaped/no script node; changing filter clears selection; plotted-circle selection resolves original point2 and point1 predecessor; snapshot remains unchanged. Existing detail.test.cjs SSR checks also reran successfully for duplicate/reversed time, unknown source, first-point disclaimer and escaping.

Initial mounted run printed success but retained React/HappyDOM scheduler handles. Reviewer stopped that finished test process and added explicit success/error process exit after all assertions/unmount, then rebuilt and reran to exit0. Not a hidden assertion failure.

## Static review

No blocker found in the bounded predecessor-display change. Actual parsed points are copied per record; source filtering preserves those record object identities. Thus indexOf on selected filtered record correctly locates its original returned position without timestamp-based identity merging. Backend parseSnapshot bounds finite timeSec to ±1e12, avoiding nonfinite subtraction for valid page inputs. The component is not a new untrusted-input validator; arbitrary direct props outside parsed contract are not certified.

Data remains in original returned order. Repeated/reversed time is described rather than repaired, and no missing-message threshold, raw-AIS authenticity, interpolation, clock calibration or numerical backend change is introduced. Table/plot numbering remains filtered-view numbering while detail heading refers to original sequence index, as checked in the interaction test.

## Boundaries

HappyDOM is mounted component simulation, **not real-browser visual/accessibility or actual AIS/API end-to-end acceptance**. Coordinator's full tsc/Vite build is reported separately, not independently repeated here. No production file edit, remote operation, deployment or genuine data/model call by reviewer. Preserve concurrent TrackView changes. Coordinator normalized an extra terminal LF in the supplied before snapshot during review; the reviewed production candidate hash above did not change.
