# Original W12 analysis seed

Exact original seed and SHA sidecar, archived before independently reviewed
current-CLI regeneration. Seed SHA256:
`3ccc329f375de404993b65dfb1c22c3d467057bc57f376a958a22336ffb28cb5`.

Historical generating DLL SHA256:
`b0e507b80b41f2d3a5de0dd73adac2b070dd7310e2f9c52b65a6ab44b9b652f3`.
See `logs/core-dll-provenance-investigation.md` and
`tools/provenance/reproduce_historical_core.py` for byte-identical recovery.

To restore the seed, copy these two files to `service/mcis_service/analysis/data/` (two levels above this archive directory)
(after preserving any newer baseline). This restores historical data, NOT the
current-CLI provenance match; do not install an old binary in production merely
to pass source freshness checks. Current regeneration evidence is retained in
`logs/current-core-seed-candidate-verification.json`.
