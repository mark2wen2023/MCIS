# Offline report/audio empty-directory preflight

Baseline: b1e1d337abee523299ff1bb860f1d81c1813f263. This tool checks only a caller-created, empty directory and a fixed sample/path plan. It does not prepare a runnable demo.

## Why not run the existing preflight?

`tools/media_review_demo/launch.py` imports config, the demo factory and prepare at module scope; check_manifest opens SQLite and checks prepared rows. `prepare.py` imports TestClient and the demo factory and calls existing APIs. These remain outside the approved offline scope. This small pre-application check neither replaces nor invokes them.

Only the existing synthetic non-speech WAV is planned: `tests_acceptance/synthetic-audio-review/make_wav.py` at `c10b2cd787f4b70d404893be9b9bfeb4f7de4361`. Its 12 seconds / 8000 Hz / 96000 frames, `synthetic-markers.wav` and `manifest.json` remain the source of material generation; no generator copy or new waveform is added. That source is on a separate synthetic-scenario chain, is not fetched/imported/executed here, and its existence is not checked by this tool. The prior fixture source hashes are placeholders, not this generated WAV's registered identity. Reusing it later requires explicit fixed-source review, generation and actual-byte verification; this preflight proves none of those.

## Standalone check only — NOT a startup command

With standard-library Python and a new caller-controlled temporary directory:

```sh
preflight_root=$(mktemp -d /tmp/mcis-report-audio-XXXXXX)
python tools/report_audio_preflight/check.py --root "$preflight_root" --sample synthetic-markers-v1
rmdir "$preflight_root"
```

Do not point it at a real case directory. It checks directory metadata along the explicitly supplied path, and a single-level emptiness check of that root, not the checkout or mounted directory contents. It does not read directory member contents, environment variables, databases, seeds, credentials or media. An absolute root with the dedicated prefix is required; symlink/non-directory components fail. Sample and planned members are exact allowlists. Invalid input or filesystem error exits 2 with a generic error, without exposing filenames from the root. No fallback, retry, service factory or `--serve` exists.

Output plans only `demo.db`, `materials/synthetic-markers.wav`, `materials/manifest.json`. The materials subdirectory does not yet exist, matching the old generator's new-output-directory rule. The proposed seed_demo=False, loopback 127.0.0.1:8766 and disabled models reflect the existing launcher's intent, not applied configuration. Existing default seed/import risks remain; no Settings or application module is imported.

## Development evidence and limits

`python tests_acceptance/report-audio-preflight/check.py` passed: standard-library TemporaryDirectory with explicit /tmp; empty-root plan and no output files; unlisted sample, relative/parent traversal and unlisted member inputs; ordinary nonempty synthetic-root rejection. CLI normal check passed, and ordinary relative-root input exited 2. These are input validation checks, not permission-denial, writes-rejected, failure injection, recovery or ORM probes. No paused suite was run.

The caller must ensure the directory was newly created, owned/controlled and remains stable without concurrent writers. Emptiness at one instant does not prove freshness, isolation, absence of mounts or later path stability. No race resistance or sandbox is claimed; hard links, mounted filesystems, source/dependency closure and runtime isolation are not certified. The check does not grant startup approval: startupAllowed/isolationVerified remain false and no DB/materials are created. Do not use a successful plan as authorization to run the existing preparer, launcher, ORM or service.

Next gate: approved, verifiable runtime isolation and dependency/source closure; then separately authorized synthetic preparation with original-byte identity, trusted sentence binding, authorization intersection and consistent report/media read view. All remain unverified. No main/mcis-3d/product logic changes, deployment, or actual listening test.
