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
