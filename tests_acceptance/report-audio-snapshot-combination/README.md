# Generation sentence + exact audio range: synthetic composition

Product baseline: `30ac3e83d09bbae65beb6db56d3526bbcf37f662` on `candidate/audio-reference-range`.

Run from the repository root with existing Python/jsonschema dependencies:

```sh
python tests_acceptance/report-audio-snapshot-combination/check.py
```

Development result: two normal synthetic scenarios passed. First: two handmade report generation RA snapshots and explicitly handmade sentence associations select revision 1 (1000–2500ms) and revision 2 (4000–5500ms) respectively, using each exact reference digest. After adding revision 2/new generation, selecting the old RA still returns its old sentence and range. Second, separate scenario: the old revision's unknown time remains null/null; the new declared range does not supply a guessed time to the old one. Both check exact row-read order, unmodified inputs, file-relative 96000-frame/8000Hz basis, and explicit false verification/binding/media flags.

The script reuses actual generation_sentence, read_exact_audio_range and the existing exact reference reader/projector. Existing synthetic fixture functions and the pure-module AST loader are selected by name without running their test-file top levels. Existing report schema is used via jsonschema. No old test suite or paused nodes are executed. Product files are unchanged.

**The linking dictionaries are test fixtures, not trusted server bindings.** They are not written into reports or persisted, do not confer authority, and do not prove source authenticity. sourceVerified/persistentBinding remain false; mediaRetrieved/factVerified remain false. Digests here link handmade in-memory values only. This is not reading or hearing an old audio segment, an HTTP test, real report generation, an ORM snapshot, authorization intersection, or independent acceptance.

Still needed before product connection: trusted server-owned sentence/media binding, authorization intersection and one proven consistent read view including report snapshot, exact revisions, evidence/source digests and reliable original sample basis. No route, default export, database, Save, migration, recovery, permissions, service, browser, model or real case test was added/run. Startup/archival pauses remain. No new dependencies or binary/media fixtures are included.

## Actual synthetic WAV bytes (follow-up to 7a2d0e4)

```sh
python tests_acceptance/report-audio-snapshot-combination/check.py
python tests_acceptance/report-audio-snapshot-combination/check_wav.py
```

Both commands passed in development. The first retains the original purely in-memory placeholder scenarios. The second reads only the fixed local Git object `c10b2cd787f4b70d404893be9b9bfeb4f7de4361:tests_acceptance/synthetic-audio-review/make_wav.py`, verifies source SHA-256 `d5a9285e64898077888f92615082e33278fd405ddabadad4e339a82fcec0cd23`, then executes that generator in a fresh automatically cleaned /tmp directory. Missing object fails: no automatic fetch, source fallback or checked-in generator copy. Requires /usr/bin/git with GIT_NO_LAZY_FETCH support; no dependency installation. Only generator-produced WAV/manifest files are read; no original materials or environment values are read.

Actual file SHA-256 must equal `48e65e6aa7493adecacf16a5a2bd09e0966303658ec2bf6c980cc239fb4c266f`. Standard-library wave parses mono 16-bit PCM, 8000 Hz, 96000 frames (12 seconds) and checks PCM byte count. The composition fixture now optionally takes those observed bytes' digest and header basis: initial audio metadata; machineDraft.source currentSha256/registeredSha256 and duration/frame/rate; human audioSha256; evidence sha256/currentSha256. Both exact ranges use the same actual synthetic WAV digest and basis; the old selection remains old after the new generation. Separate unknown time remains null. No product source changed.

**Those field assignments do not perform registration or authenticate evidence.** Evidence IDs, registration/custody assertions, stateDigest, machine artifact/draft hashes, report snapshots, human revisions and sentence associations remain handmade fixtures. In particular the unchanged machine artifact/state placeholder hashes are asserted as such. There is no real machine output, receipt or trusted persistent binding. The range reader still returns mediaRetrieved/factVerified=false, and generation_sentence still returns sourceVerified/persistentBinding=false. Only the standalone test setup reads its generated tone file, not the report reader or a production media endpoint.

This 8 kHz non-speech tone is **not suitable for SenseVoice acceptance requiring 16 kHz mono 16-bit PCM**; that separately needs authorized speech material. No model or resampling is run. Future authorized player acceptance must measure actual seek position and pause/end position against the intended file-relative range, including unknown-time non-positioning; hearing the marker alone is insufficient. Neither command runs a player or proves browser listening, seek precision, pause timing, permission intersection, ORM snapshot, Save, service startup or source authenticity. The older frozen test manifest remains evidence for its old version; the follow-up manifest is logs/report-audio-generated-wav-frozen.txt.
