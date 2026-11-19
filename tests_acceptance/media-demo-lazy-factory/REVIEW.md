# Media demo factory: defer application imports

Base: candidate/media-demo-launcher `76d6c22c474172a28f7b2da9ae45021e8d573b82`.
Separate candidate: candidate/media-demo-lazy-factory. No merge of source-policy or other product candidates.

Static path: tools/media_review_demo/launch.py:11 and prepare.py:19 import create_media_review_demo; previously media_review_demo.py:2 immediately imported main. On this fixed media head main.py:40–42 imports the three seed modules before create_app can inspect seed_demo. Their bodies were not opened. image_review.app and audio_review.app also import ORM/router dependencies at module scope. The source-policy head `6d5069b9d320dcaddab28b95f8ed265bfc567b67` moves main's direct seed imports inside its seed_demo branch, but has no media_review_demo.py or tools/media_review_demo/launch.py; it is not incorporated here.

The only product edit moves all three factory dependencies into create_media_review_demo, preserving original import order followed by create_app(settings), register_image_review(app), register_audio_review(app), return app. No fallback, exception swallowing, data substitution, route/configuration/role/schema changes or model-enabling arguments. Seed defaults and actual invocation behavior are not made safe by this edit. Import errors now occur at explicit factory invocation, not module definition.

Repository source-reference search found known callers import only create_media_review_demo. The previously incidental imported globals create_app/register_image_review/register_audio_review are no longer attributes of this module; external monkeypatching of those incidental names is not certified. Actual factory signature is unchanged. The standard main entry is untouched.

## Development verification

`python tests_acceptance/media-demo-lazy-factory/check.py`

Passed: old fixed source gives three eager fake import events, candidate zero at definition; explicit invocation produces the same full import/create/image/audio sequence, same configuration object and same returned object. AST confirms unchanged signature and ordinary function body, and no exception suppression. Full factory source executes with a closed synthetic __import__ mapping and handmade callbacks; no real application package, FastAPI, ORM, database or seed modules import. No existing/paused tests run. Fixed local old Git object is required; no automatic fetch. This is a counterexample and candidate check using AST/fakes, not real startup or environment-isolation acceptance.

The sparse worktree contains only explicit allowed source/instruction/record paths. Staged increment is one small source edit, the synthetic test and verification/freeze/process records, no case/media/model/database/credentials.

## Still blocked

This removes only the eager main dependency of this factory module. It does not prove launch/prepare import closure: they have other top-level dependencies, including config, TestClient, converters and libraries. Explicit factory invocation still imports the original main and its case seeds on this base, creates database/schema/directories, and registers application routes. No invocation with real dependencies is authorized by this test. No real module import, startup, HTTP, source-policy combination, trusted identity, media, save, archival/recovery, permission probes, browser or model tested. Startup/archival pauses remain; not deployable. Next step requires separately reviewed closure/combination and an approved isolated runtime, not running existing launcher merely because this test passed.
