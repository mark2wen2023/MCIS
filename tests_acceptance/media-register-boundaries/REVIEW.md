# Private media registration boundaries

Base: df05eb6b0cbbc0494ea44a05d3d4bbfbb356b7f3, candidate/media-demo-lazy-factory.

Only product changes are in image_review/app.py and audio_review/app.py. Each existing register function now delegates the original table/trigger block to a private _initialize_*_review_storage helper and the original router/page decorator block to a private _mount_*_review_routes helper. No public function/signature, skip-DDL option, model, permission shortcut or independent application factory is added.

Default order remains: duplicate check → load tasks module → runtime assignment → create_all → trigger transaction/UPDATE then DELETE → review router then tasks router → page decorators → registered flag → same app. SQL expressions are moved verbatim, page response bodies/headers and paths unchanged. Exceptions propagate without interception; initialization early failure does not mount routes or set the registered flag, while the runtime assignment remains as previously. These helpers are internal refactoring boundaries, not approved standalone entry points.

Development command: `python tests_acceptance/media-register-boundaries/check.py`.

Passed six old/new synthetic sequence comparisons: image/audio each normal, duplicate registration, and early initialization failure. This last case is a handmade create_all callback raising a sentinel exception, not a database fault/permission probe. It checks identical exception identity, no later mounting and no success flag. Fake importer/task/router/engine/context/decorators record calls only. No SQL or page function executes. Runtime and engine arguments are checked by object identity. Complete AST equality after helper expansion proves no unrelated source operations changed; original and new SQL source segments compare byte-for-byte. Old fixed source is read from a local Git object; only selected register/private helper functions are compiled with handmade dependencies. No imports from either real app module, ORM, settings, models or service.

This is limited development validation, awaiting independent review. Not a real application, DDL, HTTP, page/browser, runtime-isolation or startup test. No prior paused tests run; no original cases, seed bodies, media, model files, databases or credentials read. No deployment or main/AI Studio change.

Remaining: media_review_demo still calls full main.create_app; Database.create_all still registers the full model set; task module imports and evidence receipt/archive/report access paths remain. This extraction does not reduce those closures or certify an isolated minimal factory. Actual initialization, permission intersection and consistent request read views remain unverified. Startup/archive pauses remain.
